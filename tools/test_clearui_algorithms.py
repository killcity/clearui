#!/usr/bin/env python3
"""Compile the production waterfall/name routines with bounded host hardware stubs."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(path, name):
    source = (ROOT / path).read_text()
    match = re.search(r"^(?:static )?(?:void|bool|uint8_t|uint16_t) " + name +
                      r"\([^;]*?\)\s*\{", source, re.M)
    if match is None:
        raise RuntimeError(f"Missing production function: {name}")
    depth = 1
    end = match.end()
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end] + "\n"


PREAMBLE = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MIN(a,b) ((a) < (b) ? (a) : (b))
#define clamp(v,lo,hi) ((v) < (lo) ? (lo) : ((v) > (hi) ? (hi) : (v)))
static const uint16_t RSSI_MAX_VALUE = 65535;
static const uint8_t DrawingTopY = 8;
static uint16_t rssiHistory[128];
static uint8_t waterfallHistory[32][16];
static uint8_t waterfallPhase;
static bool redrawScreen;
static struct { uint16_t measurementsCount; } scanInfo;
static struct { int dbMin, dbMax; } settings = {-128, -50};
static uint8_t framebuffer[7][128];
static int Rssi2DBm(uint16_t value) { return value / 2 - 160; }
static void PutPixel(uint8_t x, uint8_t y, bool value) {
    assert(x < 128 && y >= 8 && y < 40 && value);
    framebuffer[y / 8][x] |= 1u << (y % 8);
}
static uint8_t flash[0x8000];
static unsigned reads;
static bool RADIO_CheckValidChannel(uint16_t channel, bool scan, uint8_t list) {
    (void)scan; (void)list;
    return channel < 1024;
}
static void PY25Q16_ReadBuffer(uint32_t offset, void *buffer, uint16_t length) {
    assert(offset >= 0x4000 && offset + length <= sizeof(flash));
    memcpy(buffer, flash + offset, length);
    ++reads;
}
static void PY25Q16_WriteBuffer(uint32_t offset, const void *buffer,
                              uint16_t length, bool erase) {
    (void)erase;
    assert(offset >= 0x4000 && offset + length <= sizeof(flash));
    memcpy(flash + offset, buffer, length);
}
"""

TESTS = r"""
static void set_level(unsigned level) {
    // Select a real RSSI input giving the requested quantized density.
    uint16_t value;
    for (value = 1; value < 400 && Rssi2PX(value, 0, 4) != level; ++value) {}
    assert(value < 400);
    for (unsigned x = 0; x < 128; ++x) rssiHistory[x] = value;
}
static unsigned row_bits(unsigned row) {
    unsigned count = 0;
    for (unsigned x = 0; x < 128; ++x)
        count += !!(waterfallHistory[row][x / 8] & (1u << (x % 8)));
    return count;
}
static void test_waterfall(void) {
    scanInfo.measurementsCount = 128;
    memset(waterfallHistory, 0xff, sizeof(waterfallHistory));
    memset(rssiHistory, 0xff, sizeof(rssiHistory));
    waterfallPhase = 99;
    ResetWaterfall();
    assert(waterfallPhase == 0);
    for (unsigned row = 0; row < 32; ++row) assert(row_bits(row) == 0);
    for (unsigned x = 0; x < 128; ++x) assert(rssiHistory[x] == 0);

    for (unsigned level = 0; level <= 4; ++level) {
        ResetWaterfall();
        set_level(level);
        WaterfallCaptureRow();
        WaterfallCaptureRow();
        assert(row_bits(0) + row_bits(1) == level * 64);
    }
    ResetWaterfall();
    set_level(4);
    WaterfallCaptureRow();
    memset(rssiHistory, 0, sizeof(rssiHistory));
    WaterfallCaptureRow();
    assert(row_bits(0) == 0 && row_bits(1) == 128);
    for (unsigned n = 0; n < 30; ++n) WaterfallCaptureRow();
    assert(row_bits(31) == 128);
    WaterfallCaptureRow();
    assert(row_bits(31) == 0);
    for (unsigned n = 0; n < 300; ++n) WaterfallCaptureRow();

    // One sample, normal/interpolated spans, and binned large spans.
    const unsigned spans[] = {1, 16, 32, 64, 127, 128, 129, 1024};
    for (unsigned s = 0; s < sizeof(spans)/sizeof(spans[0]); ++s) {
        ResetWaterfall();
        scanInfo.measurementsCount = spans[s];
        set_level(4);
        WaterfallCaptureRow();
        assert(row_bits(0) == 128);
        memset(rssiHistory, 0xff, sizeof(rssiHistory));
        WaterfallCaptureRow();
        assert(row_bits(0) == 0);
    }
    scanInfo.measurementsCount = 0;
    uint8_t previous[sizeof(waterfallHistory)];
    memcpy(previous, waterfallHistory, sizeof(previous));
    WaterfallCaptureRow();
    assert(memcmp(previous, waterfallHistory, sizeof(previous)) == 0);

    // Rendering may only touch the four reserved history pages.
    memset(waterfallHistory, 0xff, sizeof(waterfallHistory));
    memset(framebuffer, 0, sizeof(framebuffer));
    memset(framebuffer[0], 0x55, 128);
    memset(framebuffer[5], 0x33, 128);
    memset(framebuffer[6], 0xaa, 128);
    DrawWaterfall();
    for (unsigned x = 0; x < 128; ++x) {
        assert(framebuffer[0][x] == 0x55);
        assert(framebuffer[5][x] == 0x33);
        assert(framebuffer[6][x] == 0xaa);
        for (unsigned page = 1; page <= 4; ++page)
            assert(framebuffer[page][x] == 0xff);
    }
}
static void test_names(void) {
    const char *full = "ABCDEFGHIJKLMNOP";
#ifdef ENABLE_CLEAR_UI
    const unsigned max_name = 16;
#else
    const unsigned max_name = 10;
#endif
    SETTINGS_SaveChannelName(1023, full);
    for (unsigned n = 0; n < 16; ++n)
        assert(flash[0x7ff0 + n] == (n < max_name ? full[n] : 0));
    for (unsigned capacity = 0; capacity <= 24; ++capacity) {
        unsigned char guarded[28];
        memset(guarded, 0xa5, sizeof(guarded));
        SETTINGS_FetchChannelName((char *)guarded + 1, 1023, capacity);
        assert(guarded[0] == 0xa5);
        for (unsigned n = capacity + 1; n < sizeof(guarded); ++n)
            assert(guarded[n] == 0xa5);
        if (capacity) {
            unsigned length = MIN(capacity - 1, max_name);
            assert(memcmp(guarded + 1, full, length) == 0);
            assert(guarded[length + 1] == 0);
        } else assert(guarded[1] == 0xa5);
    }
    char result[17];
    SETTINGS_FetchChannelName(result, 65535, sizeof(result));
    assert(result[0] == 0);
    SETTINGS_FetchChannelName(NULL, 0, 17);
    SETTINGS_SaveChannelName(0, "  Test   ");
    SETTINGS_FetchChannelName(result, 0, sizeof(result));
    assert(strcmp(result, "  Test") == 0);
    SETTINGS_SaveChannelName(0, "");
    SETTINGS_FetchChannelName(result, 0, sizeof(result));
    assert(result[0] == 0);
    memset(flash + 0x4000, 0xff, 16);
    SETTINGS_FetchChannelName(result, 0, sizeof(result));
    assert(result[0] == 0);
    memcpy(flash + 0x4000, "AB\177CD", 5);
    SETTINGS_FetchChannelName(result, 0, sizeof(result));
    assert(strcmp(result, "AB") == 0);
    unsigned old_reads = reads;
    SETTINGS_FetchChannelName(result, 0, 1);
    assert(result[0] == 0 && reads == old_reads);
}
int main(void) {
    test_waterfall();
    test_names();
    puts("Waterfall ordering, density, reset, bounds, and channel names: passed");
    return 0;
}
"""


def main():
    routines = "".join(function("App/app/spectrum.c", name) for name in (
        "ResetWaterfall", "iSqrt", "IsRssiHistoryInvalid", "Rssi2PX",
        "InterpolateRssi", "WaterfallCaptureRow", "DrawWaterfall"))
    routines += function("App/settings.c", "SETTINGS_FetchChannelName")
    routines += function("App/settings.c", "SETTINGS_SaveChannelName")
    with tempfile.TemporaryDirectory(prefix="clearui-host-tests-") as directory:
        source = Path(directory) / "test.c"
        source.write_text(PREAMBLE + routines + TESTS)
        for mode in ([], ["-DENABLE_CLEAR_UI"]):
            binary = Path(directory) / ("clearui" if mode else "stock")
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                            *mode, str(source), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
