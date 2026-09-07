#!/usr/bin/env python3
"""Test production waterfall quick-menu logic and key timing with host stubs."""
from pathlib import Path
import subprocess
import tempfile
from test_clearui_menus import function, declaration

PREAMBLE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define ENABLE_CLEAR_UI
typedef int KEY_Code_t;
enum {KEY_INVALID, KEY_UP, KEY_DOWN, KEY_MENU, KEY_EXIT, KEY_PTT, KEY_0};
enum {SPECTRUM, FREQ_INPUT, STILL};
enum {STEPS_128, STEPS_64, STEPS_32, STEPS_16};
enum {MODULATION_FM, MODULATION_AM, MODULATION_USB, MODULATION_UKNOWN};
static struct {KEY_Code_t prev,current; unsigned counter;} kbd;
static struct {uint8_t scanStepIndex,stepsCount,modulationType,listenBw;
               uint16_t rssiTriggerLevel;} settings;
static bool manualSetFlag, scopeMenuOpen, scopeMenuChild, scopeMenuEatRelease;
static bool menuKeyPendingShort,menuKeyLongHandled,redrawScreen,redrawStatus;
static uint8_t scopeMenuRow,scopeMenuChoice,waterfallHistory[32][16],waterfallPhase;
static uint16_t rssiHistory[128];
static uint32_t gScanRangeStart;
static const uint16_t RSSI_MAX_VALUE=65535;
static unsigned launches,rx_off,exits,resets,passthrough,render_calls;
static int currentState=SPECTRUM;
static KEY_Code_t fakeKey;
static KEY_Code_t KEYBOARD_GetKey(void) {return fakeKey;}
static void SYSTEM_DelayMs(unsigned ms) {assert(ms==20);}
static void UpdateScanStep(bool inc) {assert(inc); settings.scanStepIndex=(settings.scanStepIndex+1)%15; ++launches;}
static void ToggleStepsCount(void) {settings.stepsCount=(settings.stepsCount+3)%4; ++launches;}
static void ToggleModulation(void) {settings.modulationType=(settings.modulationType+1)%3; ++launches;}
static void ToggleRX(bool on) {assert(!on); ++rx_off;}
static void RelaunchScan(void) {++launches;}
static void OnKeyDown(uint8_t key);
static void ResetSpectrumToDefaults(void) {++resets;}
static bool OnKeyDownCommon(uint8_t key) {(void)key; ++passthrough; return false;}
static void OnKeyDownFreqInput(KEY_Code_t key) {(void)key; ++passthrough;}
static void OnKeyDownStill(KEY_Code_t key) {(void)key; ++passthrough;}
static void UI_CLEARUI_DrawScopeMenu(const char *title,const char *const *labels,
                                    uint8_t count,uint8_t selection) {
    assert(count>0 && count<=15 && selection<count);
    if(title) assert(strlen(title)<24);
    for(unsigned i=0;i<count;i++) {
        assert(labels[i] && strlen(labels[i])>0 && strlen(labels[i])<24);
        for(unsigned j=0;labels[i][j];j++) assert(labels[i][j]>=32 && labels[i][j]<=126);
    }
    ++render_calls;
}
'''

TESTS = r'''
static void OnKeyDown(uint8_t key) {
    if(key==KEY_MENU) ClearUIScopeOpen();
    else if(key==KEY_EXIT) ++exits;
    else ++passthrough;
}
static void tick(KEY_Code_t key,unsigned ticks) {
    fakeKey=key;
    for(unsigned i=0;i<ticks;i++) HandleUserInput();
}
static void tap(KEY_Code_t key) {tick(key,5); tick(KEY_INVALID,1);}
static void open_menu(void) {
    kbd.current=KEY_INVALID; scopeMenuEatRelease=false;
    ClearUIScopeOpen(); assert(scopeMenuOpen && !scopeMenuChild);
}
int main(void) {
    // Actual debounce/hold dispatcher: opening release cannot choose an item.
    tap(KEY_MENU); assert(scopeMenuOpen && !scopeMenuChild);
    tap(KEY_MENU); assert(scopeMenuChild);
    tap(KEY_DOWN); assert(scopeMenuChoice==1 && !manualSetFlag);
    tap(KEY_EXIT); assert(scopeMenuOpen && !scopeMenuChild && !manualSetFlag);
    tap(KEY_EXIT); assert(!scopeMenuOpen);
    // Holding MENU opens once, never invokes the old destructive reset.
    tick(KEY_MENU,40); assert(scopeMenuOpen && !scopeMenuChild && resets==0);
    tick(KEY_INVALID,1); assert(!scopeMenuChild);
    tap(KEY_MENU); assert(scopeMenuChild);
    tap(KEY_DOWN);
    tick(KEY_MENU,40); assert(!scopeMenuOpen && manualSetFlag && resets==0);
    tick(KEY_INVALID,1); assert(!scopeMenuOpen);
    // Popup captures other shortcuts and PTT until release.
    open_menu(); unsigned before=passthrough;
    tap(KEY_0); assert(passthrough==before && scopeMenuOpen);
    tick(KEY_PTT,40); assert(!scopeMenuOpen && passthrough==before);
    tick(KEY_INVALID,1);
    // Every setting/value commits through its existing spectrum helper.
    for(unsigned row=0;row<ClearUIScopeCount();row++) {
        open_menu(); scopeMenuRow=row; ClearUIScopeRender();
        unsigned item=ClearUIScopeItem(row), count=ClearUIScopeChoiceCount(item);
        if(!count) continue;
        for(unsigned choice=0;choice<count;choice++) {
            open_menu(); scopeMenuRow=row; ClearUIScopeKey(KEY_MENU);
            assert(scopeMenuChild && scopeMenuChoice==ClearUIScopeCurrent(item));
            scopeMenuChoice=choice; ClearUIScopeRender();
            memset(waterfallHistory,0xa5,sizeof(waterfallHistory));
            memset(rssiHistory,0x5a,sizeof(rssiHistory));
            ClearUIScopeKey(KEY_MENU); assert(!scopeMenuOpen);
            if(item<5) assert(ClearUIScopeCurrent(item)==choice);
            if(item==5) {
                assert(waterfallHistory[0][0]==(choice ? 0 : 0xa5));
                assert(rssiHistory[0]==0x5a5a);
            }
        }
    }
    assert(launches && rx_off && render_calls);
    // Parent and child navigation wraps. Exiting an uncommitted edit saves nothing.
    open_menu(); ClearUIScopeKey(KEY_UP); assert(scopeMenuRow==ClearUIScopeCount()-1);
    ClearUIScopeKey(KEY_DOWN); assert(scopeMenuRow==0);
    ClearUIScopeKey(KEY_MENU); scopeMenuChoice=0;
    ClearUIScopeKey(KEY_UP); assert(scopeMenuChoice==1);
    bool saved=manualSetFlag; ClearUIScopeKey(KEY_EXIT); assert(manualSetFlag==saved);
    // Close scope explicitly invokes its normal exit/save path exactly once.
    scopeMenuRow=ClearUIScopeCount()-1; before=exits;
    ClearUIScopeKey(KEY_MENU); assert(exits==before+1 && !scopeMenuOpen);
#ifdef ENABLE_SCAN_RANGES
    gScanRangeStart=44000000;
    assert(ClearUIScopeCount()==6);
    for(unsigned row=0;row<ClearUIScopeCount();row++) {
        assert(ClearUIScopeItem(row)!=2);
        open_menu(); scopeMenuRow=row; ClearUIScopeRender();
    }
#endif
    puts("Scope quick menu: settings, cancel/apply, labels, range mapping, hold/release, PTT isolation passed");
    return 0;
}
'''

def main():
    routines = declaration('App/app/spectrum.h', 'scanStepValues')
    routines += declaration('App/app/spectrum.c', 'scopeMenuLabels')
    for name in ('ClearUIScopeItem', 'ClearUIScopeCount', 'ClearUIScopeChoiceCount',
                 'ClearUIScopeCurrent', 'ClearUIScopeOpen', 'ClearUIScopeClose',
                 'ClearUIScopeApply', 'ClearUIScopeKey', 'ClearUIScopeHandleKeys',
                 'ClearUIScopeRender', 'HandleUserInput'):
        routines += function('App/app/spectrum.c', name)
    with tempfile.TemporaryDirectory(prefix='clearui-scope-test-') as directory:
        source, binary = Path(directory)/'test.c', Path(directory)/'test'
        source.write_text(PREAMBLE + routines + TESTS)
        for flags in ([], ['-DENABLE_SCAN_RANGES']):
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Wno-unused-function',
                            '-Wno-unused-variable', '-fsanitize=address,undefined',
                            *flags, str(source), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

if __name__ == '__main__':
    main()
