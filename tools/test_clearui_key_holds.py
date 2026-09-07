#!/usr/bin/env python3
"""Production long-hold routing with host stubs; no radio writes."""
from pathlib import Path
import re
import subprocess
import tempfile
from test_clearui_menus import function, declaration, read

PREAMBLE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define ENABLE_CLEAR_UI
#define ENABLE_VOX
#define ENABLE_FEAT_F4HWN_MENU_CAT
#define ENABLE_FEAT_F4HWN_RESCUE_OPS
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define IS_MR_CHANNEL(ch) ((ch)<1024)
#define MR_CHANNELS_LIST 24
typedef int KEY_Code_t;
enum {KEY_0,KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7,KEY_8,KEY_9,
      KEY_UP,KEY_DOWN,KEY_MENU,KEY_STAR,KEY_EXIT,KEY_PTT};
enum {DISPLAY_MAIN,DISPLAY_QUICK,DISPLAY_MENU};
enum {BEEP_1KHZ_60MS_OPTIONAL,BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL};
enum {SCAN_OFF,CAT_ALL,MENU_LEVEL_ITEMS,MENU_1_CALL};
static struct {bool VFO_OPEN,MENU_LOCK;} gEeprom={true,false};
static struct {unsigned CHANNEL_SAVE;} txvfo={1};
static __typeof__(txvfo) *gTxVfo=&txvfo;
static uint16_t gNextMrChannel;
static uint8_t gClearUIQuickContext,gClearUIQuickSelection,gClearUIQuickSubSelection,gClearUIQuickLevel;
static bool gClearUIQuickScanMemory,gClearUIEditorActive,gClearUIPendingEditor;
static bool gClearUIIgnoreNextRelease,gWasFKeyPressed,gClearUINumericEntry;
static unsigned gMenuCategory,gMenuLevel,gMenuCursor,gClearUIEditorReturnDisplay;
static unsigned gBeepToPlay,gRequestDisplayScreen,gInputBoxIndex,gScanStateDir,applied;
static int edit_index;
static void UI_MENU_BuildView(void) {}
static uint8_t UI_MENU_GetViewPos(uint8_t id) {return id;}
static void MENU_ShowCurrentSetting(void) {}
static void GENERIC_Key_PTT(bool pressed) {if(pressed)gRequestDisplayScreen=DISPLAY_MAIN;}
static void CLEARUI_MoveSelection(uint8_t *p,uint8_t count,int8_t dir,unsigned display) {
    *p=(*p+count+dir)%count; gRequestDisplayScreen=display;
}
'''

TESTS = r'''
static void fresh(void) {
    gScanStateDir=SCAN_OFF; gWasFKeyPressed=false; gEeprom.MENU_LOCK=false;
    gInputBoxIndex=0; gClearUINumericEntry=false; gClearUIIgnoreNextRelease=false;
    gRequestDisplayScreen=DISPLAY_MAIN;
}
int main(void) {
    const KEY_Code_t keys[]={KEY_1,KEY_3,KEY_6,KEY_7,KEY_8};
    const uint8_t items[]={CLEARUI_QUICK_BAND,CLEARUI_QUICK_VFO_MEMORY,
        CLEARUI_QUICK_POWER,CLEARUI_QUICK_VOX,CLEARUI_QUICK_REVERSE};
    for(unsigned memory=0;memory<2;memory++) for(unsigned k=0;k<5;k++) {
        fresh(); txvfo.CHANNEL_SAVE=memory ? 12 : 1024;
        assert(!MAIN_ClearUIKeyHold(keys[k],true,false)); // tap stays a digit
        assert(MAIN_ClearUIKeyHold(keys[k],true,true));
        assert(gRequestDisplayScreen==DISPLAY_QUICK && gClearUIQuickLevel==1);
        assert(CLEARUI_QuickItemId(0)==items[k] && gClearUIIgnoreNextRelease);
        assert(txvfo.CHANNEL_SAVE==(memory ? 12 : 1024)); // opening does not tune
        CLEARUI_QUICK_ProcessKeys(keys[k],false,true); // swallow held release
        assert(!gClearUIIgnoreNextRelease && applied==0);
        CLEARUI_QUICK_ProcessKeys(KEY_EXIT,false,false);
        assert(gRequestDisplayScreen==DISPLAY_MAIN && gClearUIQuickDirectItem==CLEARUI_QUICK_COUNT);
        assert(!gClearUIQuickLevel && applied==0);
        assert(MAIN_ClearUIKeyHold(keys[k],true,true));
        CLEARUI_QUICK_ProcessKeys(keys[k],false,true);
        CLEARUI_QUICK_ProcessKeys(KEY_MENU,false,false); assert(applied==1); applied=0;
        fresh(); gWasFKeyPressed=true;
        assert(!MAIN_ClearUIKeyHold(keys[k],true,true));
        fresh(); gInputBoxIndex=1;
        assert(MAIN_ClearUIKeyHold(keys[k],true,true) && gRequestDisplayScreen==DISPLAY_MAIN);
        fresh(); gClearUINumericEntry=true;
        assert(MAIN_ClearUIKeyHold(keys[k],true,true) && gRequestDisplayScreen==DISPLAY_MAIN);
        fresh(); gEeprom.MENU_LOCK=true;
        assert(MAIN_ClearUIKeyHold(keys[k],true,true) && gRequestDisplayScreen==DISPLAY_MAIN);
    }
    fresh(); assert(!MAIN_ClearUIKeyHold(KEY_2,true,true));
    assert(!MAIN_ClearUIKeyHold(KEY_4,true,true));
    assert(!MAIN_ClearUIKeyHold(KEY_0,true,true));
    assert(!MAIN_ClearUIKeyHold(KEY_5,true,true));
    assert(MAIN_ClearUIKeyHold(KEY_9,true,true));
    assert(gRequestDisplayScreen==DISPLAY_MENU && gMenuCursor==MENU_1_CALL);
    assert(gClearUIPendingEditor && gClearUIEditorReturnDisplay==DISPLAY_MAIN);
    fresh(); gEeprom.VFO_OPEN=false;
    assert(MAIN_ClearUIKeyHold(KEY_1,true,true) && gRequestDisplayScreen==DISPLAY_MAIN);
    fresh(); gEeprom.VFO_OPEN=true; gScanStateDir=1;
    assert(!MAIN_ClearUIKeyHold(KEY_6,true,true));
    puts("Key holds: mappings, tap/F-key preservation, numeric/lock guards, held release, cancel/apply passed");
}
'''

def main():
    source=PREAMBLE + '\n'.join(re.findall(r'\benum\s*\{.*?\};',read('App/app/clearui.h'),re.S))
    source+='\nstatic uint8_t gClearUIQuickDirectItem=CLEARUI_QUICK_COUNT;\n'
    source+='static uint8_t gClearUIQuickLastSelection[CLEARUI_QUICK_CONTEXT_COUNT];\n'
    for name in ('CLEARUI_QUICK_MEMORY_ITEMS','CLEARUI_QUICK_VFO_ITEMS','CLEARUI_QUICK_SCAN_MEMORY_ITEMS','CLEARUI_QUICK_SCAN_VFO_ITEMS'):
        source+=declaration('App/app/clearui.c',name)
    for name in ('CLEARUI_QuickItems','CLEARUI_QuickItemCount','CLEARUI_QuickItemId','CLEARUI_OpenQuickMenu'):
        source+=function('App/app/clearui.c',name)
    source+='static uint8_t CLEARUI_QuickSubCount(void) {return 11;}\n'
    source+='static uint8_t CLEARUI_QuickCurrentSelection(void) {return 1;}\n'
    source+='static void CLEARUI_QuickExecute(void) {++applied;}\n'
    source+=function('App/app/clearui.c','CLEARUI_OpenKeyMenu')
    source+=function('App/app/main.c','MAIN_ClearUIKeyHold')
    source+=function('App/app/clearui.c','CLEARUI_QUICK_ProcessKeys')
    with tempfile.TemporaryDirectory(prefix='clearui-key-holds-') as directory:
        cfile,binary=Path(directory)/'test.c',Path(directory)/'test'
        cfile.write_text(source+TESTS)
        subprocess.run(['cc','-std=gnu11','-fsanitize=address,undefined',str(cfile),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)

if __name__=='__main__': main()
