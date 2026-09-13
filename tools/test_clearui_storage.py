#!/usr/bin/env python3
"""Check programming address translation and persistent scan-skip behavior."""
from pathlib import Path
import subprocess
import tempfile
from test_clearui_algorithms import function

ROOT = Path(__file__).resolve().parents[1]
PREAMBLE = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "settings.h"
#include "misc.h"
#include "driver/eeprom_compat.c"
EEPROM_Config_t gEeprom;
static ChannelAttributes_t attributes[MR_CHANNELS_MAX + 7];
static unsigned flash_reads, flash_writes;
static uint32_t last_address;
static uint8_t last_data[8];
ChannelAttributes_t *MR_GetChannelAttributes(uint16_t channel) {
    assert(channel < MR_CHANNELS_MAX + 7);
    return &attributes[channel];
}
void MR_SetChannelAttributes(uint16_t channel, const ChannelAttributes_t *value) {
    attributes[channel] = *value;
}
void SETTINGS_SaveChannelName(uint16_t channel, const char *name) {
    assert(channel < 1024 && name[0] == 0);
}
void PY25Q16_ReadBuffer(uint32_t address, void *buffer, uint32_t size) {
    last_address = address;
    ++flash_reads;
    memset(buffer, 0x55, size);
}
void PY25Q16_WriteBuffer(uint32_t address, const void *buffer, uint32_t size, bool append) {
    (void)append;
    assert(size == 8);
    last_address = address;
    memcpy(last_data, buffer, size);
    ++flash_writes;
}
'''
TESTS = r'''
int main(void) {
    uint8_t settings[8];
    memset(settings, 0xFF, sizeof(settings));
    assert(!SETTINGS_ClearUIMeterStyle(settings)); // fresh/full reset: Spine
    assert(!SETTINGS_ClearUIRxFrame(settings)); // fresh/full reset: no frame
    settings[0] = 0; // Saved block: even 0xFF in byte 5 remains a valid choice.
    for (unsigned value = 0; value < 256; ++value) {
        settings[5] = value;
        assert(SETTINGS_ClearUIMeterStyle(settings) == ((value & 0x40) != 0));
        assert(SETTINGS_ClearUIRxFrame(settings) == ((value & 0x20) != 0));
    }
    uint8_t data[8] = {1,2,3,4,5,6,7,8};
    for (unsigned mode = 0; mode < 8; ++mode) {
        memset(settings, 0x55, sizeof(settings));
        SETTINGS_SaveClearUIRxFrame(settings, mode);
        assert(SETTINGS_ClearUIRxFrame(settings) == (mode < 7 ? mode : 0));
        assert((settings[5] & ~0x20) == (0x55 & ~0x20));
        for (unsigned i = 0; i < 8; ++i)
            if (i != 3 && i != 5) assert(settings[i] == 0x55);
    }
    // The tag alone cannot enable inversion; old saved On remains Dotted.
    settings[3] = 0xA2; settings[5] &= ~0x20;
    assert(SETTINGS_ClearUIRxFrame(settings) == 0);
    settings[5] |= 0x20; settings[3] = 0xFF;
    assert(SETTINGS_ClearUIRxFrame(settings) == 1);
    assert(sizeof(ChannelAttributes_t) == 2);
    EEPROM_WriteBuffer(0xD000, data, sizeof(data));
    assert(flash_writes == 1 && last_address == 0xD000);
    assert(memcmp(last_data, data, 8) == 0);
    EEPROM_WriteBuffer(0xD1F8, data, sizeof(data));
    assert(flash_writes == 2 && last_address == 0xD1F8);
    EEPROM_WriteBuffer(0xD200, data, sizeof(data));
    assert(flash_writes == 2);
    EEPROM_ReadBuffer(0xD000, data, sizeof(data));
    assert(last_address == 0xD000 && data[0] == 0x55);
    EEPROM_ReadBuffer(0xD200, data, sizeof(data));
    assert(flash_reads == 1 && data[0] == 0xff);
    EEPROM_ReadBuffer(0xB000, data, sizeof(data));
    assert(last_address == 0x10000);
    EEPROM_ReadBuffer(0xC000, data, sizeof(data));
    assert(last_address == 0x11000);

    for (unsigned i = 0; i < MR_CHANNELS_MAX + 7; i++) attributes[i].band = 7;
    attributes[0].band = BAND3_137MHz;
    attributes[0].scanlist = 1;
    attributes[0].unused_2 = 1;
    assert((attributes[0].__val & 0x40) == 0x40);
    assert(RADIO_CheckValidChannel(0, false, 1));
    assert(!RADIO_CheckValidChannel(0, true, 1));
    assert(!RADIO_CheckValidChannel(0, true, 25));
    assert(!RADIO_CheckValidList(1));
    attributes[0].exclude = 1;
    attributes[0].exclude = 0; // Startup clears temporary exclusions only.
    assert(!RADIO_CheckValidChannel(0, true, 1));
    VFO_Info_t vfo = {.Band = BAND3_137MHz, .SCANLIST_PARTICIPATION = 1};
    SETTINGS_UpdateChannel(0, &vfo, true);
    assert(attributes[0].unused_2);
    assert(!RADIO_CheckValidList(1));
    attributes[0].unused_2 = 0;
    assert(RADIO_CheckValidChannel(0, true, 1));
    assert(RADIO_CheckValidList(1));
    SETTINGS_UpdateChannel(0, &vfo, false);
    assert(!attributes[0].unused_2 && attributes[0].band == 7);
    puts("Address mapping, calibration/logo separation, persistent skips, channel edits and Spine defaults: passed");
}
'''

def main():
    routines = function("App/radio.c", "RADIO_CheckValidList")
    routines += function("App/radio.c", "RADIO_CheckValidChannel")
    routines += function("App/settings.c", "SETTINGS_UpdateChannel")
    routines += function("App/settings.c", "SETTINGS_ClearUIMeterStyle")
    routines += function("App/settings.c", "SETTINGS_ClearUIRxFrame")
    routines += function("App/settings.c", "SETTINGS_SaveClearUIRxFrame")
    with tempfile.TemporaryDirectory(prefix="clearui-storage-") as tmp:
        source, binary = Path(tmp) / "test.c", Path(tmp) / "test"
        source.write_text(PREAMBLE + routines + TESTS)
        subprocess.run(["cc", "-std=gnu11", "-Wall", "-Werror",
                        "-DENABLE_CLEAR_UI", "-DENABLE_FEAT_F4HWN",
                        "-fsanitize=address,undefined", "-I", str(ROOT / "App"),
                        str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

if __name__ == "__main__":
    main()
