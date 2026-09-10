/*
 * SPDX-License-Identifier: Apache-2.0
 * Added for ClearUI in 2026.
 *
 * ClearUI interaction layer for the Fusion v5.9 firmware.
 *
 * This module only owns the new Quick and Scan Group screens.  Radio,
 * EEPROM, and calibration behavior remain in the existing F4HWN modules.
 */

#ifndef APP_CLEARUI_H
#define APP_CLEARUI_H

#include <stdbool.h>
#include <stdint.h>

#include "driver/keyboard.h"

#define CLEARUI_LIST_NAME_LENGTH 16
#define CLEARUI_LIST_NAMES 0xFE
#define CLEARUI_HF_LISTEN 0xFD

enum
{
    CLEARUI_QUICK_POWER = 0,
    CLEARUI_QUICK_VFO_MEMORY,
    CLEARUI_QUICK_MODE,
    CLEARUI_QUICK_BANDWIDTH,
    CLEARUI_QUICK_LIST,
    CLEARUI_QUICK_DUPLEX,
    CLEARUI_QUICK_TSQL,
    CLEARUI_QUICK_STEP,
    CLEARUI_QUICK_DISPLAY,
    CLEARUI_QUICK_SQUELCH,
    CLEARUI_QUICK_RX_COMPAND,
    CLEARUI_QUICK_RX_AUDIO,
    CLEARUI_QUICK_WATERFALL,
    CLEARUI_QUICK_BAND,
    CLEARUI_QUICK_TEMP_SKIP,
    CLEARUI_QUICK_SCAN_DIRECTION,
    CLEARUI_QUICK_SCAN_STOP,
    CLEARUI_QUICK_ENTER,
    CLEARUI_QUICK_VOX,
    CLEARUI_QUICK_REVERSE,
    CLEARUI_QUICK_HF_LISTEN,
    CLEARUI_QUICK_COUNT
};

enum
{
    CLEARUI_QUICK_CONTEXT_MEMORY = 0,
    CLEARUI_QUICK_CONTEXT_VFO,
    CLEARUI_QUICK_CONTEXT_SCAN,
    CLEARUI_QUICK_CONTEXT_COUNT
};

enum
{
    CLEARUI_MENU_RADIO = 0,
    CLEARUI_MENU_MEMORY,
    CLEARUI_MENU_SCAN,
    CLEARUI_MENU_DISPLAY,
    CLEARUI_MENU_SOUND,
    CLEARUI_MENU_SYSTEM,
    CLEARUI_MENU_CATEGORY_COUNT
};

extern uint8_t gClearUIQuickSelection;
extern uint8_t gClearUIQuickSubSelection;
extern uint8_t gClearUIQuickLevel;
extern uint8_t gClearUIQuickContext;
extern bool    gClearUIQuickScanMemory;
extern bool    gClearUINumericEntry;
extern uint8_t gClearUIScanSelection;
extern bool    gClearUIScanMemoryMode;
extern bool    gClearUIListPickOnly;
extern uint8_t gClearUIMenuCategory;
extern uint8_t gClearUIMenuSelection;
extern uint8_t gClearUIMenuLevel;
extern bool    gClearUIEditorActive;
extern bool    gClearUIPendingEditor;
extern bool    gClearUIIgnoreNextRelease;
extern uint8_t gClearUIEditorReturnDisplay;
extern bool    gClearUIEditingListNames;
extern bool    gClearUIListNameEditor;
extern uint8_t gClearUIListNameCursor;
extern char    gClearUIListEditName[CLEARUI_LIST_NAME_LENGTH + 1];

void CLEARUI_OpenMainMenu(void);
void CLEARUI_OpenQuickMenu(void);
bool CLEARUI_OpenKeyMenu(KEY_Code_t key);
void CLEARUI_OpenScanMenu(void);
void CLEARUI_ToggleDual(void);
const char *CLEARUI_GetListName(uint8_t listIndex);
void CLEARUI_LoadListNames(void);
void CLEARUI_SaveListName(uint8_t listIndex, const char *name);
uint8_t CLEARUI_GetGroup(uint8_t vfo);
void CLEARUI_SyncGroup(void);
bool CLEARUI_ChannelInGroup(uint16_t channel, uint8_t group);
uint16_t CLEARUI_FindGroupChannel(uint16_t start, int8_t direction, uint8_t group);
bool CLEARUI_SelectGroup(uint8_t group);

uint8_t CLEARUI_MenuItemCount(uint8_t category);
uint8_t CLEARUI_MenuItemId(uint8_t category, uint8_t selection);
uint8_t CLEARUI_QuickSubCount(void);
uint8_t CLEARUI_QuickItemCount(void);
uint8_t CLEARUI_QuickItemId(uint8_t selection);
uint8_t CLEARUI_QuickBandId(uint8_t selection);

void CLEARUI_MENU_ProcessKeys(KEY_Code_t Key, bool bKeyPressed, bool bKeyHeld);
void CLEARUI_QUICK_ProcessKeys(KEY_Code_t Key, bool bKeyPressed, bool bKeyHeld);
void CLEARUI_SCAN_ProcessKeys(KEY_Code_t Key, bool bKeyPressed, bool bKeyHeld);

#endif
