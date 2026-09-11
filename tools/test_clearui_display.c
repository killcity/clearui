/* Host checks for the actual firmware renderer; no RF hardware is simulated. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "ui/clearui_main.c"

EEPROM_Config_t gEeprom;
uint8_t gStatusLine[128], gFrameBuffer[7][128];
uint8_t gVFO_RSSI_bar_level[2], gBatteryDisplayLevel = 6, gKeypadLocked;
uint16_t gEEPROM_RSSI_CALIB[7][4], gNextMrChannel;
bool gLowBatteryBlink, gLowBattery, gLowBatteryConfirmed, gRxIdleMode;
bool gUpdateDisplay;
bool gClearUINumericEntry;
bool gSetting_mic_bar, gSetting_set_met;
uint8_t gSetting_battery_text;
uint16_t gBatteryVoltageAverage = 800;
static unsigned fakePercent = 75;
unsigned int BATTERY_VoltsToPercent(unsigned int voltage) {(void)voltage; return fakePercent;}
int8_t gScanStateDir;
uint8_t CHFRSCANNER_Owner(void) { return 1; }
center_line_t center_line;
FUNCTION_Type_t gCurrentFunction;
GUI_DisplayType_t gScreenToDisplay;
VfoState_t VfoState[2];
const char *const VfoStateStr[] = {"", "Busy", "Low battery", "TX disabled",
                                  "Timeout", "Alarm", "High voltage"};
const char gModulationStr[MODULATION_UKNOWN][4] = {"FM", "AM", "USB"};
char gInputBox[8];
uint8_t gInputBoxIndex;
static uint16_t fakeRSSI;

uint16_t BK4819_GetRSSI(void) { return fakeRSSI; }
uint16_t BK4819_GetVoiceAmplitudeOut(void) { return fakeRSSI; }
bool FUNCTION_IsRx(void) { return gCurrentFunction == FUNCTION_RECEIVE; }
const char *CLEARUI_GetListName(uint8_t index) { (void)index; return "Public Safety"; }
void ST7565_BlitStatusLine(void) {}
void ST7565_BlitFullScreen(void) {}

static void snapshot(const char *directory, const char *name)
{
    char path[1024];
    snprintf(path, sizeof(path), "%s/%s.pgm", directory, name);
    FILE *out = fopen(path, "wb");
    assert(out);
    fputs("P5\n128 64\n255\n", out);
    for (unsigned y = 0; y < 64; y++)
        for (unsigned x = 0; x < 128; x++)
        {
            const uint8_t col = y < 8 ? gStatusLine[x] : gFrameBuffer[(y - 8) / 8][x];
            fputc(col & (1u << (y % 8)) ? 0 : 255, out);
        }
    fclose(out);
}

static void inactive_pixels(uint8_t top, uint8_t *pixels)
{
    for (unsigned y = 0; y < 19; y++)
        for (unsigned x = 0; x < 128; x++)
            *pixels++ = !!(gFrameBuffer[(top + y) / 8][x] & (1u << ((top + y) % 8)));
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    UI_CLEARUI_RenderBootLogo();
    snapshot(argv[1], "boot-logo");
    // Names and both VFO layouts must use the same native numeric face.
    uint8_t digit_reference[sizeof(gFrameBuffer)];
    gEeprom.VfoInfo[0].pRX = &gEeprom.VfoInfo[0].freq_config_RX;
    for (char digit = '0'; digit <= '9'; digit++)
    {
        char text[12];
        const uint32_t frequency = (digit - '0') * 11111100u;
        gEeprom.VfoInfo[0].pRX->Frequency = frequency;
        sprintf(text, "%u.%03u", frequency / 100000, frequency / 100 % 1000);
        UI_DisplayClear(); CLEARUI_DrawFrequencyBig(0, 0);
        memcpy(digit_reference, gFrameBuffer, sizeof(gFrameBuffer));
        UI_DisplayClear(); CLEARUI_DrawNameAt(text, 0, 0, 128);
        assert(memcmp(digit_reference, gFrameBuffer, sizeof(gFrameBuffer)) == 0);
        UI_DisplayClear(); CLEARUI_DrawFrequencyHuge(0, 0);
        assert(memcmp(digit_reference, gFrameBuffer, sizeof(gFrameBuffer)) == 0);
        assert(CLEARUI_NameWidth((char[]){digit, '\0'}) == 9);
    }
    // Ambiguous identifiers must remain distinct, in both optical sizes.
    const char pairs[][2] = {{'0','O'}, {'1','I'}, {'1','l'}, {'I','l'}};
    for (unsigned i = 0; i < sizeof(pairs) / sizeof(*pairs); i++)
    {
        for (unsigned small = 0; small < 2; small++)
        {
            UI_DisplayClear();
            const char a[] = {pairs[i][0], '\0'}, b[] = {pairs[i][1], '\0'};
            if (small) CLEARUI_DrawSmallAt(a, 0, 0); else CLEARUI_DrawNameAt(a, 0, 0, 128);
            memcpy(digit_reference, gFrameBuffer, sizeof(gFrameBuffer));
            UI_DisplayClear();
            if (small) CLEARUI_DrawSmallAt(b, 0, 0); else CLEARUI_DrawNameAt(b, 0, 0, 128);
            assert(memcmp(digit_reference, gFrameBuffer, sizeof(gFrameBuffer)) != 0);
        }
    }
    // Printable alphabet, punctuation, descenders, and left/right clipping.
    for (char glyph = ' '; glyph < 127; glyph++)
    {
        const char text[] = {glyph, '\0'};
        assert(CLEARUI_NameWidth(text) > 0);
        UI_DisplayClear(); CLEARUI_DrawNameAt(text, -5, 38, 127);
        CLEARUI_DrawNameAt(text, 123, 0, 128);
        CLEARUI_DrawSmallAt(text, 122, 48);
    }
    UI_DisplayClear();
    memset(gStatusLine, 0, sizeof(gStatusLine));
    CLEARUI_DrawNameAt("K1JC 0123", 0, 0, 128);
    CLEARUI_DrawNameAt("Chester 45", 0, 19, 128);
    CLEARUI_DrawNameAt("g j p q y", 0, 38, 128);
    snapshot(argv[1], "radio-font");
    for (unsigned v = 0; v < 2; v++)
    {
        VFO_Info_t *info = &gEeprom.VfoInfo[v];
        info->pRX = &info->freq_config_RX;
        info->pTX = &info->freq_config_TX;
        info->pRX->Frequency = v ? 44275000 : 14547000;
        info->pTX->Frequency = info->pRX->Frequency;
        info->Modulation = MODULATION_FM;
        info->OUTPUT_POWER = OUTPUT_POWER_HIGH;
        strcpy(info->Name, v ? "Relay One" : "Hilltop NW");
        gEeprom.ScreenChannel[v] = v ? 1023 : 5;
    }
    gEeprom.CHANNEL_DISPLAY_MODE = MDF_NAME_FREQ;
    gEeprom.DUAL_WATCH = DUAL_WATCH_CHAN_A;
    gVFO_RSSI_bar_level[0] = 4;
    // Empty meter ghosts must be distinguishable from the first filled level,
    // and strength must add pixels monotonically in both pane sizes/styles.
    for (unsigned style = 0; style < 2; style++)
    for (unsigned active = 0; active < 2; active++)
    {
        unsigned previous = 0;
        gSetting_set_met = style;
        for (unsigned level = 0; level <= 6; level++)
        {
            unsigned count = 0;
            gVFO_RSSI_bar_level[0] = level;
            UI_DisplayClear(); CLEARUI_DrawSignalMeter(0, 55, active);
            for (unsigned y = 0; y < 56; y++)
            for (unsigned x = style ? 0 : 121; x < (style ? 89 : 126); x++)
                count += !!(gFrameBuffer[y / 8][x] & (1u << (y % 8)));
            assert(count > previous);
            previous = count;
        }
    }
    // Ribbon has the same track and fill endpoints in both pane sizes and
    // positions at every level. Only its thickness changes with selection.
    gSetting_set_met = true;
    for (unsigned level = 0; level <= 6; level++)
    {
        uint8_t reference[89];
        gVFO_RSSI_bar_level[0] = level;
        UI_DisplayClear(); CLEARUI_DrawSignalMeter(0, 34, true);
        for (unsigned x = 0; x < 89; x++)
            reference[x] = !!(gFrameBuffer[34 / 8][x] & (1u << (34 % 8)));
        assert(reference[22]);
        for (unsigned x = 0; x < 22; x++) assert(!reference[x]);
        if (level == 6) assert(reference[88]);
        for (unsigned pane = 0; pane < 4; pane++)
        {
            const unsigned bottom = (unsigned[]){18,34,54,55}[pane];
            for (unsigned active = 0; active < 2; active++)
            {
                UI_DisplayClear(); CLEARUI_DrawSignalMeter(0, bottom, active);
                for (unsigned x = 0; x < 89; x++)
                    assert(reference[x] == !!(gFrameBuffer[bottom / 8][x] &
                                              (1u << (bottom % 8))));
            }
        }
    }
    gSetting_set_met = false;
    gVFO_RSSI_bar_level[1] = 6;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "dual-a");
    gEeprom.TX_VFO = 1;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "dual-b");
    gEeprom.DUAL_WATCH = DUAL_WATCH_OFF;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "single-memory");
    gEeprom.ScreenChannel[1] = FREQ_CHANNEL_FIRST;
    char name[17];
    CLEARUI_ChannelName(1, name);
    assert(strcmp(name, "VFO B") == 0);
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "single-frequency");

    // Reproduce the user's two named panes and both active positions.
    gEeprom.ScreenChannel[0] = 0;
    gEeprom.ScreenChannel[1] = 65;
    strcpy(gEeprom.VfoInfo[0].Name, "Relay One");
    strcpy(gEeprom.VfoInfo[1].Name, "Lake View");
    gEeprom.VfoInfo[0].pRX->Frequency = 44275000;
    gEeprom.VfoInfo[1].pRX->Frequency = 15585000;
    gEeprom.DUAL_WATCH = DUAL_WATCH_CHAN_A;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "user-dual-b");
    gEeprom.TX_VFO = 0;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "user-dual-a");
    gEeprom.DUAL_WATCH = DUAL_WATCH_OFF;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "user-single");
    for (unsigned mode = 0; mode < 4; mode++)
    {
        char label[32];
        gEeprom.CHANNEL_DISPLAY_MODE = mode;
        for (unsigned single = 0; single < 2; single++)
        {
            gEeprom.DUAL_WATCH = single ? DUAL_WATCH_OFF : DUAL_WATCH_CHAN_A;
            snprintf(label, sizeof(label), "mode-%u-%s", mode, single ? "single" : "dual");
            UI_CLEARUI_RenderBackground(); snapshot(argv[1], label);
        }
    }
    gEeprom.CHANNEL_DISPLAY_MODE = MDF_NAME_FREQ;
    gEeprom.DUAL_WATCH = DUAL_WATCH_OFF;
    for (unsigned mode = 0; mode < 4; mode++)
    for (unsigned active = 0; active < 2; active++)
    {
        char label[40];
        gEeprom.CHANNEL_DISPLAY_MODE = mode;
        gEeprom.TX_VFO = active;
        gEeprom.DUAL_WATCH = DUAL_WATCH_CHAN_A;
        snprintf(label, sizeof(label), "design-mode-%u-active-%u", mode, active);
        UI_CLEARUI_RenderBackground(); snapshot(argv[1], label);
    }
    gEeprom.CHANNEL_DISPLAY_MODE = MDF_NAME_FREQ;
    gEeprom.DUAL_WATCH = DUAL_WATCH_OFF;
    gEeprom.TX_VFO = 0;
    // GHz plus fractional-kHz suffix must not be lost at the new size.
    gEeprom.ScreenChannel[0] = FREQ_CHANNEL_FIRST;
    gEeprom.VfoInfo[0].pRX->Frequency = 129999875;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "precision-frequency");

    // A compact pane must render identically at the top and bottom.
    uint8_t top[19 * 128], bottom[19 * 128];
    UI_DisplayClear(); CLEARUI_DrawInactiveBody(0, 0); inactive_pixels(0, top);
    UI_DisplayClear(); CLEARUI_DrawInactiveBody(0, 36); inactive_pixels(36, bottom);
    assert(memcmp(top, bottom, sizeof(top)) == 0);
    // Native glyphs must leave a blank pixel row after the pane divider.
    for (unsigned x = 0; x < 128; x++) assert(top[x] == 0);
    UI_DisplayClear(); CLEARUI_DrawDualActive(1, 20);
    for (unsigned x = 0; x < 128; x++) assert(!(gFrameBuffer[20 / 8][x] & (1u << (20 % 8))));

    // The last memory and a VFO are not confused by 8-bit truncation.
    gEeprom.ScreenChannel[0] = 1023;
    strcpy(gEeprom.VfoInfo[0].Name, "Memory 1024");
    CLEARUI_ChannelName(0, name); assert(strcmp(name, "Memory 1024") == 0);
    gEeprom.ScreenChannel[0] = FREQ_CHANNEL_FIRST;
    CLEARUI_ChannelName(0, name); assert(strcmp(name, "VFO A") == 0);

    // One receiver's RSSI sample must not erase the other pane's sample.
    for (unsigned i = 0; i < 4; i++) gEEPROM_RSSI_CALIB[0][i] = 50 + i * 50;
    gEeprom.RX_VFO = 1; fakeRSSI = 250; CLEARUI_SampleSignalMeter();
    assert(gVFO_RSSI_bar_level[1] == 6);
    gEeprom.RX_VFO = 0; fakeRSSI = 0; CLEARUI_SampleSignalMeter();
    assert(gVFO_RSSI_bar_level[0] == 0 && gVFO_RSSI_bar_level[1] == 6);

    // Paused scan reception must request a redraw on rising/falling RSSI,
    // without waiting for the 500 ms name-scroll timer or erasing the sub VFO.
    gScreenToDisplay = DISPLAY_MAIN;
    gScanStateDir = 1;
    gCurrentFunction = FUNCTION_RECEIVE;
    gNextMrChannel = gEeprom.ScreenChannel[0] = 0;
    gEeprom.VfoInfo[0].pRX->Frequency = 44275000;
    strcpy(gEeprom.VfoInfo[0].Name, "Relay One");
    for (unsigned active = 0; active < 2; active++)
    for (unsigned single = 0; single < 2; single++)
    {
        gEeprom.RX_VFO = gEeprom.TX_VFO = active;
        gEeprom.DUAL_WATCH = single ? DUAL_WATCH_OFF : DUAL_WATCH_CHAN_A;
        fakeRSSI = 0;
        for (unsigned t = 0; t < 6; t++) UI_CLEARUI_TimeSlice10ms();
        assert(gVFO_RSSI_bar_level[active] == 0);
        gUpdateDisplay = false; fakeRSSI = 250;
        for (unsigned t = 0; t < 5; t++) UI_CLEARUI_TimeSlice10ms();
        assert(gVFO_RSSI_bar_level[active] == 6 && gUpdateDisplay);
        UI_CLEARUI_RenderBackground();
        char label[32];
        snprintf(label, sizeof(label), "scan-busy-%u-%s", active, single ? "single" : "dual");
        snapshot(argv[1], label);
        gUpdateDisplay = false;
        CLEARUI_SampleSignalMeter(); assert(!gUpdateDisplay); // unchanged
        fakeRSSI = 0; CLEARUI_SampleSignalMeter(); assert(gUpdateDisplay);
    }
    // Do not dismiss an open menu just because received strength changes.
    gScreenToDisplay = DISPLAY_MENU; gUpdateDisplay = false;
    fakeRSSI = 250; CLEARUI_SampleSignalMeter(); assert(!gUpdateDisplay);
    gScreenToDisplay = DISPLAY_MAIN; gScanStateDir = SCAN_OFF;
    // Selection and reception are independent: B can be heard while A is
    // large, and conversely. Even level 1 must rise above the empty baseline.
    gCurrentFunction = FUNCTION_RECEIVE;
    gEeprom.DUAL_WATCH = DUAL_WATCH_CHAN_A;
    // First receive frame must work even before a new VFO's 50 ms poll.
    for (unsigned selected = 0; selected < 2; selected++)
    for (unsigned receiving = 0; receiving < 2; receiving++)
    {
        gEeprom.TX_VFO = selected; gEeprom.RX_VFO = receiving;
        gVFO_RSSI_bar_level[0] = gVFO_RSSI_bar_level[1] = 0;
        fakeRSSI = 250;
        UI_CLEARUI_RenderBackground();
        assert(gVFO_RSSI_bar_level[receiving] == 6);
        assert(gVFO_RSSI_bar_level[!receiving] == 0);
    }
    for (unsigned selected = 0; selected < 2; selected++)
    {
        const unsigned receiving = !selected;
        gEeprom.TX_VFO = selected;
        gEeprom.RX_VFO = receiving;
        gVFO_RSSI_bar_level[selected] = 0;
        fakeRSSI = 75;
        for (unsigned t = 0; t < 6; t++) UI_CLEARUI_TimeSlice10ms();
        assert(gVFO_RSSI_bar_level[receiving] == 1);
        assert(gVFO_RSSI_bar_level[selected] == 0);
        UI_CLEARUI_RenderBackground();
        const unsigned y = selected == 0 ? 53 : 17;
        assert(gFrameBuffer[y / 8][121] & (1u << (y % 8)));
        char label[32];
        snprintf(label, sizeof(label), "sub-vfo-%u-receiving", receiving);
        snapshot(argv[1], label);
    }
    // MR/VFO badges share a fixed x origin across sizes and number lengths.
    for (unsigned style = 0; style < 2; style++)
    for (unsigned active = 0; active < 2; active++)
    for (unsigned c = 0; c < 3; c++)
    {
        gSetting_set_met = style;
        gEeprom.ScreenChannel[0] = (uint16_t[]){0,1023,FREQ_CHANNEL_FIRST}[c];
        UI_DisplayClear(); CLEARUI_DrawSignalMeter(0, 55, active);
        const unsigned y = 55 - (active ? 5 : 4) + 1;
        const unsigned x = style ? 92 : 79;
        assert(gFrameBuffer[y / 8][x] & (1u << (y % 8)));
        assert(!(gFrameBuffer[y / 8][x - 1] & (1u << (y % 8))));
    }
    gVFO_RSSI_bar_level[1] = 6;

    gCurrentFunction = FUNCTION_TRANSMIT;
    gSetting_mic_bar = true;
    fakeRSSI = 0; CLEARUI_SampleSignalMeter(); assert(gClearUITxLevel == 0);
    fakeRSSI = 65535; CLEARUI_SampleSignalMeter(); assert(gClearUITxLevel == 6);
    gSetting_mic_bar = false;
    CLEARUI_SampleSignalMeter(); assert(gClearUITxLevel == 0);
    assert(gVFO_RSSI_bar_level[1] == 6);
    gCurrentFunction = FUNCTION_FOREGROUND;

    // Exercise layout bounds, four-digit memory numbers, scrolling and input.
    const uint16_t channels[] = {0, 255, 256, 999, 1023, FREQ_CHANNEL_FIRST};
    for (unsigned style = 0; style < 2; style++)
    for (unsigned c = 0; c < sizeof(channels) / sizeof(*channels); c++)
    for (unsigned active = 0; active < 2; active++)
    for (unsigned single = 0; single < 2; single++)
    for (unsigned level = 0; level < 7; level++)
    for (unsigned mode = 0; mode < 4; mode++)
    {
        gSetting_set_met = style;
        gEeprom.CHANNEL_DISPLAY_MODE = mode;
        gEeprom.ScreenChannel[active] = channels[c];
        gEeprom.TX_VFO = active;
        gEeprom.DUAL_WATCH = single ? DUAL_WATCH_OFF : DUAL_WATCH_CHAN_A;
        memset(gEeprom.VfoInfo[active].Name, 'W', 16);
        gVFO_RSSI_bar_level[active] = level;
        gClearUINameScroll = level * 17;
        UI_CLEARUI_RenderBackground();
    }
    // Release previews, every pane position/style and the single-pane layout.
    gCurrentFunction = FUNCTION_FOREGROUND;
    gEeprom.CHANNEL_DISPLAY_MODE = MDF_NAME_FREQ;
    gEeprom.ScreenChannel[0] = 0; gEeprom.ScreenChannel[1] = 65;
    strcpy(gEeprom.VfoInfo[0].Name, "Relay One");
    strcpy(gEeprom.VfoInfo[1].Name, "Lake View");
    gEeprom.VfoInfo[0].pRX->Frequency = 44275000;
    gEeprom.VfoInfo[1].pRX->Frequency = 15585000;
    gVFO_RSSI_bar_level[0] = 1; gVFO_RSSI_bar_level[1] = 4;
    for (unsigned style = 0; style < 2; style++)
    for (unsigned active = 0; active < 2; active++)
    for (unsigned single = 0; single < 2; single++)
    {
        char label[40];
        gSetting_set_met = style;
        gEeprom.TX_VFO = active;
        gEeprom.DUAL_WATCH = single ? DUAL_WATCH_OFF : DUAL_WATCH_CHAN_A;
        snprintf(label, sizeof(label), "%s-%u-%s", style ? "ribbon" : "spine", active, single ? "single" : "dual");
        UI_CLEARUI_RenderBackground(); snapshot(argv[1], label);
    }
    gEeprom.KEY_LOCK = true; gKeypadLocked = 4;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "locked");
    gInputBoxIndex = 2; gInputBox[0] = 1; gInputBox[1] = 4;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "frequency-entry");
    gInputBoxIndex = 0; gKeypadLocked = 0; gEeprom.KEY_LOCK = false;
    // Battery-only formats never draw an icon. Both remains compact even at
    // 100%, and battery drawing cannot overwrite lock/RX/power columns.
    for (unsigned mode=0; mode<4; mode++) {
        gSetting_battery_text=mode; fakePercent=100;
        memset(gStatusLine,0x55,sizeof(gStatusLine));
        CLEARUI_DrawCompactBattery();
        for(unsigned x=0;x<100;x++) assert(gStatusLine[x]==0x55);
        const unsigned right=mode==3 ? 116 : 128;
        uint8_t expected[28]; memcpy(expected,gStatusLine+100,28);
        memset(gStatusLine+100,0,28);
        if(mode) GUI_DisplaySmallest(mode==1 ? "8.00V" : "100%",
                                    right-(mode==1 ? 5 : 4)*4,1,true,true);
        if(mode==0 || mode==3) {
            assert(expected[18]==0x3e && expected[25]==0x3e);
            memcpy(gStatusLine+118,expected+18,10);
        }
        assert(memcmp(expected,gStatusLine+100,28)==0);
        UI_CLEARUI_RenderBackground();
        char label[32]; snprintf(label,sizeof(label),"battery-%u",mode); snapshot(argv[1],label);
        gBatteryDisplayLevel=1; gLowBatteryBlink=true;
        CLEARUI_DrawCompactBattery();
        for(unsigned x=100;x<128;x++) assert(gStatusLine[x]==0);
        gBatteryDisplayLevel=6; gLowBatteryBlink=false;
    }
    gSetting_battery_text=0;
    gClearUINumericEntry = true;
    UI_CLEARUI_RenderBackground(); snapshot(argv[1], "entry-start");
    puts("Display checks passed: matching native VFO/name digits, distinct 0/O and 1/I/l, ASCII and descenders, pane symmetry, channel 1024, RSSI isolation, layout bounds.");
    return 0;
}
