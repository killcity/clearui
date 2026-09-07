#!/usr/bin/env python3
"""Exercise extracted production C menu logic with ASan/UBSan hardware stubs."""
from pathlib import Path
import re
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


def function(path, name):
    source = read(path)
    match = re.search(r"^[^\n;]*\b" + name + r"\([^;]*?\)\s*\{", source, re.M)
    if not match:
        raise ValueError(name)
    end, depth = match.end(), 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end] + "\n"


def declaration(path, name):
    source = read(path)
    match = re.search(r"^[^\n]*\b" + name + r"\[.*?=\s*\{.*?\};", source, re.M | re.S)
    return match.group() + "\n"


def main():
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsyntax-only",
                    "-I" + str(ROOT / "App"), str(ROOT / "App/ui/clearui_text.c")], check=True)
    ui = read("App/ui/menu.c")
    header = read("App/ui/menu.h")
    defines = sorted(set(re.findall(r"-D(ENABLE_\w+)", read("build/ClearUI/build.ninja"))))
    enums = re.findall(r"\benum\s*\{.*?\};", header, re.S)
    source = "\n".join("#define " + name for name in defines) + r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MR_CHANNELS_LIST 24
#define MR_CHANNEL_LAST 1023
#define MR_CHANNELS_MAX 1024
#define MODULATION_FM 0
#define MODULATION_AM 1
#define MODULATION_USB 2
#define MODULATION_UKNOWN 3
#define MENU_LEVEL_CAT 0
#define MENU_LEVEL_ITEMS 1
#define SET_LCK_LEN 4
#define SET_SAV_LEN 4
typedef struct {const char name[7]; uint8_t menu_id;} t_menu_item;
typedef struct {const char *name; uint8_t id;} t_sidefunction;
static struct {unsigned Modulation; unsigned CHANNEL_SAVE; unsigned StepFrequency;} vfo;
static __typeof__(vfo) *gTxVfo = &vfo;
static bool gF_LOCK = true;
static uint8_t gMenuCursor, gMenuListCount, gMenuIndices[256];
static int32_t gSubMenuSelection;
static bool gIsInSubMenu, gAskForConfirmation;
static int edit_index;
static int gSetting_set_ctr, gSetting_set_inv;
static uint8_t gFrameBuffer[7][128], gStatusLine[128];
static const char gModulationStr[][4] = {"FM", "AM", "USB"};
static const uint8_t gMicGain_dB2[] = {3,8,16,24,32,40,48,56,63};
static bool RADIO_CheckValidChannel(int value, bool scan, unsigned list) {
    (void)scan; (void)list; return value >= 0 && value <= 1023;
}
static void SETTINGS_FetchChannelName(char *text, int value, size_t capacity) {
    assert(value >= 0 && value <= 1023); snprintf(text, capacity, "ABCDEFGHIJKLMNOP");
}
static void UI_GenerateChannelStringEx(char *text, bool valid, int value) {
    (void)valid; sprintf(text, "CH-%04d", value + 1);
}
static bool unnamed_group;
static bool gallery_groups;
static const char *CLEARUI_GetListName(int list) {
    assert(list >= 0 && list < 24);
    if (gallery_groups) {
        static const char *names[]={"Local repeaters","Simplex","Weather","Marine","Favorites"};
        return list < 5 ? names[list] : "";
    }
    return unnamed_group ? "" : "ABCDEFGHIJKLMNOP";
}
static void BACKLIGHT_SetBrightness(int level) {assert(level >= 0 && level <= 10);}
static void ST7565_ContrastAndInv(void) {}
static void ST7565_BlitStatusLine(void) {}
static void ST7565_BlitFullScreen(void) {}
static void PutPixel(uint8_t x, uint8_t y, bool fill) {
    assert(x < 128 && y < 56); if(fill) gFrameBuffer[y/8][x] |= 1u << (y%8);
}
static void PutPixelStatus(uint8_t x, uint8_t y, bool fill) {
    assert(x < 128 && y < 8); if(fill) gStatusLine[x] |= 1u << y;
}
static void UI_DrawLineBuffer(uint8_t buffer[7][128], uint8_t x1, uint8_t y1,
                              uint8_t x2, uint8_t y2, bool fill) {
    (void)buffer; assert(x1==x2 || y1==y2);
    for(unsigned y=y1;y<=y2;y++) for(unsigned x=x1;x<=x2;x++) PutPixel(x,y,fill);
}
static void UI_DrawPixelBuffer(uint8_t buffer[7][128], uint8_t x, uint8_t y, bool fill) {
    (void)buffer; PutPixel(x,y,fill);
}
static void UI_DrawRectangleBuffer(uint8_t buffer[7][128], int x1, int y1, int x2, int y2, bool fill) {
    UI_DrawLineBuffer(buffer,x1,y1,x2,y1,fill); UI_DrawLineBuffer(buffer,x1,y2,x2,y2,fill);
    UI_DrawLineBuffer(buffer,x1,y1,x1,y2,fill); UI_DrawLineBuffer(buffer,x2,y1,x2,y2,fill);
}
'''
    source += "\n".join(enums)
    source += "enum {" + ",".join(sorted(set(re.findall(r"\bACTION_OPT_\w+", ui)))) + "};\n"
    frequency_header = read("App/frequencies.h")
    source += re.search(r"typedef enum\s*\{[^}]*STEP_2_5kHz.*?STEP_Setting_t;", frequency_header, re.S).group()
    source += declaration("App/frequencies.c", "gStepFrequencyTable")
    source += declaration("App/frequencies.c", "StepSortedIndexes")
    source += function("App/frequencies.c", "FREQUENCY_GetStepIdxFromSortedIdx")
    for name in ("CTCSS_Options", "DCS_Options"):
        source += declaration("App/dcs.c", name)
    source += declaration("App/ui/menu.c", "MenuList")
    source += "const uint8_t FIRST_HIDDEN_MENU_ITEM = MENU_F_LOCK;\n"
    source += ui[ui.index("const char* const gSubMenu_TXP"):ui.index("bool    gIsInSubMenu;")]
    source += ui[ui.index("static const uint8_t CatChannels"):ui.index("// Nombre d'items")]
    for name in ("UI_MENU_GetMenuIdx", "UI_MENU_GetViewPos", "UI_MENU_GetCurrentMenuId", "UI_MENU_BuildView"):
        source += function("App/ui/menu.c", name)
    source += function("App/app/menu.c", "MENU_GetLimits")
    for name in ("gFontSmall", "gFontSmallBold", "gFont3x5"):
        source += declaration("App/font.c", name)
    for name in ("UI_PrintStringBuffer", "UI_PrintStringSmall", "UI_PrintStringSmallNormal", "UI_PrintStringSmallBold", "GUI_DisplaySmallest", "UI_DisplayClear"):
        source += function("App/ui/helper.c", name)
    source += re.sub(r'^#include[^\n]*\n', '', read("App/ui/clearui_text.c"), flags=re.M)
    for name in ("UI_CLEARUI_MenuChoiceLabel", "UI_CLEARUI_SettingsRow"):
        source += function("App/ui/menu.c", name)
    source += r'''
typedef int GUI_DisplayType_t;
enum {DISPLAY_MENU, DISPLAY_CLEAR_MENU, DISPLAY_MAIN, DISPLAY_QUICK, DISPLAY_SCAN_GROUP};
static bool gClearUIEditorActive, gClearUIIgnoreNextRelease;
static uint8_t gClearUIEditorReturnDisplay, gRequestDisplayScreen, gClearUIQuickSubSelection;
static int accepted_id, accepted_value;
static void MENU_AcceptSetting(void) {
    accepted_id = UI_MENU_GetCurrentMenuId(); accepted_value = gSubMenuSelection;
}
'''
    source += function("App/app/menu.c", "MENU_ReturnToClearUI")
    source += function("App/app/clearui.c", "CLEARUI_QuickApplyMenuSetting")
    source += r'''
#define CLEARUI_LIST_NAME_LENGTH 16
#define IS_MR_CHANNEL(channel) ((channel) < 1024)
typedef int KEY_Code_t;
enum {KEY_UP, KEY_DOWN, KEY_PTT, KEY_MENU, KEY_STAR, KEY_EXIT};
enum {BEEP_1KHZ_60MS_OPTIONAL, BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL};
enum {SCAN_OFF, SCAN_FWD};
static int gBeepToPlay, gScanStateDir;
static bool gClearUIEditingListNames, gClearUIListNameEditor;
static bool gClearUIScanMemoryMode, gClearUIListPickOnly;
static uint8_t gClearUIListNameCursor, gClearUIScanSelection;
static char gClearUIListEditName[17], saved_alias[17];
static struct {unsigned SCAN_LIST_DEFAULT; unsigned TX_VFO; bool SET_NAV; unsigned BACKLIGHT_TIME;} gEeprom = {1,0};
static uint8_t selected_group = 1;
static uint8_t CLEARUI_GetGroup(uint8_t vfo) {assert(vfo < 2); return selected_group;}
static bool CLEARUI_SelectGroup(uint8_t group) {
    assert(group >= 1 && group <= 25); selected_group=group; return true;
}
static unsigned scan_calls;
static void CHFRSCANNER_Stop(void) {gScanStateDir=SCAN_OFF;}
static void GENERIC_Key_PTT(bool pressed) {(void)pressed; gRequestDisplayScreen=DISPLAY_MAIN;}
static void SETTINGS_WriteCurrentState(void) {}
static void ACTION_Scan(bool restart) {(void)restart; ++scan_calls;}
static void CLEARUI_SaveListName(unsigned list, const char *name) {
    assert(list < 24); strcpy(saved_alias, name);
}
'''
    for name in ("CLEARUI_ScanItemCount", "CLEARUI_OpenScanMenu", "CLEARUI_ScanExecute", "CLEARUI_MoveSelection", "CLEARUI_SCAN_ProcessKeys"):
        source += function("App/app/clearui.c", name)
    source += "\n".join(re.findall(r"\benum\s*\{.*?\};", read("App/app/clearui.h"), re.S))
    source += r'''
#define CLEARUI_ALL_SETTINGS 255
#define CLEARUI_LIST_NAMES 254
static uint8_t gClearUIMenuLevel, gClearUIMenuCategory, gClearUIMenuSelection;
static uint8_t gClearUIQuickContext, gClearUIQuickSelection, gClearUIQuickLevel;
static uint8_t gClearUIQuickDirectItem=CLEARUI_QUICK_COUNT;
static bool gClearUIQuickScanMemory;
static void UI_CLEARUI_QuickSubLabel(uint8_t value, char *text) {(void)value; text[0]=0;}
static uint8_t CLEARUI_QuickSubCount(void) {return 0;}
static uint8_t CLEARUI_MenuItemCount(uint8_t category) {(void)category; return 1;}
static uint8_t CLEARUI_MenuItemId(uint8_t category, uint8_t row) {(void)category;(void)row;return MENU_STEP;}
static void UI_CLEARUI_RenderBackground(void) {
    UI_DisplayClear(); memset(gStatusLine,0,sizeof(gStatusLine));
    UI_ClearTextLine(gStatusLine,"A FM L1",2,126,false);
    UI_ClearText("145.470",5,126,0,false);
    UI_ClearText("442.750",5,126,6,false);
}
'''
    for name in ("CLEARUI_QUICK_MEMORY_ITEMS", "CLEARUI_QUICK_VFO_ITEMS", "CLEARUI_QUICK_SCAN_MEMORY_ITEMS", "CLEARUI_QUICK_SCAN_VFO_ITEMS"):
        source += declaration("App/app/clearui.c", name)
    for name in ("CLEARUI_QuickItems", "CLEARUI_QuickItemCount", "CLEARUI_QuickItemId"):
        source += function("App/app/clearui.c", name)
    source += r'''
static unsigned scope_calls, scope_vfo;
static bool gClearUINumericEntry;
static void APP_RunSpectrum(void) {++scope_calls; scope_vfo=gEeprom.TX_VFO;}
static void CLEARUI_QuickApply(void) {}
static uint8_t CLEARUI_QuickCurrentSelection(void) {return 0;}
'''
    source += function("App/app/clearui.c", "CLEARUI_QuickExecute")
    for name in ("MENU_CATEGORY_LABELS", "MENU_CATEGORY_ICONS", "QUICK_LABELS", "MENU_NAME_IDS"):
        source += declaration("App/ui/clearui.c", name)
    source += re.search(r"static const char MENU_NAMES\[\] =.*?\n;", read("App/ui/clearui.c"), re.S).group()
    for name in ("UI_CLEARUI_MenuItemName", "UI_CLEARUI_InvertTile", "UI_CLEARUI_Chevron", "UI_CLEARUI_DrawList", "UI_CLEARUI_List", "UI_CLEARUI_DrawScopeMenu", "UI_DisplayClearUIMenu", "UI_DisplayClearUIQuick", "UI_DisplayClearUIScanGroup"):
        source += function("App/ui/clearui.c", name)
    source += function("App/ui/menu.c", "UI_CLEARUI_DisplayMenuChoices")
    source += r'''
#define MENU_NAME_LENGTH 16
static uint8_t gInputBoxIndex;
static bool gFlagRefreshSetting;
static char edit[17];
static uint8_t edit_last_key;
static bool SCANNER_IsScanning(void) {return false;}
static void BACKLIGHT_TurnOff(void) {}
static int32_t NUMBER_AddWithWraparound(int32_t value,int32_t step,int32_t min,int32_t max) {
    value+=step; return value<min ? max : value>max ? min : value;
}
static uint32_t FREQUENCY_RoundToStep(uint32_t frequency,uint16_t step) {(void)step;return frequency;}
static uint16_t RADIO_FindNextChannel(uint16_t start,int8_t direction,bool scan,unsigned vfo) {
    (void)direction;(void)scan;(void)vfo;
    return start==65535 ? 1023 : start>1023 ? 0 : start;
}
'''
    source += function("App/app/menu.c", "MENU_ClampSelection")
    source += function("App/app/menu.c", "MENU_Key_UP_DOWN")
    source += r'''
static void preview(const char *path) {
    FILE *file=fopen(path,"wb"); assert(file); fputs("P5\n128 64\n255\n",file);
    for(unsigned y=0;y<64;y++) for(unsigned x=0;x<128;x++) {
        unsigned byte=y<8?gStatusLine[x]:gFrameBuffer[(y-8)/8][x];
        fputc((byte & (1u<<(y%8)))?0:255,file);
    }
    fclose(file);
}
int main(int argc, char **argv) {
    unsigned choices = 0;
    gMenuCategory = CAT_ALL; UI_MENU_BuildView(); gMenuLevel = MENU_LEVEL_ITEMS;
    // Physical Right is KEY_DOWN: its raw -1 must advance every choice list,
    // regardless of the legacy navigation setting. Left does the inverse.
    for(unsigned nav=0;nav<2;nav++) {
        gEeprom.SET_NAV=nav; gIsInSubMenu=true;
        const uint8_t ids[]={MENU_F1SHRT,MENU_F1LONG,MENU_TXP,MENU_STEP,MENU_BAT_TXT};
        for(unsigned i=0;i<ARRAY_SIZE(ids);i++) {
            gMenuCursor=UI_MENU_GetViewPos(ids[i]);
            int32_t min,max; assert(!MENU_GetLimits(ids[i],&min,&max));
            gSubMenuSelection=min;
            MENU_Key_UP_DOWN(true,false,-1); assert(gSubMenuSelection==min+1);
            MENU_Key_UP_DOWN(false,false,-1); assert(gSubMenuSelection==min+1);
            MENU_Key_UP_DOWN(true,false,1); assert(gSubMenuSelection==min);
            MENU_Key_UP_DOWN(true,true,1); assert(gSubMenuSelection==max);
            MENU_Key_UP_DOWN(true,true,-1); assert(gSubMenuSelection==min);
        }
        gMenuCursor=UI_MENU_GetViewPos(MENU_1_CALL); gSubMenuSelection=1023;
        MENU_Key_UP_DOWN(true,false,-1); assert(gSubMenuSelection==0);
        MENU_Key_UP_DOWN(true,false,1); assert(gSubMenuSelection==1023);
        gIsInSubMenu=false; gMenuCursor=0;
        MENU_Key_UP_DOWN(true,false,-1); assert(gMenuCursor==1);
        MENU_Key_UP_DOWN(true,false,1); assert(gMenuCursor==0);
    }
    gIsInSubMenu=false;
    const unsigned all_count = gMenuListCount;
    for (unsigned row = 0; row < all_count; ++row) {
        unsigned id = MenuList[gMenuIndices[row]].menu_id;
        const char *title = UI_CLEARUI_MenuItemName(id);
        assert(strlen(title) <= 30);
        for(unsigned n=0;title[n];n++) assert(title[n]>=32 && title[n]<=126);
        assert(UI_MENU_GetViewPos(id) == row);
        int32_t minimum, maximum;
        if (MENU_GetLimits(id, &minimum, &maximum) || id == MENU_VOL) continue;
        for (int value = minimum; value <= maximum; ++value) {
            struct {unsigned char before[8]; char text[64]; unsigned char after[8];} guard;
            memset(&guard, 0xa5, sizeof(guard));
            UI_CLEARUI_MenuChoiceLabel(id, value, guard.text);
            assert(strlen(guard.text) <= 30);
            assert(UI_ClearTextWidth(guard.text,255) - (strlen(guard.text)-1) <= 117);
            for(unsigned n=0;n<8;n++) assert(guard.before[n]==0xa5 && guard.after[n]==0xa5);
            UI_CLEARUI_SettingsRow(guard.text, value % 6, true);
            ++choices;
        }
    }
    // Every ASCII glyph and malformed input stays inside its requested text rectangle.
    for(unsigned c=1;c<=255;c++) for(unsigned left=0;left<128;left++) {
        unsigned char pixels[130]; memset(pixels,0xa5,sizeof(pixels));
        char glyph[2]={(char)c,0};
        UI_ClearTextLine(pixels+1,glyph,left,128,false);
        assert(pixels[0]==0xa5 && pixels[129]==0xa5);
        for(unsigned x=0;x<left;x++) assert(pixels[x+1]==0xa5);
    }
    assert(UI_ClearTextWidth("iii",255)<UI_ClearTextWidth("WWW",255));
    assert(strcmp(QUICK_LABELS[CLEARUI_QUICK_LIST],"Group select")==0);
    assert(strcmp(QUICK_LABELS[CLEARUI_QUICK_WATERFALL],"Scope")==0);
    // Both idle contexts expose one direct Scope action. It launches once
    // for either selected VFO and returns to the main screen after exit.
    for(unsigned context=0;context<2;context++) {
        gClearUIQuickContext=context ? CLEARUI_QUICK_CONTEXT_MEMORY : CLEARUI_QUICK_CONTEXT_VFO;
        unsigned found=0;
        for(unsigned row=0;row<CLEARUI_QuickItemCount();row++) {
            if(CLEARUI_QuickItemId(row)!=CLEARUI_QUICK_WATERFALL) continue;
            ++found; gClearUIQuickSelection=row;
            for(unsigned vfo=0;vfo<2;vfo++) {
                gEeprom.TX_VFO=vfo; gClearUIQuickLevel=0;
                const unsigned previous=scope_calls;
                CLEARUI_QuickExecute();
                assert(scope_calls==previous+1 && scope_vfo==vfo);
                assert(gRequestDisplayScreen==DISPLAY_MAIN && !gClearUIQuickLevel);
            }
        }
        assert(found==1);
    }
    gClearUIQuickContext=CLEARUI_QUICK_CONTEXT_SCAN;
    for(unsigned memory=0;memory<2;memory++) {
        gClearUIQuickScanMemory=memory;
        for(unsigned row=0;row<CLEARUI_QuickItemCount();row++)
            assert(CLEARUI_QuickItemId(row)!=CLEARUI_QUICK_WATERFALL);
    }
    gEeprom.TX_VFO=0;
    assert(strcmp(UI_CLEARUI_MenuItemName(MENU_S_LIST),"Group select")==0);
    assert(strcmp(UI_CLEARUI_MenuItemName(CLEARUI_LIST_NAMES),"Group names")==0);
    unnamed_group=true;
    char group_label[64];
    UI_CLEARUI_MenuChoiceLabel(MENU_S_LIST,1,group_label);
    assert(strcmp(group_label,"Group 01")==0);
    UI_CLEARUI_MenuChoiceLabel(MENU_S_LIST,25,group_label);
    assert(strcmp(group_label,"All channels")==0);
    unnamed_group=false;
    for(unsigned n=0;n<ARRAY_SIZE(QUICK_LABELS);n++)
        assert(UI_ClearTextWidth(QUICK_LABELS[n],255) - (strlen(QUICK_LABELS[n])-1) <= 100);
    for (unsigned category = 0; category < CAT_COUNT; ++category) {
        gMenuCategory = category; UI_MENU_BuildView();
        for(unsigned row=0;row<gMenuListCount;row++)
            assert(UI_MENU_GetViewPos(MenuList[gMenuIndices[row]].menu_id)==row);
        gClearUIQuickSubSelection = 12;
        CLEARUI_QuickApplyMenuSetting(MENU_STEP);
        assert(accepted_id==MENU_STEP && accepted_value==12);
        assert(gMenuCategory==CAT_ALL && gMenuLevel==MENU_LEVEL_ITEMS);
    }
    gClearUIEditorActive = true; gIsInSubMenu = true;
    assert(!MENU_ReturnToClearUI());
    gIsInSubMenu = false; gClearUIEditorReturnDisplay = DISPLAY_CLEAR_MENU;
    assert(MENU_ReturnToClearUI() && !gClearUIEditorActive && gClearUIIgnoreNextRelease);
    assert(gRequestDisplayScreen == DISPLAY_CLEAR_MENU);
    gClearUIEditorActive = true; gClearUIEditorReturnDisplay = DISPLAY_MENU;
    assert(MENU_ReturnToClearUI() && gClearUIEditorActive && !gClearUIIgnoreNextRelease);
    assert(gRequestDisplayScreen == DISPLAY_MENU);
    gClearUIEditingListNames=true; gClearUIScanMemoryMode=true;
    assert(CLEARUI_ScanItemCount()==24);
    gClearUIListNameEditor=false; gClearUIScanSelection=23;
    gClearUIIgnoreNextRelease=true;
    CLEARUI_SCAN_ProcessKeys(KEY_MENU,false,true);
    assert(!gClearUIIgnoreNextRelease && !gClearUIListNameEditor);
    CLEARUI_SCAN_ProcessKeys(KEY_MENU,false,false);
    assert(gClearUIListNameEditor && gClearUIListNameCursor==0);
    assert(strcmp(gClearUIListEditName,"ABCDEFGHIJKLMNOP")==0);
    for(unsigned n=0;n<16;n++) CLEARUI_SCAN_ProcessKeys(KEY_MENU,false,false);
    assert(gClearUIListNameCursor==0);
    CLEARUI_SCAN_ProcessKeys(KEY_UP,true,false);
    assert(gClearUIListEditName[0]=='B');
    CLEARUI_SCAN_ProcessKeys(KEY_STAR,false,false);
    assert(!gClearUIListNameEditor && saved_alias[0]=='B');
    CLEARUI_SCAN_ProcessKeys(KEY_MENU,false,false);
    CLEARUI_SCAN_ProcessKeys(KEY_PTT,true,false);
    CLEARUI_OpenScanMenu();
    assert(!gClearUIListNameEditor && !gClearUIEditingListNames && !gClearUIListPickOnly);
    assert(CLEARUI_ScanItemCount()==25);
    CLEARUI_SCAN_ProcessKeys(KEY_MENU,false,false);
    assert(scan_calls==1);
    // Main icons keep their selection tile but no separator grid. The gap
    // stays clear for every selection, including former horizontal crossings.
    gClearUIMenuLevel=0;
    for(unsigned selected=0;selected<CLEARUI_MENU_CATEGORY_COUNT;selected++) {
        gClearUIMenuCategory=selected;
        UI_DisplayClearUIMenu();
        for(unsigned y=8;y<56;y++)
            for(unsigned x=63;x<=64;x++)
                assert(!(gFrameBuffer[y/8][x] & (1u << (y%8))));
        const unsigned page=1+(selected/2)*2;
        const unsigned x=selected%2 ? 65 : 0;
        assert(gFrameBuffer[page][x]==0xff); // selection remains visible
    }
    gClearUIMenuCategory=0;
    // Scope composes over its own frame, preserving everything outside the
    // window. It must not clear the waterfall or use the VFO background.
    memset(gFrameBuffer,0xa5,sizeof(gFrameBuffer));
    memset(gStatusLine,0x5a,sizeof(gStatusLine));
    const char *scope_labels[]={"Trigger mode","Sweep step","Sweep points","Mode",
                               "Receive bandwidth","Clear history","Close scope"};
    UI_CLEARUI_DrawScopeMenu(NULL,scope_labels,7,0);
    for(unsigned x=0;x<128;x++) assert(gStatusLine[x]==0x5a);
    for(unsigned y=0;y<56;y++)
        for(unsigned x=0;x<128;x++)
            if(x<5 || x>122 || y<7 || y>48)
                assert((gFrameBuffer[y/8][x] & (1u << (y%8))) ==
                       (0xa5 & (1u << (y%8))));
    gMenuCategory=CAT_ALL; UI_MENU_BuildView(); gMenuCursor=UI_MENU_GetViewPos(MENU_STEP);
    gIsInSubMenu=true; gSubMenuSelection=13; edit_index=-1;
    memset(gFrameBuffer,0,sizeof(gFrameBuffer));
    memset(gStatusLine,0,sizeof(gStatusLine));
    UI_ClearTextLine(gStatusLine,"Tuning step",2,126,false);
    for(unsigned x=0;x<128;x++) gStatusLine[x]^=0x7f;
    char text[64]; assert(UI_CLEARUI_DisplayMenuChoices(text));
    // The direct Call picker supports all 1024 slots without narrowing indices.
    gMenuCursor=UI_MENU_GetViewPos(MENU_1_CALL); gIsInSubMenu=true;
    gClearUIEditorActive=true; gClearUIEditorReturnDisplay=DISPLAY_MAIN;
    for(unsigned channel=0;channel<1024;channel++) {
        gSubMenuSelection=channel; assert(UI_CLEARUI_DisplayMenuChoices(text));
    }
    if(argc > 1) {
        char callpath[1024];
        snprintf(callpath,sizeof(callpath),"%s.call.pgm",argv[1]); preview(callpath);
        const char *power[]={"Custom","Low 1","Low 2","Low 3","Low 4","Low 5","Mid","High"};
        UI_CLEARUI_RenderBackground();
        UI_CLEARUI_DrawScopeMenu("Transmit power",power,8,6);
        snprintf(callpath,sizeof(callpath),"%s.power.pgm",argv[1]); preview(callpath);
    }
    gClearUIEditorActive=false;
    if(argc > 1) {
        preview(argv[1]);
        char path[1024];
        UI_DisplayClearUIMenu(); snprintf(path,sizeof(path),"%s.icons.pgm",argv[1]); preview(path);
        gClearUIQuickSelection=1; gClearUIQuickContext=CLEARUI_QUICK_CONTEXT_MEMORY;
        UI_DisplayClearUIQuick(); snprintf(path,sizeof(path),"%s.quick.pgm",argv[1]); preview(path);
        for(unsigned row=0;row<CLEARUI_QuickItemCount();row++)
            if(CLEARUI_QuickItemId(row)==CLEARUI_QUICK_WATERFALL) gClearUIQuickSelection=row;
        UI_DisplayClearUIQuick(); snprintf(path,sizeof(path),"%s.scope.pgm",argv[1]); preview(path);
        // Synthetic history behind the real scope-menu renderer.
        UI_DisplayClear();
        for(unsigned y=8;y<40;y++) for(unsigned x=0;x<128;x++)
            if((x+y)%13<3) PutPixel(x,y,true);
        UI_ClearText("442.750",2,126,0,false);
        UI_CLEARUI_DrawScopeMenu(NULL,scope_labels,7,1);
        snprintf(path,sizeof(path),"%s.scope-quick.pgm",argv[1]); preview(path);
        const char *scope_steps[]={"6.25 kHz","8.33 kHz","10.00 kHz","12.50 kHz","15.00 kHz"};
        UI_CLEARUI_DrawScopeMenu("Sweep step",scope_steps,5,3);
        snprintf(path,sizeof(path),"%s.scope-step.pgm",argv[1]); preview(path);
        const char *modes[]={"FM","AM","USB"};
        UI_CLEARUI_RenderBackground(); UI_CLEARUI_List("Mode",modes,3,1,false,true,false);
        snprintf(path,sizeof(path),"%s.mode.pgm",argv[1]); preview(path);
        strcpy(gClearUIListEditName,"Public Safety   ");
        gClearUIListNameCursor=7; gClearUIListNameEditor=true;
        UI_DisplayClearUIScanGroup();
        snprintf(path,sizeof(path),"%s.list-name.pgm",argv[1]); preview(path);
        gClearUIListNameEditor=false; gClearUIEditingListNames=false;
        gClearUIScanMemoryMode=true; gClearUIScanSelection=0; gallery_groups=true;
        UI_DisplayClearUIScanGroup();
        snprintf(path,sizeof(path),"%s.groups.pgm",argv[1]); preview(path);
    }
    printf("Menu labels: %u choices; all category mappings, Quick apply, return states, and drawing bounds passed\n",choices);
}
'''
    with tempfile.TemporaryDirectory(prefix="clearui-menu-test-") as directory:
        cfile, binary = Path(directory) / "test.c", Path(directory) / "test"
        cfile.write_text(source)
        subprocess.run(["cc", "-std=gnu11", "-Wno-deprecated-declarations", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        str(cfile), "-o", str(binary)], check=True)
        subprocess.run([str(binary), *sys.argv[1:]], check=True)


if __name__ == "__main__":
    main()
