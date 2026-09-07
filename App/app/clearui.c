/*
 * SPDX-License-Identifier: Apache-2.0
 * Added for ClearUI in 2026.
 *
 * ClearUI interaction layer for the Fusion v5.9 firmware.
 *
 * Short M opens Quick Menu and holding M opens the icon Menu.  Short * starts
 * or stops scanning; holding * opens the context-sensitive scan chooser.
 * F+* remains the existing CTCSS/DCS scan shortcut.
 */

#include "app/clearui.h"

#include "app/action.h"
#include "app/chFrScanner.h"
#include "app/common.h"
#include "app/generic.h"
#include "app/menu.h"
#include "driver/py25q16.h"
#ifdef ENABLE_SPECTRUM
    #include "app/spectrum.h"
#endif
#include "audio.h"
#include "misc.h"
#include "radio.h"
#include "settings.h"
#include "ui/menu.h"
#include "ui/main.h"
#include "ui/ui.h"

#ifndef ARRAY_SIZE
    #define ARRAY_SIZE(x) (sizeof(x) / sizeof(x[0]))
#endif

#define CLEARUI_ALL_SETTINGS 0xFF
#define CLEARUI_LIST_STORE_ADDRESS 0x012000u
#define CLEARUI_LIST_STORE_VERSION 1u

uint8_t gClearUIQuickSelection;
uint8_t gClearUIQuickSubSelection;
uint8_t gClearUIQuickLevel;
uint8_t gClearUIQuickContext;
bool    gClearUIQuickScanMemory;
static uint8_t gClearUIQuickDirectItem = CLEARUI_QUICK_COUNT;
bool    gClearUINumericEntry;
uint8_t gClearUIScanSelection;
bool    gClearUIScanMemoryMode;
bool    gClearUIListPickOnly;
uint8_t gClearUIMenuCategory;
uint8_t gClearUIMenuSelection;
uint8_t gClearUIMenuLevel;
bool    gClearUIEditorActive;
bool    gClearUIPendingEditor;
bool    gClearUIIgnoreNextRelease;
uint8_t gClearUIEditorReturnDisplay;
bool    gClearUIEditingListNames;
bool    gClearUIListNameEditor;
uint8_t gClearUIListNameCursor;
char    gClearUIListEditName[CLEARUI_LIST_NAME_LENGTH + 1];

typedef struct __attribute__((packed))
{
    char magic[3];
    uint8_t version;
    char name[MR_CHANNELS_LIST][CLEARUI_LIST_NAME_LENGTH + 1];
} ClearUIListStore_t;

static ClearUIListStore_t gClearUIListStore;
static bool gClearUIListNamesLoaded;

static uint8_t gClearUIQuickLastSelection[CLEARUI_QUICK_CONTEXT_COUNT];

void CLEARUI_LoadListNames(void)
{
    if (gClearUIListNamesLoaded)
        return;

    PY25Q16_ReadBuffer(CLEARUI_LIST_STORE_ADDRESS, &gClearUIListStore,
                       sizeof(gClearUIListStore));
    if (memcmp(gClearUIListStore.magic, "CUI", 3) != 0 ||
        gClearUIListStore.version != CLEARUI_LIST_STORE_VERSION)
    {
        memset(&gClearUIListStore, 0, sizeof(gClearUIListStore));
        memcpy(gClearUIListStore.magic, "CUI", 3);
        gClearUIListStore.version = CLEARUI_LIST_STORE_VERSION;

        for (uint8_t list = 0; list < MR_CHANNELS_LIST; list++)
        {
            for (uint8_t i = 0; i < sizeof(gListName[0]) - 1; i++)
            {
                const uint8_t c = gListName[list][i];
                if (c < 32 || c > 126)
                    break;
                gClearUIListStore.name[list][i] = c;
            }
        }
    }

    for (uint8_t list = 0; list < MR_CHANNELS_LIST; list++)
    {
        for (uint8_t i = 0; i < CLEARUI_LIST_NAME_LENGTH; i++)
        {
            const uint8_t c = gClearUIListStore.name[list][i];
            if (c < 32 || c > 126)
            {
                gClearUIListStore.name[list][i] = '\0';
                break;
            }
        }
        gClearUIListStore.name[list][CLEARUI_LIST_NAME_LENGTH] = '\0';
    }
    gClearUIListNamesLoaded = true;
}

const char *CLEARUI_GetListName(uint8_t listIndex)
{
    CLEARUI_LoadListNames();
    return listIndex < MR_CHANNELS_LIST
         ? gClearUIListStore.name[listIndex] : "";
}

void CLEARUI_SaveListName(uint8_t listIndex, const char *name)
{
    if (listIndex >= MR_CHANNELS_LIST)
        return;

    CLEARUI_LoadListNames();
    memset(gClearUIListStore.name[listIndex], 0,
           sizeof(gClearUIListStore.name[listIndex]));
    strncpy(gClearUIListStore.name[listIndex], name,
            CLEARUI_LIST_NAME_LENGTH);

    for (int8_t i = CLEARUI_LIST_NAME_LENGTH - 1;
         i >= 0 && gClearUIListStore.name[listIndex][i] == ' '; i--)
        gClearUIListStore.name[listIndex][i] = '\0';

    memset(gListName[listIndex], 0, sizeof(gListName[listIndex]));
    strncpy(gListName[listIndex], gClearUIListStore.name[listIndex],
            sizeof(gListName[listIndex]) - 1);

    PY25Q16_WriteBuffer(CLEARUI_LIST_STORE_ADDRESS, &gClearUIListStore,
                       sizeof(gClearUIListStore), false);
    PY25Q16_WriteBuffer(0x00880E, gListName, sizeof(gListName), false);
}

static const uint8_t CLEARUI_QUICK_MEMORY_ITEMS[] =
{
    CLEARUI_QUICK_LIST,
    CLEARUI_QUICK_ENTER,
    CLEARUI_QUICK_WATERFALL,
    CLEARUI_QUICK_TEMP_SKIP,
    CLEARUI_QUICK_TSQL,
    CLEARUI_QUICK_DUPLEX,
    CLEARUI_QUICK_POWER,
    CLEARUI_QUICK_RX_COMPAND,
    CLEARUI_QUICK_RX_AUDIO,
    CLEARUI_QUICK_DISPLAY,
    CLEARUI_QUICK_SQUELCH,
    CLEARUI_QUICK_VFO_MEMORY
};

static const uint8_t CLEARUI_QUICK_VFO_ITEMS[] =
{
    CLEARUI_QUICK_BAND,
    CLEARUI_QUICK_ENTER,
    CLEARUI_QUICK_WATERFALL,
    CLEARUI_QUICK_STEP,
    CLEARUI_QUICK_MODE,
    CLEARUI_QUICK_BANDWIDTH,
    CLEARUI_QUICK_TSQL,
    CLEARUI_QUICK_DUPLEX,
    CLEARUI_QUICK_POWER,
    CLEARUI_QUICK_RX_COMPAND,
    CLEARUI_QUICK_RX_AUDIO,
    CLEARUI_QUICK_SQUELCH,
    CLEARUI_QUICK_VFO_MEMORY
};

static const uint8_t CLEARUI_QUICK_SCAN_MEMORY_ITEMS[] =
{
    CLEARUI_QUICK_TEMP_SKIP,
    CLEARUI_QUICK_LIST,
    CLEARUI_QUICK_SCAN_DIRECTION,
    CLEARUI_QUICK_SCAN_STOP
};

static const uint8_t CLEARUI_QUICK_SCAN_VFO_ITEMS[] =
{
    CLEARUI_QUICK_SCAN_DIRECTION,
    CLEARUI_QUICK_SCAN_STOP
};

static const uint8_t *CLEARUI_QuickItems(uint8_t *count)
{
    if (gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_SCAN)
    {
        if (gClearUIQuickScanMemory)
        {
            *count = ARRAY_SIZE(CLEARUI_QUICK_SCAN_MEMORY_ITEMS);
            return CLEARUI_QUICK_SCAN_MEMORY_ITEMS;
        }

        *count = ARRAY_SIZE(CLEARUI_QUICK_SCAN_VFO_ITEMS);
        return CLEARUI_QUICK_SCAN_VFO_ITEMS;
    }

    if (gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_MEMORY)
    {
        *count = ARRAY_SIZE(CLEARUI_QUICK_MEMORY_ITEMS);
        return CLEARUI_QUICK_MEMORY_ITEMS;
    }

    *count = ARRAY_SIZE(CLEARUI_QUICK_VFO_ITEMS);
    return CLEARUI_QUICK_VFO_ITEMS;
}

uint8_t CLEARUI_QuickItemCount(void)
{
    uint8_t count;
    CLEARUI_QuickItems(&count);
    return count;
}

uint8_t CLEARUI_QuickItemId(uint8_t selection)
{
    if (gClearUIQuickDirectItem < CLEARUI_QUICK_COUNT)
        return gClearUIQuickDirectItem;
    uint8_t count;
    const uint8_t *items = CLEARUI_QuickItems(&count);

    return items[selection < count ? selection : 0];
}

uint8_t CLEARUI_QuickBandId(uint8_t selection)
{
    if (!gSetting_350EN && selection >= BAND5_350MHz)
        selection++;

    return selection;
}

static const uint8_t CLEARUI_RADIO_ITEMS[] =
{
    MENU_STEP, MENU_TXP, MENU_SQL, MENU_AM, MENU_W_N, MENU_TDR,
    MENU_R_CTCS, MENU_R_DCS, MENU_T_CTCS, MENU_T_DCS,
    MENU_SFT_D, MENU_OFFSET, MENU_BCL,
#ifdef ENABLE_FEAT_F4HWN
    MENU_TX_LOCK,
#endif
};

static const uint8_t CLEARUI_MEMORY_ITEMS[] =
{
    MENU_MEM_CH, MENU_DEL_CH, MENU_MEM_NAME, MENU_MDF,
    MENU_LIST_CH, MENU_1_CALL
};

static const uint8_t CLEARUI_SCAN_ITEMS[] =
{
    CLEARUI_LIST_NAMES, MENU_S_LIST, MENU_S_PRI,
    MENU_S_PRI_CH_1, MENU_S_PRI_CH_2,
    MENU_SC_REV
};

static const uint8_t CLEARUI_DISPLAY_ITEMS[] =
{
    MENU_MDF, MENU_SET_MET, MENU_PONMSG, MENU_ABR, MENU_ABR_MIN, MENU_ABR_MAX,
    MENU_ABR_ON_TX_RX, MENU_BAT_TXT,
#ifdef ENABLE_FEAT_F4HWN
    MENU_SET_CTR, MENU_SET_INV, MENU_SET_TMR,
#endif
};

static const uint8_t CLEARUI_SOUND_ITEMS[] =
{
    MENU_MIC, MENU_COMPAND,
#ifdef ENABLE_FEAT_F4HWN_AUDIO
    MENU_SET_AUD,
#endif
#ifdef ENABLE_AM_FIX
    MENU_AM_FIX,
#endif
#ifdef ENABLE_AUDIO_BAR
    MENU_MIC_BAR,
#endif
    MENU_BEEP, MENU_ROGER, MENU_STE,
    MENU_RP_STE,
#ifdef ENABLE_VOX
    MENU_VOX,
#endif
    MENU_PTT_ID, MENU_D_ST, MENU_D_PRE,
    MENU_D_LIVE_DEC
};

static const uint8_t CLEARUI_SYSTEM_ITEMS[] =
{
    MENU_AUTOLK, MENU_TOT, MENU_SAVE,
    MENU_F1SHRT, MENU_F1LONG, MENU_F2SHRT, MENU_F2LONG, MENU_MLONG,
    MENU_VOL,
#ifdef ENABLE_FEAT_F4HWN
    MENU_SET_PWR, MENU_SET_PTT, MENU_SET_TOT, MENU_SET_EOT, MENU_SET_LCK,
    #ifdef ENABLE_FEAT_F4HWN_NARROWER
        MENU_SET_NFM,
    #endif
    #ifdef ENABLE_FEAT_F4HWN_SLEEP
        MENU_SET_OFF,
    #endif
#endif
    MENU_BATTYP, MENU_RESET, CLEARUI_ALL_SETTINGS
};

static const uint8_t *CLEARUI_CategoryItems(uint8_t category, uint8_t *count)
{
    switch (category)
    {
        case CLEARUI_MENU_RADIO:
            *count = ARRAY_SIZE(CLEARUI_RADIO_ITEMS);
            return CLEARUI_RADIO_ITEMS;
        case CLEARUI_MENU_MEMORY:
            *count = ARRAY_SIZE(CLEARUI_MEMORY_ITEMS);
            return CLEARUI_MEMORY_ITEMS;
        case CLEARUI_MENU_SCAN:
            *count = ARRAY_SIZE(CLEARUI_SCAN_ITEMS);
            return CLEARUI_SCAN_ITEMS;
        case CLEARUI_MENU_DISPLAY:
            *count = ARRAY_SIZE(CLEARUI_DISPLAY_ITEMS);
            return CLEARUI_DISPLAY_ITEMS;
        case CLEARUI_MENU_SOUND:
            *count = ARRAY_SIZE(CLEARUI_SOUND_ITEMS);
            return CLEARUI_SOUND_ITEMS;
        default:
            *count = ARRAY_SIZE(CLEARUI_SYSTEM_ITEMS);
            return CLEARUI_SYSTEM_ITEMS;
    }
}

static bool CLEARUI_MenuItemVisible(uint8_t id)
{
    if (id == CLEARUI_ALL_SETTINGS || id == CLEARUI_LIST_NAMES)
        return true;

    const uint8_t index = UI_MENU_GetMenuIdx(id);
    return index < gMenuListCount && MenuList[index].menu_id == id;
}

uint8_t CLEARUI_MenuItemCount(uint8_t category)
{
    uint8_t rawCount;
    uint8_t visibleCount = 0;
    const uint8_t *items = CLEARUI_CategoryItems(category, &rawCount);

    for (uint8_t i = 0; i < rawCount; i++)
        if (CLEARUI_MenuItemVisible(items[i]))
            visibleCount++;

    return visibleCount;
}

uint8_t CLEARUI_MenuItemId(uint8_t category, uint8_t selection)
{
    uint8_t rawCount;
    const uint8_t *items = CLEARUI_CategoryItems(category, &rawCount);

    for (uint8_t i = 0; i < rawCount; i++)
    {
        if (!CLEARUI_MenuItemVisible(items[i]))
            continue;
        if (selection-- == 0)
            return items[i];
    }

    return CLEARUI_ALL_SETTINGS;
}

static uint8_t CLEARUI_ScanItemCount(void)
{
    return gClearUIScanMemoryMode
         ? MR_CHANNELS_LIST + !gClearUIEditingListNames : 1;
}

void CLEARUI_OpenMainMenu(void)
{
#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    gMenuCategory = CAT_ALL;
    UI_MENU_BuildView();
    gMenuLevel = MENU_LEVEL_ITEMS;
#endif
    if (gScanStateDir != SCAN_OFF)
        CHFRSCANNER_Stop();

    gClearUIMenuLevel      = 0;
    gClearUIEditingListNames = false;
    gClearUIListNameEditor = false;
    gClearUIEditorActive  = false;
    gClearUIPendingEditor = false;
    gMenuCountdown     = menu_timeout_500ms;
    gRequestDisplayScreen = DISPLAY_CLEAR_MENU;
}

void CLEARUI_OpenQuickMenu(void)
{
    gClearUIQuickDirectItem = CLEARUI_QUICK_COUNT;
    if (gScanStateDir != SCAN_OFF)
    {
        gClearUIQuickContext = CLEARUI_QUICK_CONTEXT_SCAN;
        gClearUIQuickScanMemory = IS_MR_CHANNEL(gNextMrChannel);
    }
    else
    {
        gClearUIQuickContext = IS_MR_CHANNEL(gTxVfo->CHANNEL_SAVE)
                          ? CLEARUI_QUICK_CONTEXT_MEMORY
                          : CLEARUI_QUICK_CONTEXT_VFO;
        gClearUIQuickScanMemory = false;
    }

    gClearUIEditorActive = false;
    gClearUIQuickLevel   = 0;
    gClearUIQuickSelection = gClearUIQuickLastSelection[gClearUIQuickContext];
    if (gClearUIQuickSelection >= CLEARUI_QuickItemCount())
        gClearUIQuickSelection = 0;
    gRequestDisplayScreen = DISPLAY_QUICK;
}

void CLEARUI_OpenScanMenu(void)
{
    gClearUIEditingListNames = false;
    gClearUIListNameEditor = false;
    if (gScanStateDir != SCAN_OFF)
        CHFRSCANNER_Stop();

    gClearUIEditorActive = false;
    gClearUIListPickOnly = false;
    gClearUIScanMemoryMode = IS_MR_CHANNEL(gTxVfo->CHANNEL_SAVE);
    gClearUIScanSelection  = gClearUIScanMemoryMode
                           ? CLEARUI_GetGroup(gEeprom.TX_VFO) - 1 : 0;
    gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
}

void CLEARUI_ToggleDual(void)
{
    static uint8_t previousDual = DUAL_WATCH_CHAN_A;
    static uint8_t previousCross = CROSS_BAND_OFF;

    if (gEeprom.DUAL_WATCH != DUAL_WATCH_OFF ||
        gEeprom.CROSS_BAND_RX_TX != CROSS_BAND_OFF)
    {
        previousDual  = gEeprom.DUAL_WATCH;
        previousCross = gEeprom.CROSS_BAND_RX_TX;
        gEeprom.DUAL_WATCH       = DUAL_WATCH_OFF;
        gEeprom.CROSS_BAND_RX_TX = CROSS_BAND_OFF;
    }
    else
    {
        gEeprom.DUAL_WATCH = previousDual == DUAL_WATCH_OFF
                           ? gEeprom.TX_VFO + 1 : previousDual;
        gEeprom.CROSS_BAND_RX_TX = previousCross;
    }

    ACTION_Update();
    gRequestDisplayScreen = DISPLAY_MAIN;
}

static void CLEARUI_OpenMenuItem(void)
{
    const uint8_t id = CLEARUI_MenuItemId(gClearUIMenuCategory, gClearUIMenuSelection);

    gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
    gClearUIEditorActive = true;
    gClearUIEditorReturnDisplay = DISPLAY_CLEAR_MENU;

    if (id == CLEARUI_LIST_NAMES)
    {
        CLEARUI_LoadListNames();
        gClearUIEditingListNames = true;
        gClearUIListNameEditor = false;
        gClearUIListPickOnly = true;
        gClearUIScanMemoryMode = true;
        gClearUIScanSelection = 0;
        gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
        return;
    }

#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    gMenuCategory = CAT_ALL;
    UI_MENU_BuildView();
    gMenuLevel = MENU_LEVEL_ITEMS;
#endif

    if (id == CLEARUI_ALL_SETTINGS)
    {
        gClearUIEditorReturnDisplay = DISPLAY_MENU;
        gMenuCursor = 0;
        gFlagRefreshSetting = true;
        gRequestDisplayScreen = DISPLAY_MENU;
        return;
    }

    gMenuCursor = UI_MENU_GetViewPos(id);
    edit_index = -1;
    MENU_ShowCurrentSetting();
    gClearUIPendingEditor = true;
    gRequestDisplayScreen = DISPLAY_MENU;
}

uint8_t CLEARUI_QuickSubCount(void)
{
    switch (CLEARUI_QuickItemId(gClearUIQuickSelection))
    {
        case CLEARUI_QUICK_POWER:        return OUTPUT_POWER_HIGH + 1;
        case CLEARUI_QUICK_VOX:          return 11;
        case CLEARUI_QUICK_REVERSE:      return 2;
        case CLEARUI_QUICK_VFO_MEMORY:   return 2;
        case CLEARUI_QUICK_MODE:         return MODULATION_UKNOWN;
        case CLEARUI_QUICK_BANDWIDTH:    return 2;
        case CLEARUI_QUICK_LIST:         return MR_CHANNELS_LIST + 1;
        case CLEARUI_QUICK_DUPLEX:       return 3;
        case CLEARUI_QUICK_TSQL:         return 5;
        case CLEARUI_QUICK_STEP:         return STEP_N_ELEM;
        case CLEARUI_QUICK_DISPLAY:      return 4;
        case CLEARUI_QUICK_SQUELCH:      return 10;
        case CLEARUI_QUICK_RX_COMPAND:   return 2;
        case CLEARUI_QUICK_RX_AUDIO:
            return gTxVfo->Modulation == MODULATION_AM ? 3 : 5;
        case CLEARUI_QUICK_BAND:         return BAND_N_ELEM - !gSetting_350EN;
        case CLEARUI_QUICK_TEMP_SKIP:
            return gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_SCAN ? 0 : 2;
        case CLEARUI_QUICK_SCAN_DIRECTION:return 2;
        default:                      return 0;
    }
}

static uint8_t CLEARUI_ToneSelection(void)
{
    switch (gTxVfo->freq_config_RX.CodeType)
    {
        case CODE_TYPE_CONTINUOUS_TONE: return 2;
        case CODE_TYPE_DIGITAL:         return 3;
        case CODE_TYPE_REVERSE_DIGITAL: return 4;
        default:
            return gTxVfo->freq_config_TX.CodeType == CODE_TYPE_CONTINUOUS_TONE
                 ? 1 : 0;
    }
}

static uint8_t CLEARUI_QuickCurrentSelection(void)
{
    switch (CLEARUI_QuickItemId(gClearUIQuickSelection))
    {
        case CLEARUI_QUICK_POWER:
            return gTxVfo->OUTPUT_POWER;
        case CLEARUI_QUICK_VOX:
            return gEeprom.VOX_SWITCH ? gEeprom.VOX_LEVEL + 1 : 0;
        case CLEARUI_QUICK_REVERSE:
            return gTxVfo->FrequencyReverse;
        case CLEARUI_QUICK_VFO_MEMORY:
            return IS_MR_CHANNEL(gEeprom.ScreenChannel[gEeprom.TX_VFO]);
        case CLEARUI_QUICK_MODE:
            return gTxVfo->Modulation;
        case CLEARUI_QUICK_BANDWIDTH:
            return gTxVfo->CHANNEL_BANDWIDTH;
        case CLEARUI_QUICK_LIST:
            return CLEARUI_GetGroup(gEeprom.TX_VFO) - 1;
        case CLEARUI_QUICK_DUPLEX:
            return gTxVfo->TX_OFFSET_FREQUENCY_DIRECTION;
        case CLEARUI_QUICK_TSQL:
            return CLEARUI_ToneSelection();
        case CLEARUI_QUICK_STEP:
            return FREQUENCY_GetSortedIdxFromStepIdx(gTxVfo->STEP_SETTING);
        case CLEARUI_QUICK_DISPLAY:
            return gEeprom.CHANNEL_DISPLAY_MODE;
        case CLEARUI_QUICK_SQUELCH:
            return gEeprom.SQUELCH_LEVEL;
        case CLEARUI_QUICK_RX_COMPAND:
            return (gTxVfo->Compander >> 1) & 1;
        case CLEARUI_QUICK_RX_AUDIO:
#ifdef ENABLE_FEAT_F4HWN_AUDIO
            return gTxVfo->Modulation == MODULATION_AM
                 ? gSetting_set_audio_am : gSetting_set_audio_fm;
#else
            return 0;
#endif
        case CLEARUI_QUICK_BAND:
            return gTxVfo->Band - (!gSetting_350EN && gTxVfo->Band > BAND5_350MHz);
        case CLEARUI_QUICK_TEMP_SKIP:
            if (gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_SCAN)
                return gClearUIQuickScanMemory &&
                       MR_GetChannelAttributes(gNextMrChannel)->exclude;
            return IS_MR_CHANNEL(gTxVfo->CHANNEL_SAVE) &&
                   MR_GetChannelAttributes(gTxVfo->CHANNEL_SAVE)->exclude;
        case CLEARUI_QUICK_SCAN_DIRECTION:
            return gScanStateDir == SCAN_FWD;
        default:
            return 0;
    }
}

bool CLEARUI_OpenKeyMenu(KEY_Code_t key)
{
    uint8_t item;
    switch (key) {
    case KEY_1: item = CLEARUI_QUICK_BAND; break;
    case KEY_3: item = CLEARUI_QUICK_VFO_MEMORY; break;
    case KEY_6: item = CLEARUI_QUICK_POWER; break;
#ifdef ENABLE_VOX
    case KEY_7: item = CLEARUI_QUICK_VOX; break;
#endif
    case KEY_8: item = CLEARUI_QUICK_REVERSE; break;
    case KEY_9:
        // The channel picker uses the existing 1024-entry settings editor.
#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
        gMenuCategory = CAT_ALL;
        UI_MENU_BuildView();
        gMenuLevel = MENU_LEVEL_ITEMS;
#endif
        gMenuCursor = UI_MENU_GetViewPos(MENU_1_CALL);
        edit_index = -1;
        MENU_ShowCurrentSetting();
        gClearUIEditorActive = gClearUIPendingEditor = true;
        gClearUIEditorReturnDisplay = DISPLAY_MAIN;
        gClearUIIgnoreNextRelease = true;
        gRequestDisplayScreen = DISPLAY_MENU;
        return true;
    default: return false;
    }
    if ((item == CLEARUI_QUICK_BAND || item == CLEARUI_QUICK_VFO_MEMORY) &&
        !gEeprom.VFO_OPEN) {
        gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
        return true;
    }
    CLEARUI_OpenQuickMenu();
    gClearUIQuickDirectItem = item;
    gClearUIQuickLevel = 1;
    gClearUIQuickSubSelection = CLEARUI_QuickCurrentSelection();
    if (gClearUIQuickSubSelection >= CLEARUI_QuickSubCount())
        gClearUIQuickSubSelection = 0;
    gClearUIIgnoreNextRelease = true;
    return true;
}

static void CLEARUI_QuickApplyMenuSetting(uint8_t menuId)
{
#ifdef ENABLE_FEAT_F4HWN_MENU_CAT
    gMenuCategory = CAT_ALL;
    UI_MENU_BuildView();
    gMenuLevel = MENU_LEVEL_ITEMS;
#endif
    gMenuCursor       = UI_MENU_GetViewPos(menuId);
    gSubMenuSelection = gClearUIQuickSubSelection;
    MENU_AcceptSetting();
}

static void CLEARUI_QuickApplyTone(void)
{
    FREQ_Config_t *rx = &gTxVfo->freq_config_RX;
    FREQ_Config_t *tx = &gTxVfo->freq_config_TX;
    uint8_t ctcss = 0;
    uint8_t dcs   = 0;

    if (rx->CodeType == CODE_TYPE_CONTINUOUS_TONE)
        ctcss = rx->Code;
    else if (tx->CodeType == CODE_TYPE_CONTINUOUS_TONE)
        ctcss = tx->Code;
    if (rx->CodeType == CODE_TYPE_DIGITAL ||
        rx->CodeType == CODE_TYPE_REVERSE_DIGITAL)
        dcs = rx->Code;
    else if (tx->CodeType == CODE_TYPE_DIGITAL ||
             tx->CodeType == CODE_TYPE_REVERSE_DIGITAL)
        dcs = tx->Code;

    rx->CodeType = CODE_TYPE_OFF;
    tx->CodeType = CODE_TYPE_OFF;
    rx->Code = 0;
    tx->Code = 0;

    switch (gClearUIQuickSubSelection)
    {
        case 1:
            tx->CodeType = CODE_TYPE_CONTINUOUS_TONE;
            tx->Code     = ctcss;
            break;
        case 2:
            rx->CodeType = tx->CodeType = CODE_TYPE_CONTINUOUS_TONE;
            rx->Code = tx->Code = ctcss;
            break;
        case 3:
            rx->CodeType = tx->CodeType = CODE_TYPE_DIGITAL;
            rx->Code = tx->Code = dcs;
            break;
        case 4:
            rx->CodeType = tx->CodeType = CODE_TYPE_REVERSE_DIGITAL;
            rx->Code = tx->Code = dcs;
            break;
        default:
            break;
    }

    gRequestSaveChannel = 1;
    gVfoConfigureMode   = VFO_CONFIGURE;
}

static bool CLEARUI_TemporarySkipCurrent(void)
{
    if (gScanStateDir == SCAN_OFF || !IS_MR_CHANNEL(gNextMrChannel))
        return false;

    uint16_t channel = IS_MR_CHANNEL(lastFoundFrqOrChan)
                     ? (uint16_t)lastFoundFrqOrChan : gNextMrChannel;
    ChannelAttributes_t *attributes = MR_GetChannelAttributes(channel);

    attributes->exclude = true;
    MR_SaveChannelAttributesToFlash(channel, attributes);
    UI_MAIN_NotifyScanProgressDataChanged();
    gVfoConfigureMode = VFO_CONFIGURE;
    gFlagResetVfos = true;
    lastFoundFrqOrChan = lastFoundFrqOrChanOld;
    CHFRSCANNER_ContinueScanning();
    return true;
}

static void CLEARUI_QuickApply(void)
{
    const uint8_t item = CLEARUI_QuickItemId(gClearUIQuickSelection);

    switch (item)
    {
        case CLEARUI_QUICK_POWER:
            CLEARUI_QuickApplyMenuSetting(MENU_TXP);
            break;
        case CLEARUI_QUICK_VOX:
#ifdef ENABLE_VOX
            CLEARUI_QuickApplyMenuSetting(MENU_VOX);
#endif
            break;
        case CLEARUI_QUICK_REVERSE:
            gTxVfo->FrequencyReverse = gClearUIQuickSubSelection;
            gRequestSaveChannel = 1;
            gVfoConfigureMode = VFO_CONFIGURE;
            gFlagResetVfos = true;
            break;
        case CLEARUI_QUICK_VFO_MEMORY:
            if (gClearUIQuickSubSelection !=
                IS_MR_CHANNEL(gEeprom.ScreenChannel[gEeprom.TX_VFO]))
                COMMON_SwitchVFOMode();
            break;
        case CLEARUI_QUICK_MODE:
            CLEARUI_QuickApplyMenuSetting(MENU_AM);
            break;
        case CLEARUI_QUICK_BANDWIDTH:
            CLEARUI_QuickApplyMenuSetting(MENU_W_N);
            break;
        case CLEARUI_QUICK_LIST:
            if (!CLEARUI_SelectGroup(gClearUIQuickSubSelection + 1))
                return;
            gRequestSaveSettings = true;
#ifdef ENABLE_FEAT_F4HWN_RESUME_STATE
            SETTINGS_WriteCurrentState();
#endif
            if (gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_SCAN &&
                gScanStateDir != SCAN_OFF)
            {
                CHFRSCANNER_Start(false, gScanStateDir);
                if (gScanStateDir == SCAN_OFF)
                    return;
            }
            break;
        case CLEARUI_QUICK_DUPLEX:
            CLEARUI_QuickApplyMenuSetting(MENU_SFT_D);
            break;
        case CLEARUI_QUICK_TSQL:
            CLEARUI_QuickApplyTone();
            break;
        case CLEARUI_QUICK_STEP:
            CLEARUI_QuickApplyMenuSetting(MENU_STEP);
            break;
        case CLEARUI_QUICK_DISPLAY:
            CLEARUI_QuickApplyMenuSetting(MENU_MDF);
            break;
        case CLEARUI_QUICK_SQUELCH:
            CLEARUI_QuickApplyMenuSetting(MENU_SQL);
            break;
        case CLEARUI_QUICK_RX_COMPAND:
            gTxVfo->Compander = (gTxVfo->Compander & 1) |
                                (gClearUIQuickSubSelection << 1);
            SETTINGS_UpdateChannel(gTxVfo->CHANNEL_SAVE, gTxVfo, true);
            gVfoConfigureMode = VFO_CONFIGURE;
            gFlagResetVfos = true;
            break;
        case CLEARUI_QUICK_RX_AUDIO:
#ifdef ENABLE_FEAT_F4HWN_AUDIO
            CLEARUI_QuickApplyMenuSetting(MENU_SET_AUD);
#endif
            break;
        case CLEARUI_QUICK_BAND:
        {
            const uint8_t band = CLEARUI_QuickBandId(gClearUIQuickSubSelection);
            if (!gEeprom.VFO_OPEN) return;
            if (band != gTxVfo->Band || IS_MR_CHANNEL(gTxVfo->CHANNEL_SAVE))
            {
                const uint8_t vfo = gEeprom.TX_VFO;
                gTxVfo->Band               = band;
                gEeprom.ScreenChannel[vfo] = FREQ_CHANNEL_FIRST + band;
                gEeprom.FreqChannel[vfo]   = FREQ_CHANNEL_FIRST + band;
                gRequestSaveVFO            = true;
                gVfoConfigureMode          = VFO_CONFIGURE_RELOAD;
            }
            break;
        }
        case CLEARUI_QUICK_TEMP_SKIP:
            if (gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_SCAN)
            {
                if (!gClearUIQuickScanMemory ||
                    !CLEARUI_TemporarySkipCurrent())
                    gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
            }
            else if (IS_MR_CHANNEL(gTxVfo->CHANNEL_SAVE))
            {
                ChannelAttributes_t *attributes =
                    MR_GetChannelAttributes(gTxVfo->CHANNEL_SAVE);
                attributes->exclude = gClearUIQuickSubSelection;
                MR_SaveChannelAttributesToFlash(gTxVfo->CHANNEL_SAVE,
                                                attributes);
                UI_MAIN_NotifyScanProgressDataChanged();
            }
            break;
        case CLEARUI_QUICK_SCAN_DIRECTION:
            if (gScanStateDir != SCAN_OFF)
                CHFRSCANNER_Start(false, gClearUIQuickSubSelection
                                       ? SCAN_FWD : SCAN_REV);
            break;
        case CLEARUI_QUICK_SCAN_STOP:
            if (gScanStateDir != SCAN_OFF)
                CHFRSCANNER_Stop();
            break;
        default:
            break;
    }

    gClearUIQuickLevel = 0;
    gRequestDisplayScreen = gClearUIQuickDirectItem < CLEARUI_QUICK_COUNT ||
                            item == CLEARUI_QUICK_SCAN_STOP ||
                            item == CLEARUI_QUICK_LIST ||
                            item == CLEARUI_QUICK_VFO_MEMORY ||
                            (gClearUIQuickContext == CLEARUI_QUICK_CONTEXT_SCAN &&
                             item == CLEARUI_QUICK_TEMP_SKIP)
                          ? DISPLAY_MAIN : DISPLAY_QUICK;
    gClearUIQuickDirectItem = CLEARUI_QUICK_COUNT;
}

static void CLEARUI_QuickExecute(void)
{
    gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;

    if (gClearUIQuickLevel)
    {
        CLEARUI_QuickApply();
        return;
    }

    if (CLEARUI_QuickSubCount() != 0)
    {
        gClearUIQuickSubSelection = CLEARUI_QuickCurrentSelection();
        gClearUIQuickLevel = 1;
        gRequestDisplayScreen = DISPLAY_QUICK;
        return;
    }

    switch (CLEARUI_QuickItemId(gClearUIQuickSelection))
    {
        case CLEARUI_QUICK_ENTER:
            gClearUINumericEntry = true;
            gRequestDisplayScreen = DISPLAY_MAIN;
            return;
        case CLEARUI_QUICK_WATERFALL:
#ifdef ENABLE_SPECTRUM
            APP_RunSpectrum();
#else
            gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
#endif
            break;

        case CLEARUI_QUICK_SCAN_STOP:
            CLEARUI_QuickApply();
            return;

        case CLEARUI_QUICK_TEMP_SKIP:
            gClearUIQuickSubSelection = 1;
            CLEARUI_QuickApply();
            return;

        default:
            break;
    }

    gRequestDisplayScreen = DISPLAY_MAIN;
}

static void CLEARUI_ScanExecute(void)
{
    gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;

    if (gClearUIEditingListNames)
    {
        if (!gClearUIListNameEditor)
        {
            const char *name = CLEARUI_GetListName(gClearUIScanSelection);
            memset(gClearUIListEditName, ' ', CLEARUI_LIST_NAME_LENGTH);
            memcpy(gClearUIListEditName, name, strlen(name));
            gClearUIListEditName[CLEARUI_LIST_NAME_LENGTH] = '\0';
            gClearUIListNameCursor = 0;
            gClearUIListNameEditor = true;
            gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
            return;
        }

        CLEARUI_SaveListName(gClearUIScanSelection, gClearUIListEditName);
        gClearUIListNameEditor = false;
        gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
        return;
    }

    if (gClearUIScanMemoryMode && !CLEARUI_SelectGroup(gClearUIScanSelection + 1))
        return;

    if (gClearUIListPickOnly)
    {
#ifdef ENABLE_FEAT_F4HWN_RESUME_STATE
        SETTINGS_WriteCurrentState();
#endif
        gRequestDisplayScreen = DISPLAY_MAIN;
        return;
    }

    ACTION_Scan(false);
}

static void CLEARUI_MoveSelection(uint8_t *selection, uint8_t count, int8_t direction,
                               GUI_DisplayType_t display)
{
    if (direction > 0)
        *selection = (*selection + 1) % count;
    else
        *selection = (*selection == 0) ? count - 1 : *selection - 1;

    gRequestDisplayScreen = display;
}

void CLEARUI_MENU_ProcessKeys(KEY_Code_t Key, bool bKeyPressed, bool bKeyHeld)
{
    if (!bKeyPressed && gClearUIIgnoreNextRelease)
    {
        gClearUIIgnoreNextRelease = false;
        return;
    }

    if (Key == KEY_PTT)
    {
        GENERIC_Key_PTT(bKeyPressed);
        return;
    }

    if (Key == KEY_UP || Key == KEY_DOWN)
    {
        if (bKeyPressed)
        {
            uint8_t *selection = gClearUIMenuLevel ? &gClearUIMenuSelection : &gClearUIMenuCategory;
            const uint8_t count = gClearUIMenuLevel
                                ? CLEARUI_MenuItemCount(gClearUIMenuCategory)
                                : CLEARUI_MENU_CATEGORY_COUNT;
            if (!bKeyHeld)
                gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            CLEARUI_MoveSelection(selection, count, Key == KEY_UP ? -1 : 1,
                               DISPLAY_CLEAR_MENU);
            gMenuCountdown = menu_timeout_500ms;
        }
        return;
    }

    if (bKeyHeld || bKeyPressed)
        return;

    gMenuCountdown = menu_timeout_500ms;

    if (!gClearUIMenuLevel && Key >= KEY_1 && Key <= KEY_6)
    {
        gClearUIMenuCategory  = Key - KEY_1;
        gClearUIMenuSelection = 0;
        gClearUIMenuLevel     = 1;
        gBeepToPlay        = BEEP_1KHZ_60MS_OPTIONAL;
        gRequestDisplayScreen = DISPLAY_CLEAR_MENU;
        return;
    }

    switch (Key)
    {
        case KEY_MENU:
            if (gClearUIMenuLevel)
                CLEARUI_OpenMenuItem();
            else
            {
                gClearUIMenuSelection = 0;
                gClearUIMenuLevel     = 1;
                gBeepToPlay        = BEEP_1KHZ_60MS_OPTIONAL;
                gRequestDisplayScreen = DISPLAY_CLEAR_MENU;
            }
            break;

        case KEY_EXIT:
        case KEY_STAR:
            gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            if (gClearUIMenuLevel)
            {
                gClearUIMenuLevel = 0;
                gRequestDisplayScreen = DISPLAY_CLEAR_MENU;
            }
            else
            {
                gMenuCountdown = 0;
                gRequestDisplayScreen = DISPLAY_MAIN;
            }
            break;

        default:
            gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
            break;
    }
}

void CLEARUI_QUICK_ProcessKeys(KEY_Code_t Key, bool bKeyPressed, bool bKeyHeld)
{
    if (!bKeyPressed && gClearUIIgnoreNextRelease)
    {
        gClearUIIgnoreNextRelease = false;
        return;
    }

    if (Key == KEY_PTT)
    {
        GENERIC_Key_PTT(bKeyPressed);
        return;
    }

    if (Key == KEY_UP || Key == KEY_DOWN)
    {
        if (bKeyPressed)
        {
            if (!bKeyHeld)
                gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            uint8_t *selection = gClearUIQuickLevel
                               ? &gClearUIQuickSubSelection
                               : &gClearUIQuickSelection;
            const uint8_t count = gClearUIQuickLevel
                                ? CLEARUI_QuickSubCount()
                                : CLEARUI_QuickItemCount();
            CLEARUI_MoveSelection(selection, count,
                               Key == KEY_UP ? -1 : 1, DISPLAY_QUICK);
            if (!gClearUIQuickLevel)
                gClearUIQuickLastSelection[gClearUIQuickContext] = gClearUIQuickSelection;
        }
        return;
    }

    if (bKeyHeld || bKeyPressed)
        return;

    if (!gClearUIQuickLevel && Key >= KEY_1 && Key <= KEY_6 &&
        Key - KEY_1 < CLEARUI_QuickItemCount())
    {
        gClearUIQuickSelection = Key - KEY_1;
        gClearUIQuickLastSelection[gClearUIQuickContext] = gClearUIQuickSelection;
        CLEARUI_QuickExecute();
        return;
    }

    switch (Key)
    {
        case KEY_MENU:
            gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            CLEARUI_QuickExecute();
            break;

        case KEY_EXIT:
        case KEY_STAR:
            gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            if (gClearUIQuickDirectItem < CLEARUI_QUICK_COUNT) {
                gClearUIQuickDirectItem = CLEARUI_QUICK_COUNT;
                gClearUIQuickLevel = 0;
                gRequestDisplayScreen = DISPLAY_MAIN;
                break;
            }
            if (gClearUIQuickLevel)
            {
                gClearUIQuickLevel = 0;
                gRequestDisplayScreen = DISPLAY_QUICK;
            }
            else
                gRequestDisplayScreen = DISPLAY_MAIN;
            break;

        default:
            gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
            break;
    }
}

void CLEARUI_SCAN_ProcessKeys(KEY_Code_t Key, bool bKeyPressed, bool bKeyHeld)
{
    const uint8_t count = CLEARUI_ScanItemCount();

    if (!bKeyPressed && gClearUIIgnoreNextRelease)
    {
        gClearUIIgnoreNextRelease = false;
        return;
    }

    if (Key == KEY_PTT)
    {
        GENERIC_Key_PTT(bKeyPressed);
        return;
    }

    if (gClearUIListNameEditor && (Key == KEY_UP || Key == KEY_DOWN))
    {
        static const char characters[] =
            " ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-/.";

        if (bKeyPressed)
        {
            const char current = gClearUIListEditName[gClearUIListNameCursor];
            uint8_t position = 0;
            while (characters[position] != '\0' &&
                   characters[position] != current)
                position++;
            if (characters[position] == '\0')
                position = 0;

            if (Key == KEY_UP)
                position = characters[position + 1] == '\0' ? 0 : position + 1;
            else
                position = position == 0 ? sizeof(characters) - 2 : position - 1;

            gClearUIListEditName[gClearUIListNameCursor] =
                characters[position];
            gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
        }
        return;
    }

    if (Key == KEY_UP || Key == KEY_DOWN)
    {
        if (bKeyPressed)
        {
            if (!bKeyHeld)
                gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            CLEARUI_MoveSelection(&gClearUIScanSelection, count,
                               Key == KEY_UP ? -1 : 1, DISPLAY_SCAN_GROUP);
        }
        return;
    }

    if (bKeyHeld || bKeyPressed)
        return;

    switch (Key)
    {
        case KEY_MENU:
            if (gClearUIListNameEditor)
            {
                gClearUIListNameCursor = (gClearUIListNameCursor + 1) %
                                        CLEARUI_LIST_NAME_LENGTH;
                gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
                break;
            }
            gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            CLEARUI_ScanExecute();
            break;

        case KEY_STAR:
            gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            CLEARUI_ScanExecute();
            break;

        case KEY_EXIT:
            gBeepToPlay = BEEP_1KHZ_60MS_OPTIONAL;
            if (gClearUIListNameEditor)
            {
                gClearUIListNameEditor = false;
                gRequestDisplayScreen = DISPLAY_SCAN_GROUP;
            }
            else if (gClearUIEditingListNames)
            {
                gClearUIEditingListNames = false;
                gClearUIListPickOnly = false;
                gRequestDisplayScreen = DISPLAY_CLEAR_MENU;
            }
            else
                gRequestDisplayScreen = DISPLAY_MAIN;
            break;

        default:
            gBeepToPlay = BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL;
            break;
    }
}
