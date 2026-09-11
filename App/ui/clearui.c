/* SPDX-License-Identifier: Apache-2.0
 * Added for ClearUI in 2026.
 * ClearUI monochrome menu presentation for the 128x64 LCD.
 */

#include <string.h>

#include "app/clearui.h"
#include "driver/st7565.h"
#include "external/printf/printf.h"
#include "frequencies.h"
#include "functions.h"
#include "misc.h"
#include "radio.h"
#include "settings.h"
#include "ui/helper.h"
#include "ui/clearui.h"
#include "ui/clearui_text.h"
#include "ui/main.h"
#include "ui/menu.h"

#define CLEARUI_ALL_SETTINGS 0xFF

static const char *const MENU_CATEGORY_LABELS[CLEARUI_MENU_CATEGORY_COUNT] =
{
    "Radio", "Memory", "Scan", "Display", "Sound", "System"
};

/* Compact monochrome glyphs: radio, memory, scan, display, sound, tools. */
static const uint8_t MENU_CATEGORY_ICONS[CLEARUI_MENU_CATEGORY_COUNT][11] =
{
    {0x00, 0x7F, 0x41, 0x75, 0x51, 0x75, 0x41, 0x41, 0x7F, 0x00, 0x00},
    {0x7C, 0x46, 0x55, 0x55, 0x55, 0x46, 0x54, 0x44, 0x7C, 0x00, 0x00},
    {0x0C, 0x12, 0x21, 0x21, 0x21, 0x12, 0x2C, 0x60, 0x40, 0x00, 0x00},
    {0x1F, 0x11, 0x55, 0x51, 0x75, 0x71, 0x75, 0x51, 0x55, 0x11, 0x1F},
    {0x1C, 0x1C, 0x3E, 0x7F, 0x00, 0x14, 0x2A, 0x14, 0x08, 0x00, 0x00},
    {0x00, 0x1C, 0x5D, 0x36, 0x7F, 0x36, 0x5D, 0x1C, 0x00, 0x00, 0x00}
};

static const char *const QUICK_LABELS[CLEARUI_QUICK_COUNT] =
{
    "Transmit Power",
    "VFO or Memory",
    "Mode",
    "Bandwidth",
    "Group select",
    "Repeater Shift",
    "Tone",
    "Tuning Step",
    "Display",
    "Squelch",
    "Receive Compander",
    "Receive Audio",
    "Scope",
    "Band",
    "Temporary Skip",
    "Direction",
    "Stop Scan",
    "Enter frequency",
    "VOX",
    "Reverse",
    "HF Listen",
    "Watch other VFO"
};

static void UI_CLEARUI_InvertTile(uint8_t x1, uint8_t x2, uint8_t first, uint8_t last)
{
    for (uint8_t row = first; row <= last; row++)
        for (uint8_t x = x1; x <= x2; x++)
            gFrameBuffer[row][x] ^= 0xFF;
}

static const uint8_t MENU_NAME_IDS[] =
{
#ifdef ENABLE_FEAT_F4HWN_MULTIBOOT
    MENU_SET_CFG,
#endif
    MENU_STEP, MENU_TXP, MENU_OFFSET, MENU_W_N,
    MENU_MEM_CH, MENU_DEL_CH, MENU_MEM_NAME, MENU_LIST_CH,
    MENU_S_LIST, MENU_S_PRI, MENU_S_PRI_CH_1, MENU_S_PRI_CH_2,
    MENU_SC_REV, MENU_F1SHRT, MENU_F2SHRT, MENU_MIC_BAR,
    MENU_BEEP, MENU_ROGER, MENU_1_CALL, MENU_UPCODE, MENU_DWCODE,
    MENU_PTT_ID, MENU_VOX, MENU_VOL, MENU_AM, MENU_RESET, MENU_SET_NAV,
    MENU_SQL, MENU_TDR,
    MENU_R_CTCS, MENU_R_DCS, MENU_T_CTCS, MENU_T_DCS, MENU_SFT_D,
    MENU_BCL, MENU_MDF,
    MENU_PONMSG, MENU_ABR, MENU_ABR_MIN, MENU_ABR_MAX,
    MENU_ABR_ON_TX_RX, MENU_BAT_TXT, MENU_MIC,
    MENU_COMPAND, MENU_STE, MENU_RP_STE,
    MENU_D_ST, MENU_D_PRE, MENU_D_LIVE_DEC, MENU_AUTOLK,
    MENU_TOT, MENU_SAVE, MENU_F1LONG, MENU_F2LONG, MENU_MLONG,
    MENU_BATTYP,
    MENU_F_LOCK, MENU_350EN, MENU_BATCAL,
#ifdef ENABLE_AM_FIX
    MENU_AM_FIX,
#endif
#ifdef ENABLE_FEAT_F4HWN
    MENU_SET_INV, MENU_SET_MET, MENU_RX_FRAME, MENU_SET_GUI, MENU_SET_TMR,
#ifdef ENABLE_FEAT_F4HWN_AUDIO
    MENU_SET_AUD,
#endif
#ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
    MENU_SET_SCN,
#endif
#ifdef ENABLE_FEAT_F4HWN_LOGO_SAV
    MENU_SET_SAV,
#endif
#ifdef ENABLE_FEAT_F4HWN_VOL
    MENU_SET_VOL,
#endif
#ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
    MENU_SET_KEY,
#endif
    MENU_TX_LOCK, MENU_SET_PWR, MENU_SET_PTT, MENU_SET_TOT, MENU_SET_EOT,
    MENU_SET_CTR, MENU_SET_LCK,
    #ifdef ENABLE_FEAT_F4HWN_NARROWER
        MENU_SET_NFM,
    #endif
    #ifdef ENABLE_FEAT_F4HWN_SLEEP
        MENU_SET_OFF,
    #endif
#endif
};

static const char MENU_NAMES[] =
#ifdef ENABLE_FEAT_F4HWN_MULTIBOOT
    "Configuration bank\0"
#endif
    "Tuning step\0Transmit power\0Repeater offset\0Bandwidth\0"
    "Save channel\0Delete channel\0Channel name\0Channel group\0"
    "Group select\0Priority scan\0Priority channel 1\0Priority channel 2\0"
    "Scan resume\0Side key 1 tap\0Side key 2 tap\0Microphone meter\0"
    "Key sounds\0End-of-TX tone\0Call channel\0PTT start code\0PTT end code\0"
    "PTT identification\0VOX sensitivity\0System information\0Mode\0Reset\0Navigation keys\0"
    "Squelch\0Receive Mode\0Receive CTCSS\0Receive DCS\0"
    "Transmit CTCSS\0Transmit DCS\0Repeater Shift\0"
    "Busy Channel Lock\0Channel Display\0"
    "Startup Display\0Backlight Timeout\0Minimum Backlight\0"
    "Maximum Backlight\0Backlight Events\0Battery Readout\0"
    "Microphone Gain\0Compander\0"
    "Squelch Tail\0Repeater Tail\0"
    "DTMF Sidetone\0DTMF Preamble\0DTMF Live Decode\0Automatic Lock\0"
    "Transmit Timeout\0Battery Saver\0Side Key 1 Hold\0"
    "Side Key 2 Hold\0Menu Key Hold\0"
    "Battery Capacity\0Band Limits\0Enable 350 MHz\0"
    "Calibrate Battery\0"
#ifdef ENABLE_AM_FIX
    "AM Noise Control\0"
#endif
#ifdef ENABLE_FEAT_F4HWN
    "Invert display\0Meter style\0RX frame\0Display style\0Activity timer\0"
#ifdef ENABLE_FEAT_F4HWN_AUDIO
    "Receive audio\0"
#endif
#ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
    "Scan speed\0"
#endif
#ifdef ENABLE_FEAT_F4HWN_LOGO_SAV
    "Screen saver\0"
#endif
#ifdef ENABLE_FEAT_F4HWN_VOL
    "Audio volume\0"
#endif
#ifdef ENABLE_FEAT_F4HWN_RESCUE_OPS
    "Rescue key\0"
#endif
    "Transmit Lock\0Power Output Map\0Push-to-Talk Mode\0Timeout Alert\0"
    "End-of-TX Alert\0Display Contrast\0Lock Includes PTT\0"
    #ifdef ENABLE_FEAT_F4HWN_NARROWER
        "Narrow FM Width\0"
    #endif
    #ifdef ENABLE_FEAT_F4HWN_SLEEP
        "Power-Off Timer\0"
    #endif
#endif
;

const char *UI_CLEARUI_MenuItemName(uint8_t id)
{
    const char *name = MENU_NAMES;

    if (id == CLEARUI_ALL_SETTINGS)
        return "All Settings";
    if (id == CLEARUI_LIST_NAMES)
        return "Group names";
    if (id == CLEARUI_HF_LISTEN)
        return "HF Listen";

    for (uint8_t i = 0; i < sizeof(MENU_NAME_IDS); i++)
    {
        if (MENU_NAME_IDS[i] == id)
            return name;
        name += strlen(name) + 1;
    }

    return MenuList[UI_MENU_GetMenuIdx(id)].name;
}

static void UI_CLEARUI_Chevron(uint8_t centerY)
{
    for (uint8_t offset = 0; offset < 3; offset++)
    {
        UI_DrawPixelBuffer(gFrameBuffer, 114 - offset, centerY - offset, true);
        UI_DrawPixelBuffer(gFrameBuffer, 114 - offset, centerY + offset, true);
    }
}

static void UI_CLEARUI_QuickSubLabel(uint8_t selection, char *label)
{
    static const char *const POWER[] =
        {"Custom", "Low 1", "Low 2", "Low 3", "Low 4", "Low 5", "Mid", "High"};
    static const char *const OFF_ON[] = {"Off", "On"};
    static const char *const VFO_MEMORY[] = {"VFO", "Memory"};
    static const char *const BANDWIDTH[] = {"Wide", "Narrow"};
    static const char *const DUPLEX[] = {"Off", "Positive", "Negative"};
    static const char *const TONE[] =
        {"Off", "Transmit Tone", "Tone Squelch", "DCS", "Reverse DCS"};
    static const char *const DISPLAY[] =
        {"Frequency only", "Frequency large + name", "Name only", "Name large + frequency"};
    static const char *const AUDIO_FM[] =
        {"Flat", "Clean", "Mid", "Boost", "Max"};
    static const char *const AUDIO_AM[] =
        {"Sharp", "Stock", "Open"};

    switch (CLEARUI_QuickItemId(gClearUIQuickSelection))
    {
        case CLEARUI_QUICK_POWER:
            strcpy(label, POWER[selection]);
            break;
        case CLEARUI_QUICK_VOX:
            if (selection) sprintf(label, "Level %u", selection);
            else strcpy(label, "Off");
            break;
        case CLEARUI_QUICK_REVERSE:
            strcpy(label, OFF_ON[selection]);
            break;
        case CLEARUI_QUICK_VFO_MEMORY:
            strcpy(label, VFO_MEMORY[selection]);
            break;
        case CLEARUI_QUICK_MODE:
            strcpy(label, gModulationStr[selection]);
            break;
        case CLEARUI_QUICK_BANDWIDTH:
            strcpy(label, BANDWIDTH[selection]);
            break;
        case CLEARUI_QUICK_LIST:
        {
            const char *name = CLEARUI_GetListName(selection);
            if (selection >= MR_CHANNELS_LIST)
                strcpy(label, "All channels");
            else if (name[0] == '\0')
                sprintf(label, "Group %02u", selection + 1);
            else
                sprintf(label, "%02u %.16s", selection + 1, name);
            break;
        }
        case CLEARUI_QUICK_DUPLEX:
            strcpy(label, DUPLEX[selection]);
            break;
        case CLEARUI_QUICK_TSQL:
            strcpy(label, TONE[selection]);
            break;
        case CLEARUI_QUICK_STEP:
        {
            const uint16_t step = gStepFrequencyTable[
                FREQUENCY_GetStepIdxFromSortedIdx(selection)];
            sprintf(label, "%u.%02u kHz", step / 100, step % 100);
            break;
        }
        case CLEARUI_QUICK_DISPLAY:
            strcpy(label, DISPLAY[selection]);
            break;
        case CLEARUI_QUICK_SQUELCH:
            sprintf(label, "Level %u", selection);
            break;
        case CLEARUI_QUICK_RX_COMPAND:
            strcpy(label, OFF_ON[selection]);
            break;
        case CLEARUI_QUICK_RX_AUDIO:
            strcpy(label, gTxVfo->Modulation == MODULATION_AM
                        ? AUDIO_AM[selection] : AUDIO_FM[selection]);
            break;
        case CLEARUI_QUICK_BAND:
        {
            const uint8_t band = CLEARUI_QuickBandId(selection);
            const uint32_t lower = frequencyBandTable[band].lower / 100000;
            const uint32_t upper = frequencyBandTable[band].upper / 100000;
            sprintf(label, "%lu-%lu MHz", lower, upper);
            break;
        }
        case CLEARUI_QUICK_TEMP_SKIP:
        case CLEARUI_QUICK_SCAN_WATCH:
            strcpy(label, OFF_ON[selection]);
            break;
        case CLEARUI_QUICK_SCAN_DIRECTION:
            strcpy(label, selection ? "Upward" : "Downward");
            break;
        default:
            label[0] = '\0';
            break;
    }
}

static void UI_CLEARUI_DrawList(const char *title, const char *const *labels,
                        uint8_t count, uint8_t selection, bool chevrons,
                        bool window, bool scanList)
{
    const bool showTitle = title != NULL && title[0] != '\0';
    const uint8_t maximum = window ? (showTitle ? 4 : 5) : 6;
    const uint8_t visible = count < maximum ? count : maximum;
    const uint8_t titlePage = window ? 1 : 0;
    const uint8_t firstPage = window ? (showTitle ? 2 : 1) : 1;
    uint8_t first = 0;
    char position[8];

    if (count > visible)
    {
        if (selection > visible / 2)
            first = selection - visible / 2;
        if (first + visible > count)
            first = count - visible;
    }

    if (window)
    {
        for (uint8_t page = 1; page <= 5; page++)
            memset(gFrameBuffer[page] + 6, 0, 116);
        UI_DrawRectangleBuffer(gFrameBuffer, 5, 7, 122, 48, true);
    }
    else
        UI_DisplayClear();

    if (showTitle)
    {
        sprintf(position, "%02u/%02u", selection + 1, count);
        const uint8_t right = window ? 117 : 123;
        const uint8_t countX = right - UI_ClearTextWidth(position, 255);
        const uint8_t left = window ? 9 : 2;
        const bool showCount = UI_ClearTextWidth(title, 255) + left + 5 <= countX;
        UI_ClearText(title, left, showCount ? countX - 4 : right, titlePage, false);
        if (showCount)
            UI_ClearText(position, countX, right, titlePage, false);
    }

    for (uint8_t row = 0; row < visible; row++)
    {
        const uint8_t item = first + row;
        const uint8_t page = row + firstPage;
        char dynamicLabel[32];
        const char *label;

        if (scanList)
        {
            const char *name = item < MR_CHANNELS_LIST
                             ? CLEARUI_GetListName(item) : "";
            if (item >= MR_CHANNELS_LIST)
                strcpy(dynamicLabel, "All channels");
            else if (name[0] == '\0')
                sprintf(dynamicLabel, "Group %02u", item + 1);
            else
                sprintf(dynamicLabel, "%02u %.16s", item + 1, name);
            label = dynamicLabel;
        }
        else if (labels == NULL)
        {
            UI_CLEARUI_QuickSubLabel(item, dynamicLabel);
            label = dynamicLabel;
        }
        else
            label = labels[item];

        UI_ClearText(label, window ? 10 : 5,
                     chevrons ? 110 : (window ? 117 : 122), page, false);
        if (chevrons)
            UI_CLEARUI_Chevron((page * 8) + 3);
        if (item == selection)
            UI_CLEARUI_InvertTile(window ? 7 : 1, window ? 116 : 121,
                              page, page);
    }

    if (count > visible)
    {
        const uint8_t trackTop = window ? (showTitle ? 16 : 8) : 8;
        const uint8_t trackBottom = window ? 47 : 55;
        const uint8_t trackHeight = window ? (showTitle ? 32 : 40) : 48;
        const uint8_t trackX = window ? 120 : 126;
        const uint8_t thumbHeight = (trackHeight * visible) / count;
        const uint8_t thumbTop = trackTop +
            ((uint16_t)selection * (trackHeight - thumbHeight) / (count - 1));

        UI_DrawLineBuffer(gFrameBuffer, trackX, trackTop,
                          trackX, trackBottom, true);
        for (uint8_t x = trackX - 3; x <= trackX; x++)
            UI_DrawLineBuffer(gFrameBuffer, x, thumbTop,
                              x, thumbTop + thumbHeight - 1, true);
    }

}

static void UI_CLEARUI_List(const char *title, const char *const *labels,
                        uint8_t count, uint8_t selection, bool chevrons,
                        bool window, bool scanList)
{
    UI_CLEARUI_DrawList(title, labels, count, selection, chevrons, window, scanList);
    ST7565_BlitStatusLine();
    ST7565_BlitFullScreen();
}

void UI_CLEARUI_DrawScopeMenu(const char *title, const char *const *labels,
                            uint8_t count, uint8_t selection)
{
    // Scope owns incremental display transfers; only compose its overlay here.
    UI_CLEARUI_DrawList(title, labels, count, selection, title == NULL, true, false);
}

void UI_DisplayClearUIMenu(void)
{
    UI_CLEARUI_RenderBackground();

    if (!gClearUIMenuLevel)
    {
        UI_DisplayClear();
        UI_ClearText("Menu", 0, 128, 0, true);

        for (uint8_t i = 0; i < CLEARUI_MENU_CATEGORY_COUNT; i++)
        {
            const uint8_t column = i & 1;
            const uint8_t row = i >> 1;
            const uint8_t x1 = column ? 65 : 0;
            const uint8_t x2 = column ? 127 : 62;
            const uint8_t page = 1 + (row * 2);

            memcpy(gFrameBuffer[page] + x1 + 26,
                   MENU_CATEGORY_ICONS[i], 11);
            UI_ClearText(MENU_CATEGORY_LABELS[i], x1, x2 + 1, page + 1, true);
            if (i == gClearUIMenuCategory)
                UI_CLEARUI_InvertTile(x1, x2, page, page + 1);
        }

        ST7565_BlitStatusLine();
        ST7565_BlitFullScreen();
        return;
    }

    const uint8_t count = CLEARUI_MenuItemCount(gClearUIMenuCategory);
    const char *labels[24];

    for (uint8_t i = 0; i < count; i++)
        labels[i] = UI_CLEARUI_MenuItemName(
            CLEARUI_MenuItemId(gClearUIMenuCategory, i));

    UI_CLEARUI_List(MENU_CATEGORY_LABELS[gClearUIMenuCategory], labels,
                count, gClearUIMenuSelection, true, false, false);
}

void UI_DisplayClearUIQuick(void)
{
    const uint8_t item = CLEARUI_QuickItemId(gClearUIQuickSelection);

    UI_CLEARUI_RenderBackground();

    if (gClearUIQuickLevel)
        UI_CLEARUI_List(item == CLEARUI_QUICK_BAND ? "Band (VFO)" : QUICK_LABELS[item], NULL,
                    CLEARUI_QuickSubCount(), gClearUIQuickSubSelection,
                    false, true, false);
    else
    {
        const uint8_t count = CLEARUI_QuickItemCount();
        const char *labels[CLEARUI_QUICK_COUNT];

        for (uint8_t i = 0; i < count; i++)
        {
            const uint8_t id = CLEARUI_QuickItemId(i);
            labels[i] = id == CLEARUI_QUICK_ENTER &&
                        IS_MR_CHANNEL(gTxVfo->CHANNEL_SAVE)
                      ? "Go to channel" : QUICK_LABELS[id];
        }

        UI_CLEARUI_List(NULL, labels, count, gClearUIQuickSelection,
                        true, true, false);
    }
}

void UI_DisplayClearUIScanGroup(void)
{
    UI_CLEARUI_RenderBackground();

    if (gClearUIListNameEditor)
    {
        char title[16];
        char position[8];

        for (uint8_t page = 1; page <= 5; page++)
            memset(gFrameBuffer[page] + 6, 0, 116);
        UI_DrawRectangleBuffer(gFrameBuffer, 5, 7, 122, 48, true);
        sprintf(title, "Group name %02u", gClearUIScanSelection + 1);
        UI_ClearText(title, 9, 84, 1, false);
        UI_ClearText(gClearUIListEditName, 9, 119, 3, false);
        sprintf(position, "%02u/%02u", gClearUIListNameCursor + 1,
                CLEARUI_LIST_NAME_LENGTH);
        UI_ClearText(position, 86, 119, 1, false);
        const uint8_t cursorX = 9 + UI_ClearTextWidth(gClearUIListEditName,
                                  gClearUIListNameCursor) + !!gClearUIListNameCursor;
        UI_DrawLineBuffer(gFrameBuffer, cursorX, 32, cursorX + 3, 32, true);
        UI_ClearText("Star saves", 9, 119, 5, false);
        ST7565_BlitStatusLine();
        ST7565_BlitFullScreen();
        return;
    }

    if (gClearUIScanMemoryMode)
    {
        UI_CLEARUI_List(gClearUIEditingListNames ? "Group names" : "Group select",
                    NULL, MR_CHANNELS_LIST + !gClearUIEditingListNames,
                    gClearUIScanSelection,
                    false, true, true);
        return;
    }

    static const char *const VFO_SCAN[] = {"VFO Scan"};
    UI_CLEARUI_List("Scan", VFO_SCAN, 1, 0, false, true, false);
}
