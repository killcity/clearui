/* SPDX-License-Identifier: Apache-2.0
 * Added for ClearUI in 2026.
 * ClearUI standby display for the 128x64 monochrome LCD.
 */

#include <string.h>

#include "app/clearui.h"
#include "app/chFrScanner.h"
#include "bitmaps.h"
#include "clearui_font.h"
#include "driver/bk4819.h"
#include "driver/st7565.h"
#include "external/printf/printf.h"
#include "font.h"
#include "functions.h"
#include "helper/battery.h"
#include "misc.h"
#include "radio.h"
#include "settings.h"
#include "ui/helper.h"
#include "ui/inputbox.h"
#include "ui/main.h"
#include "ui/status.h"
#include "ui/ui.h"

static char    gClearUIToast[18];
static uint8_t gClearUIToastTicks;
static uint8_t gClearUINameScroll;
static uint8_t gClearUITxLevel;
static uint16_t gClearUILastChannel[2] = {0xFFFF, 0xFFFF};

void UI_CLEARUI_ShowToast(const char *text)
{
    strncpy(gClearUIToast, text, sizeof(gClearUIToast) - 1);
    gClearUIToast[sizeof(gClearUIToast) - 1] = '\0';
    gClearUIToastTicks = 3;
    gUpdateDisplay = true;
}

static bool CLEARUI_IsSingleBand(void)
{
    return gEeprom.DUAL_WATCH == DUAL_WATCH_OFF &&
           gEeprom.CROSS_BAND_RX_TX == CROSS_BAND_OFF;
}

static bool CLEARUI_IsMemory(uint8_t vfoNumber)
{
    return IS_MR_CHANNEL(gEeprom.ScreenChannel[vfoNumber]);
}

static const char *CLEARUI_PowerName(const VFO_Info_t *vfo)
{
    static const char *const names[] =
    {
        "U", "L1", "L2", "L3", "L4", "L5", "M", "H"
    };

    return vfo->RECEIVE_ONLY ? "RX" : names[vfo->OUTPUT_POWER & 7];
}

static const char *CLEARUI_ModeName(const VFO_Info_t *vfo)
{
    if (vfo->Modulation == MODULATION_FM)
        return vfo->CHANNEL_BANDWIDTH == BANDWIDTH_NARROW ? "FM-N" : "FM";
    if (vfo->Modulation == MODULATION_AM)
        return vfo->CHANNEL_BANDWIDTH == BANDWIDTH_NARROW ? "AM-N" : "AM";

    return gModulationStr[vfo->Modulation];
}

static const char *CLEARUI_ToneName(const VFO_Info_t *vfo)
{
    switch (vfo->pRX->CodeType)
    {
        case CODE_TYPE_CONTINUOUS_TONE: return "TSQL";
        case CODE_TYPE_DIGITAL:
        case CODE_TYPE_REVERSE_DIGITAL: return "DTCS";
        default:
            return vfo->pTX->CodeType == CODE_TYPE_OFF ? "" : "TONE";
    }
}

static void CLEARUI_Metadata(uint8_t vfoNumber, char *metadata)
{
    const VFO_Info_t *vfo = &gEeprom.VfoInfo[vfoNumber];
    const char *tone = CLEARUI_ToneName(vfo);

    if (tone[0] != '\0')
        sprintf(metadata, "%s  %s  %s", CLEARUI_ModeName(vfo), tone,
                CLEARUI_PowerName(vfo));
    else
        sprintf(metadata, "%s  %s", CLEARUI_ModeName(vfo),
                CLEARUI_PowerName(vfo));
}

static void CLEARUI_ChannelName(uint8_t vfoNumber, char *name)
{
    const uint16_t channel = gEeprom.ScreenChannel[vfoNumber];

    if (gClearUILastChannel[vfoNumber] != channel)
    {
        gClearUILastChannel[vfoNumber] = channel;
        gClearUINameScroll = 0;
    }

    if (IS_MR_CHANNEL(channel))
    {
        strncpy(name, gEeprom.VfoInfo[vfoNumber].Name, 16);
        name[16] = '\0';
        if (name[0] != '\0')
            return;
        sprintf(name, "CH-%03u", channel + 1);
        return;
    }

    sprintf(name, "VFO %c", 'A' + vfoNumber);
}

static void CLEARUI_FrequencyParts(uint8_t vfoNumber, char *primary, char *extra)
{
    const VFO_Info_t *vfo = &gEeprom.VfoInfo[vfoNumber];
    uint32_t value = vfo->pRX->Frequency;
    uint8_t subKHz;

    if (gCurrentFunction == FUNCTION_TRANSMIT && gEeprom.TX_VFO == vfoNumber)
        value = vfo->pTX->Frequency;

    subKHz = value % 100;
    sprintf(primary, "%u.%03u", value / 100000, (value / 100) % 1000);
    if (subKHz == 0)
        extra[0] = '\0';
    else if ((subKHz % 10) == 0)
        sprintf(extra, "%u", subKHz / 10);
    else
        sprintf(extra, "%02u", subKHz);
}

static void CLEARUI_Frequency(uint8_t vfoNumber, char *frequency)
{
    char primary[9];
    char extra[3];

    CLEARUI_FrequencyParts(vfoNumber, primary, extra);
    sprintf(frequency, "%s%s", primary, extra);
}

static void CLEARUI_InvertArea(uint8_t top, uint8_t bottom)
{
    for (uint8_t y = top; y <= bottom; y++)
    {
        const uint8_t mask = 1 << (y & 7);
        for (uint8_t x = 0; x < 128; x++)
            gFrameBuffer[y >> 3][x] ^= mask;
    }
}

static void CLEARUI_DrawSmallAt(const char *text, uint8_t x, uint8_t y)
{
    for (; *text != '\0' && x <= 122; text++, x += 7)
    {
        if (*text <= ' ' || *text >= 127)
            continue;

        const uint8_t *glyph = &gClearUIFontSmall[(*text - ' ') * 6];
        for (uint8_t column = 0; column < 6; column++)
            for (uint8_t bit = 0; bit < 8; bit++)
                if (glyph[column] & (1 << bit))
                    UI_DrawPixelBuffer(gFrameBuffer, x + column, y + bit, true);
    }
}

static void CLEARUI_DrawSmallCentered(const char *text, uint8_t y)
{
    CLEARUI_DrawSmallAt(text, (128 - strlen(text) * 7) / 2, y);
}

static void CLEARUI_DrawPill(const char *text, uint8_t x, uint8_t y,
                          uint8_t width)
{
    for (uint8_t column = 0; column < width; column++)
        for (uint8_t row = 0; row < 6; row++)
            if (!((column == 0 || column == width - 1) &&
                  (row == 0 || row == 5)))
                UI_DrawPixelBuffer(gFrameBuffer, x + column, y + row, true);

    GUI_DisplaySmallest(text, x + (width - strlen(text) * 4) / 2,
                        y, false, false);
}

static void CLEARUI_DrawCompactPill(const char *text, uint8_t x, uint8_t y,
                                 uint8_t width)
{
    for (uint8_t column = 0; column < width; column++)
        for (uint8_t row = 0; row < 5; row++)
            if (!((column == 0 || column == width - 1) &&
                  (row == 0 || row == 4)))
                UI_DrawPixelBuffer(gFrameBuffer, x + column, y + row, true);

    GUI_DisplaySmallest(text, x + (width - strlen(text) * 4) / 2,
                        y, false, false);
}

static uint8_t CLEARUI_NameWidth(const char *text)
{
    uint16_t width = 0;

    for (; *text != '\0'; text++)
        if (*text >= ' ' && *text < 127)
            width += gClearUIFontWidths[*text - ' '];
    return MIN(width, 255);
}

static void CLEARUI_DrawNameAt(const char *text, int16_t x, uint8_t y,
                               uint8_t right)
{
    for (; *text != '\0'; text++)
    {
        if (*text < ' ' || *text >= 127)
            continue;

        const uint8_t glyph = *text - ' ';
        const uint8_t width = gClearUIFontWidths[glyph];
        const uint16_t offset = gClearUIFontOffsets[glyph];

        for (uint8_t column = 0; column < width; column++)
        {
            const int16_t px = x + column;
            if (px >= 0 && px < right)
            {
                for (uint8_t bit = 0; bit < CLEARUI_FONT_HEIGHT; bit++)
                    if (gClearUIFontData[offset + column * CLEARUI_FONT_COLUMN_BYTES + bit / 8] &
                        (1u << (bit % 8)))
                        UI_DrawPixelBuffer(gFrameBuffer, px, y + bit, true);
            }
        }
        x += width;
    }
}

static void CLEARUI_DrawBigIdentity(const char *text, uint8_t y)
{
    const uint8_t visibleWidth = gSetting_set_met ? 128 : 114;
    const uint8_t width = CLEARUI_NameWidth(text);
    int16_t x = 0;

    if (width > visibleWidth)
    {
        const uint8_t overrun = width - visibleWidth;
        const uint8_t steps = (overrun + 1) / 2;
        const uint8_t phase = gClearUINameScroll % (steps + 8);
        uint8_t offset = phase < 4 ? 0 : (phase - 3) * 2;

        if (offset > overrun)
            offset = overrun;
        x -= offset;
    }

    CLEARUI_DrawNameAt(text, x, y, visibleWidth);
}

static void CLEARUI_DrawFrequencyBig(uint8_t vfoNumber, uint8_t y)
{
    char primary[9];
    char extra[3];

    CLEARUI_FrequencyParts(vfoNumber, primary, extra);

    CLEARUI_DrawNameAt(primary, 0, y, 128);
    if (extra[0] != '\0')
        CLEARUI_DrawSmallAt(extra, CLEARUI_NameWidth(primary) + 1, y + 3);
}

void UI_CLEARUI_RenderBootLogo(void)
{
    // Original pixel mark: an open C enclosing three ascending signal bars.
    // Reuse the native font; no external bitmap or additional boot delay.
    memset(gStatusLine, 0, sizeof(gStatusLine));
    UI_DisplayClear();
    for (uint8_t y = 0; y < 26; y++)
        for (uint8_t x = 0; x < 26; x++)
        {
            const bool corner = (x < 3 || x > 22) && (y < 3 || y > 22);
            const bool shell = !corner && (x < 3 || y < 3 || y > 22);
            const bool bar = x >= 7 && x < 23 && (x - 7) % 6 < 4 &&
                y >= 17 - ((x - 7) / 6) * 4 && y < 20;
            if (shell || bar)
                UI_DrawPixelBuffer(gFrameBuffer, 12 + x, 12 + y, true);
        }
    CLEARUI_DrawNameAt("ClearUI", 47, 19, 128);
    GUI_DisplaySmallest("RADIO, SIMPLIFIED", 32, 45, false, true);
}

static void CLEARUI_DrawFrequencyHuge(uint8_t vfoNumber, uint8_t page)
{
    // Single-pane frequencies share the native face instead of stretched digits.
    CLEARUI_DrawFrequencyBig(vfoNumber, page * 8);
}

static void CLEARUI_DrawSignalMeter(uint8_t vfoNumber, uint8_t bottom,
                                 bool active)
{
    uint8_t level = gCurrentFunction == FUNCTION_TRANSMIT &&
                    gEeprom.TX_VFO == vfoNumber ? gClearUITxLevel :
                    gVFO_RSSI_bar_level[vfoNumber];
    const uint8_t pillWidth = 16;
    const bool memory = CLEARUI_IsMemory(vfoNumber);
    // Reuse the persisted SetMet bit: 0 = Spine, 1 = Ribbon. Both reserve
    // four number digits at the same x in A/B, independent of active size.
    const uint8_t pillX = gSetting_set_met ? 92 : 79;

    if (level > 6)
        level = 6;
    if (gSetting_set_met)
    {
        // Reserve the compact pane's mode label in every pane, so the meter
        // track and its fill scale keep the same horizontal position on A/B.
        const uint8_t left = 22;
        const uint8_t width = 89 - left;
        const uint8_t filled = ((uint16_t)width * level + 5) / 6;
        for (uint8_t x = 0; x < width; x++)
            if (x < filled)
                for (uint8_t row = 0; row < (active ? 3 : 2); row++)
                    UI_DrawPixelBuffer(gFrameBuffer, left + x, bottom - row, true);
            else if (x % 6 == 0)
                UI_DrawPixelBuffer(gFrameBuffer, left + x, bottom, true);
    }
    else
    {
        const uint8_t height = active ?
            (bottom == 55 && CLEARUI_IsSingleBand() ? 54 : 33) : 17;
        const uint8_t cellHeight = (height - 5) / 6;
        for (uint8_t bar = 0; bar < 6; bar++)
        {
            const uint8_t base = bottom - bar * (cellHeight + 1);
            for (uint8_t x = 0; x < 5; x++)
                for (uint8_t y = 0; y < cellHeight; y++)
                {
                    // Two-pixel outlines look filled: use a single ghost dot
                    // in compact panes, genuine hollow blocks in taller panes.
                    const bool ghost = cellHeight < 3 ? (x == 2 && y == 0) :
                        (x == 0 || x == 4 || y == 0 || y == cellHeight - 1);
                    if (bar < level || ghost)
                        UI_DrawPixelBuffer(gFrameBuffer, 121 + x, base - y, true);
                }
        }
    }

    const uint8_t pillY = bottom - (active ? 5 : 4);
    if (active)
        CLEARUI_DrawPill(memory ? "MR" : "VFO", pillX, pillY, pillWidth);
    else
        CLEARUI_DrawCompactPill(memory ? "MR" : "VFO", pillX, pillY,
                                pillWidth);
    if (memory)
    {
        char number[5];
        sprintf(number, "%03u", gEeprom.ScreenChannel[vfoNumber] + 1);
        GUI_DisplaySmallest(number, pillX + pillWidth + 2, pillY,
                            false, true);
    }
}

static void CLEARUI_SampleSignalMeter(void)
{
    if (gCurrentFunction == FUNCTION_TRANSMIT)
    {
#ifdef ENABLE_AUDIO_BAR
        // Reuse the active meter for microphone level without covering a pane.
        const uint16_t voice = BK4819_GetVoiceAmplitudeOut();
        uint32_t value = voice > 18 ? MIN((voice - 18u) * 16u, 32768u) : 0;
        uint8_t logarithm = 0;
        while (value >>= 1)
            logarithm++;
        static const uint8_t levels[16] = {0,0,0,0,0,0,1,1,1,2,2,3,4,5,6,6};
        gClearUITxLevel = gSetting_mic_bar ? levels[logarithm] : 0;
#else
        gClearUITxLevel = 0;
#endif
        if (gScreenToDisplay == DISPLAY_MAIN)
            gUpdateDisplay = true;
        return;
    }
    if (gCurrentFunction == FUNCTION_BAND_SCOPE ||
        (gCurrentFunction == FUNCTION_POWER_SAVE && gRxIdleMode))
        return;

    const uint8_t vfo = gEeprom.RX_VFO;
    const uint8_t band = gEeprom.VfoInfo[vfo].Band;
    const uint16_t rssi = BK4819_GetRSSI();
    uint8_t level;

    if (rssi >= gEEPROM_RSSI_CALIB[band][3])
        level = 6;
    else if (rssi >= gEEPROM_RSSI_CALIB[band][2])
        level = 4;
    else if (rssi >= gEEPROM_RSSI_CALIB[band][1])
        level = 2;
    else if (rssi >= gEEPROM_RSSI_CALIB[band][0])
        level = 1;
    else
        level = 0;

    if (gVFO_RSSI_bar_level[vfo] != level &&
        gScreenToDisplay == DISPLAY_MAIN)
        gUpdateDisplay = true;
    gVFO_RSSI_bar_level[vfo] = level;
}

void UI_CLEARUI_TimeSlice10ms(void)
{
    static uint8_t sampleCountdown;
    static uint8_t lastVfo = 0xFF;
    const uint8_t vfo = gEeprom.RX_VFO;

    if (lastVfo != vfo)
    {
        lastVfo = vfo;
        sampleCountdown = 5;
        return;
    }

    if (sampleCountdown > 0 && --sampleCountdown > 0)
        return;

    sampleCountdown = 5;
    CLEARUI_SampleSignalMeter();
}

static void CLEARUI_DrawStatusPill(const char *text)
{
    memset(gStatusLine, 0x7F, 20);
    gStatusLine[0] = gStatusLine[19] = 0x3E;
    GUI_DisplaySmallest(text, 2, 1, true, false);
}

static void CLEARUI_DrawCompactBattery(void)
{
    uint8_t *battery = gStatusLine + LCD_WIDTH - 10;
    const bool icon = gSetting_battery_text == 0 || gSetting_battery_text == 3;
    char text[7];
    memset(gStatusLine + 100, 0, 28);
    if (gBatteryDisplayLevel < 2 && gLowBatteryBlink)
        return;

    if (gSetting_battery_text != 0) {
        if (gSetting_battery_text == 1) {
            const uint16_t voltage = MIN(gBatteryVoltageAverage, 999);
            sprintf(text, "%u.%02uV", voltage / 100, voltage % 100);
        } else
            sprintf(text, "%u%%", MIN(BATTERY_VoltsToPercent(gBatteryVoltageAverage), 100));
        GUI_DisplaySmallest(text, (icon ? 116 : 128) - strlen(text) * 4,
                            1, true, true);
    }
    if (!icon) return;

    battery[0] = 0x3E;
    for (uint8_t x = 1; x <= 6; x++)
        battery[x] = 0x22;
    battery[7] = 0x3E;
    battery[8] = 0x1C;

    const uint8_t filled = MIN(gBatteryDisplayLevel, 6);
    for (uint8_t x = 0; x < filled; x++)
        battery[6 - x] = 0x3E;
}

static void CLEARUI_DrawCompactLock(void)
{
    if (gEeprom.KEY_LOCK)
        memcpy(gStatusLine + 90, gFontKeyLock, sizeof(gFontKeyLock));
}

static void CLEARUI_DrawStatusHeader(uint8_t vfoNumber)
{
    const VFO_Info_t *vfo = &gEeprom.VfoInfo[vfoNumber];
    memset(gStatusLine, 0, sizeof(gStatusLine));
    memset(gStatusLine, 0x7F, 13);
    gStatusLine[0] = gStatusLine[12] = 0x3E;
    GUI_DisplaySmallest(vfoNumber ? "B" : "A", 5, 1, true, false);
    GUI_DisplaySmallest(CLEARUI_ModeName(vfo), 20, 1, true, true);
    GUI_DisplaySmallest(CLEARUI_ToneName(vfo), 40, 1, true, true);
    GUI_DisplaySmallest(CLEARUI_PowerName(vfo), 80, 1, true, true);
    if (gCurrentFunction == FUNCTION_TRANSMIT)
        GUI_DisplaySmallest("TX", 60, 1, true, true);
    else if (FUNCTION_IsRx())
        GUI_DisplaySmallest(gEeprom.RX_VFO ? "RX B" : "RX A", 60, 1, true, true);
    CLEARUI_DrawCompactLock();
    CLEARUI_DrawCompactBattery();
}

static const char *CLEARUI_ScanListName(uint8_t list)
{
    static char name[17];

    if (list > MR_CHANNELS_LIST)
        return "All";
    if (list == 0)
        return "None";
    const char *savedName = CLEARUI_GetListName(list - 1);
    if (savedName[0] != '\0')
    {
        sprintf(name, "%.16s", savedName);
        return name;
    }

    sprintf(name, "List %02u", list);
    return name;
}

static void CLEARUI_DrawScanHeader(void)
{
    char text[32];

    memset(gStatusLine, 0, sizeof(gStatusLine));
    if (IS_MR_CHANNEL(gNextMrChannel))
        sprintf(text, "%.11s %s",
                CLEARUI_ScanListName(gEeprom.SCAN_LIST_DEFAULT),
                gScanStateDir > 0 ? "Up" : "Down");
    else
        sprintf(text, "VFO %s", gScanStateDir > 0 ? "Up" : "Down");

    GUI_DisplaySmallest(text, 24, 1, true, true);
    CLEARUI_DrawStatusPill("SCAN");
    CLEARUI_DrawCompactLock();
    CLEARUI_DrawCompactBattery();
}

static void CLEARUI_DrawDualAActive(void);
static void CLEARUI_DrawDualAInactive(void);
static void CLEARUI_DrawSinglePane(uint8_t vfoNumber);

static void CLEARUI_DrawScanPane(void)
{
    if (!CLEARUI_IsSingleBand())
    {
        if (gEeprom.TX_VFO == 0)
            CLEARUI_DrawDualAActive();
        else
            CLEARUI_DrawDualAInactive();
        return;
    }

    const uint8_t vfoNumber = gEeprom.RX_VFO;
    char text[32];
    CLEARUI_DrawSinglePane(vfoNumber);
    CLEARUI_Metadata(vfoNumber, text);
    GUI_DisplaySmallest(text, 0, 41, false, true);
    GUI_DisplaySmallest(FUNCTION_IsRx() ? "Busy" : "Scanning",
                        gSetting_set_met ? 96 : 80, 41, false, true);
}

static void CLEARUI_DrawDualActive(uint8_t vfoNumber, uint8_t top)
{
    char name[17];
    char text[32];

    CLEARUI_ChannelName(vfoNumber, name);
    CLEARUI_Frequency(vfoNumber, text);
    if (CLEARUI_IsMemory(vfoNumber) &&
        gEeprom.CHANNEL_DISPLAY_MODE != MDF_FREQUENCY)
    {
        if (gEeprom.CHANNEL_DISPLAY_MODE == MDF_FREQ_NAME)
        {
            CLEARUI_DrawSmallAt(name, 0, top + 2);
            CLEARUI_DrawFrequencyBig(vfoNumber, top + 13);
        }
        else
        {
            CLEARUI_DrawBigIdentity(name, top +
                (gEeprom.CHANNEL_DISPLAY_MODE == MDF_NAME ? 7 : 3));
            if (gEeprom.CHANNEL_DISPLAY_MODE == MDF_NAME_FREQ)
                CLEARUI_DrawSmallAt(text, 0, top + 20);
        }
    }
    else
    {
        CLEARUI_DrawFrequencyBig(vfoNumber, top + 7);
    }

    CLEARUI_DrawSignalMeter(vfoNumber, top + 34, true);
}

static void CLEARUI_DrawInactiveBody(uint8_t vfoNumber, uint8_t top)
{
    char name[17];
    char text[32];

    CLEARUI_ChannelName(vfoNumber, name);
    CLEARUI_Frequency(vfoNumber, text);
    if (CLEARUI_IsMemory(vfoNumber) &&
        gEeprom.CHANNEL_DISPLAY_MODE != MDF_FREQUENCY)
    {
        if (gEeprom.CHANNEL_DISPLAY_MODE == MDF_FREQ_NAME)
        {
            GUI_DisplaySmallest(name, 0, top + 1, false, true);
            CLEARUI_DrawSmallAt(text, 0, top + 7);
        }
        else
        {
            CLEARUI_DrawSmallAt(name, 0, top +
                (gEeprom.CHANNEL_DISPLAY_MODE == MDF_NAME ? 3 : 1));
            if (gEeprom.CHANNEL_DISPLAY_MODE == MDF_NAME_FREQ)
                GUI_DisplaySmallest(text, 0, top + 9, false, true);
        }
    }
    else
    {
        CLEARUI_DrawSmallAt(text, 0, top + 3);
    }

    // Keep mode out of the full-width name area; it fits left of the meter.
    GUI_DisplaySmallest(CLEARUI_ModeName(&gEeprom.VfoInfo[vfoNumber]),
                        0, top + 14, false, true);
    CLEARUI_DrawSignalMeter(vfoNumber, top + 18, false);
}

static void CLEARUI_DrawDualAActive(void)
{
    CLEARUI_DrawDualActive(0, 0);
    CLEARUI_DrawInactiveBody(1, 36);
}

static void CLEARUI_DrawDualAInactive(void)
{
    CLEARUI_DrawInactiveBody(0, 0);
    CLEARUI_DrawDualActive(1, 20);
}

static void CLEARUI_DrawSinglePane(uint8_t vfoNumber)
{
    char name[17];
    char text[32];

    CLEARUI_ChannelName(vfoNumber, name);
    CLEARUI_Frequency(vfoNumber, text);

    if (!CLEARUI_IsMemory(vfoNumber) ||
        gEeprom.CHANNEL_DISPLAY_MODE == MDF_FREQUENCY)
    {
        CLEARUI_DrawFrequencyBig(vfoNumber, 18);
    }
    else if (gEeprom.CHANNEL_DISPLAY_MODE == MDF_FREQ_NAME)
    {
        CLEARUI_DrawSmallAt(name, 0, 12);
        CLEARUI_DrawFrequencyBig(vfoNumber, 23);
    }
    else if (gEeprom.CHANNEL_DISPLAY_MODE == MDF_NAME)
    {
        CLEARUI_DrawBigIdentity(name, 18);
    }
    else
    {
        CLEARUI_DrawBigIdentity(name, 12);
        CLEARUI_DrawSmallAt(text, 0, 29);
    }

    CLEARUI_DrawSignalMeter(vfoNumber, 55, true);
}

static void CLEARUI_DrawToast(void)
{
    const char *text = gClearUIToast;

    if (gEeprom.KEY_LOCK && gKeypadLocked > 0)
        text = "Locked";
    else if (VfoState[gEeprom.TX_VFO] != VFO_STATE_NORMAL)
        text = VfoStateStr[VfoState[gEeprom.TX_VFO]];
    else if (gClearUIToastTicks == 0)
        return;

    memset(gFrameBuffer[5], 0, LCD_WIDTH);
    CLEARUI_DrawSmallCentered(text, 40);
    CLEARUI_InvertArea(40, 47);
}

static void CLEARUI_DrawInput(void)
{
    if (gInputBoxIndex == 0 && !gClearUINumericEntry)
        return;

    char text[12];
    const bool memory = CLEARUI_IsMemory(gEeprom.TX_VFO);
    const uint8_t decimal =
        gEeprom.VfoInfo[gEeprom.TX_VFO].pRX->Frequency >= _1GHz_in_KHz ? 4 : 3;
    uint8_t length = 0;
    for (uint8_t i = 0; i < (memory ? 4 : 8); i++)
    {
        if (!memory && i == decimal)
            text[length++] = '.';
        text[length++] = i < gInputBoxIndex ? '0' + gInputBox[i] : '-';
    }
    text[length] = '\0';
    memset(gFrameBuffer[2], 0, LCD_WIDTH * 2);
    CLEARUI_DrawNameAt(text, 0, 16, 128);
}

void UI_CLEARUI_RenderBackground(void)
{
    // During established reception the hardware is held on RX_VFO. Read it
    // here as well, so the first visible scan/dual-watch RX frame cannot
    // depend on a polling countdown left over from the previous VFO.
    if (gCurrentFunction == FUNCTION_RECEIVE ||
        gCurrentFunction == FUNCTION_MONITOR)
        CLEARUI_SampleSignalMeter();
    center_line = CENTER_LINE_NONE;
    if (gScanStateDir != SCAN_OFF)
        CLEARUI_DrawScanHeader();
    else
        CLEARUI_DrawStatusHeader(gEeprom.TX_VFO);
    UI_DisplayClear();

    if (gLowBattery && !gLowBatteryConfirmed)
    {
        UI_DisplayPopup("Low Battery");
        return;
    }

    if (gScanStateDir != SCAN_OFF)
    {
        CLEARUI_DrawScanPane();
        return;
    }

    if (CLEARUI_IsSingleBand())
    {
        CLEARUI_DrawSinglePane(gEeprom.TX_VFO);
    }
    else
    {
        if (gEeprom.TX_VFO == 0)
            CLEARUI_DrawDualAActive();
        else
            CLEARUI_DrawDualAInactive();
    }

    CLEARUI_DrawToast();
    CLEARUI_DrawInput();
}

void UI_DisplayClearUIMain(void)
{
    UI_CLEARUI_RenderBackground();
    ST7565_BlitStatusLine();
    ST7565_BlitFullScreen();
}

void UI_CLEARUI_TimeSlice500ms(void)
{
    if (gScreenToDisplay == DISPLAY_MAIN)
    {
        gClearUINameScroll++;
        if (gClearUIToastTicks > 0)
            gClearUIToastTicks--;
        UI_DisplayClearUIMain();
    }
}
