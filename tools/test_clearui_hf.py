#!/usr/bin/env python3
"""Exercise production HF controls, bounds and pixels without a radio.

Optional argument: directory for actual-renderer PGM screen fixtures.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from test_clearui_menus import function, declaration, read

PREAMBLE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "clearui_font.h"
#define ENABLE_CLEAR_UI
#define ENABLE_SCAN_RANGES
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define LCD_WIDTH 128
#define F_MIN 1800000u
#define F_MAX 130000000u
#define LISTEN_OPEN_HYST_RSSI 5
enum {KEY_INVALID, KEY_UP, KEY_DOWN, KEY_MENU, KEY_EXIT, KEY_PTT, KEY_STAR, KEY_0};
enum {SPECTRUM, STILL};
typedef unsigned KEY_Code_t;
static struct {KEY_Code_t current; unsigned counter;} kbd;
struct FrequencyBandInfo {uint32_t lower,upper,middle;};
static bool hfListen=true, hfEatRelease, hfMenuPending, monitorMode, newScanStart;
static bool manualSetFlag;
static uint32_t gScanRangeStart,gScanRangeStop;
static bool redrawScreen,redrawStatus,isListening;
static uint8_t hfBand=3,hfMenu,hfSelection,currentState;
static uint32_t currentFreq,fMeasure;
static uint8_t waterfallHistory[32][16],waterfallPhase;
static uint16_t rssiHistory[128];
static char String[32];
static uint8_t gFrameBuffer[7][128],gStatusLine[128];
static uint8_t gBatteryDisplayLevel=5,gSetting_battery_text;
static uint16_t gBatteryVoltageAverage=810;
static bool gLowBatteryBlink;
static unsigned BATTERY_VoltsToPercent(unsigned volts){(void)volts;return 97;}
typedef struct {unsigned modulationType,listenBw,rssiTriggerLevel;} SpectrumSettings;
static SpectrumSettings settings;
static struct {unsigned rssi;} peak;
static const uint16_t RSSI_MAX_VALUE=65535;
static unsigned exits,relaunches,mode_changes;
static uint16_t GetStepsCount(void){return 64;}
static uint16_t GetScanStep(void){return 50;}
static uint32_t GetBW(void){return GetStepsCount()*GetScanStep();}
static bool IsCenterMode(void){return true;}
static void SetState(unsigned state){currentState=state;}
static void SetF(uint32_t f){fMeasure=f;}
static void ToggleRX(bool on){isListening=on;}
static void DeInitSpectrum(void){++exits;}
static void RelaunchScan(void){++relaunches;ToggleRX(false);}
static void RADIO_SetModulation(unsigned mode){assert(mode<3);++mode_changes;}
static void APP_RunSpectrum(void){
    assert(hfListen && !gScanRangeStart && !gScanRangeStop);
    settings.modulationType=2;settings.listenBw=2;settings.rssiTriggerLevel=65535;
    manualSetFlag=monitorMode=true;
}
static void PutPixel(uint8_t x,uint8_t y,bool on){assert(x<128 && y<56); if(on)gFrameBuffer[y/8][x]|=1u<<(y%8);else gFrameBuffer[y/8][x]&=~(1u<<(y%8));}
static void PutPixelStatus(uint8_t x,uint8_t y,bool on){assert(x<128 && y<8);if(on)gStatusLine[x]|=1u<<y;else gStatusLine[x]&=~(1u<<y);}
static void UI_DrawPixelBuffer(uint8_t (*buffer)[128],uint8_t x,uint8_t y,bool on){assert(buffer==gFrameBuffer);PutPixel(x,y,on);}
static bool IsRssiHistoryInvalid(uint16_t rssi){return !rssi || rssi==65535;}
static uint16_t InterpolateRssi(uint8_t bars,uint16_t pos){assert(bars==64);return rssiHistory[pos>>8];}
static uint8_t Rssi2PX(uint16_t rssi,uint8_t min,uint8_t max){(void)min;return rssi>max ? max:rssi;}
static void UI_CLEARUI_DrawScopeMenu(const char *title,const char *const *labels,uint8_t count,uint8_t selection){
    assert(title && count>=2 && count<=3 && selection<count);
    for(unsigned i=0;i<count;i++)assert(labels[i] && strlen(labels[i])<24);
}
'''

TESTS = r'''
static void tap(KEY_Code_t key) {
    kbd.current=key; kbd.counter=3; assert(HFHandleKeys());
    kbd.current=KEY_INVALID; kbd.counter=0; assert(HFHandleKeys());
}
static void hold_menu(void) {
    kbd.current=KEY_MENU;kbd.counter=3;HFHandleKeys();assert(!hfMenu && hfMenuPending);
    kbd.counter=16;HFHandleKeys();assert(hfMenu==4 && !hfMenuPending);
    for(unsigned i=0;i<8;i++) { HFHandleKeys(); }
    assert(hfMenu==4 && hfSelection==0);
    kbd.current=KEY_INVALID;kbd.counter=0;HFHandleKeys();assert(hfMenu==4);
}
static void dump(const char *dir,const char *name) {
    if(!dir)return;
    char path[1024];snprintf(path,sizeof(path),"%s/%s.pgm",dir,name);
    FILE *f=fopen(path,"wb");assert(f);fprintf(f,"P5\n128 64\n255\n");
    for(unsigned y=0;y<64;y++)for(unsigned x=0;x<128;x++) {
        const uint8_t b=y<8?gStatusLine[x]:gFrameBuffer[(y-8)/8][x];
        fputc(b&(1u<<(y%8))?0:255,f);
    }
    fclose(f);
}
int main(int argc,char **argv) {
    currentFreq=hfBands[3].middle;
    // A held entry key cannot accidentally select or tune after opening HF.
    hfEatRelease=true;kbd.current=KEY_MENU;kbd.counter=3;HFHandleKeys();assert(!hfMenu);
    kbd.current=KEY_INVALID;HFHandleKeys();assert(!hfEatRelease);
    tap(KEY_MENU);assert(hfMenu==1 && hfSelection==3);
    tap(KEY_DOWN);assert(hfSelection==0);tap(KEY_EXIT);assert(!hfMenu);
    hold_menu();tap(KEY_MENU);assert(hfMenu==2);
    tap(KEY_DOWN);tap(KEY_MENU);assert(!hfMenu && settings.modulationType==1 && mode_changes==1);
    tap(KEY_MENU);tap(KEY_UP);tap(KEY_MENU);assert(hfBand==2 && currentFreq==2495000);
    // Child cancel returns to the correct parent option; parent cancel keeps band.
    hold_menu();tap(KEY_MENU);assert(hfMenu==2);
    tap(KEY_EXIT);assert(hfMenu==4 && hfSelection==0);tap(KEY_DOWN);tap(KEY_MENU);
    assert(hfMenu==3);tap(KEY_UP);tap(KEY_MENU);assert(settings.listenBw==2);
    tap(KEY_MENU);tap(KEY_DOWN);tap(KEY_EXIT);assert(hfBand==2 && !hfMenu);
    // Band picker wraps and only commits with Menu; PTT dismisses, never TX.
    tap(KEY_MENU);hfSelection=0;tap(KEY_UP);assert(hfSelection==3);
    tap(KEY_DOWN);assert(hfSelection==0);tap(KEY_PTT);assert(!hfMenu && !isListening);
    tap(KEY_STAR);assert(currentState==STILL && isListening && monitorMode && fMeasure==currentFreq);
    const uint32_t before=currentFreq;tap(KEY_DOWN);assert(currentFreq==before+10 && fMeasure==currentFreq);
    kbd.current=KEY_DOWN;kbd.counter=16;HFHandleKeys();assert(currentFreq==before+510);
    tap(KEY_EXIT);assert(currentState==SPECTRUM && !isListening && !monitorMode);
    tap(KEY_PTT);assert(currentState==STILL && isListening);
    tap(KEY_PTT);assert(currentState==SPECTRUM && !isListening);
    tap(KEY_EXIT);assert(exits==1);
    // Sweep endpoints and tuning stay in all four bands, including both edges.
    for(hfBand=0;hfBand<4;hfBand++) {
        for(uint32_t f=hfBands[hfBand].lower;f<=hfBands[hfBand].upper;f+=10) {
            currentFreq=f;
            assert(GetFStart()>=hfBands[hfBand].lower && GetFEnd()<=hfBands[hfBand].upper);
            assert(GetFEnd()-GetFStart()==3150 && GetFStart()<=f && GetFEnd()>=f);
        }
        currentFreq=hfBands[hfBand].lower;tap(KEY_UP);assert(currentFreq==hfBands[hfBand].lower);
        currentFreq=hfBands[hfBand].upper;tap(KEY_DOWN);assert(currentFreq==hfBands[hfBand].upper);
        assert(HFClampFrequency(0)==hfBands[hfBand].lower);
        assert(HFClampFrequency(130000000)==hfBands[hfBand].upper);
    }
    // Even an invalid/max RSSI cannot trigger automatic listening in HF.
    peak.rssi=65535;settings.rssiTriggerLevel=0;assert(!IsPeakOverOpenLevel());
    hfListen=false;assert(IsPeakOverOpenLevel());assert(!HFHandleKeys());hfListen=true;
    // Temporary HF settings/range never replace the normal scope session.
    const SpectrumSettings saved=settings;
    gScanRangeStart=44000000;gScanRangeStop=45000000;manualSetFlag=false;
    APP_RunHFListen();
    assert(!hfListen && !manualSetFlag && !monitorMode && currentState==SPECTRUM);
    assert(memcmp(&saved,&settings,sizeof(settings))==0);
    assert(gScanRangeStart==44000000 && gScanRangeStop==45000000);
    gScanRangeStart=gScanRangeStop=0;hfListen=true;
    // Render both extremes, noisy traces, menu states; ASAN catches buffer overruns.
    hfBand=3;currentFreq=hfBands[3].middle;hfMenu=0;
    for(unsigned n=0;n<256;n++) {
        for(unsigned x=0;x<128;x++)rssiHistory[x]=(x+n)%19;
        memset(waterfallHistory,n,sizeof(waterfallHistory));
        memset(gFrameBuffer,0,sizeof(gFrameBuffer));HFRender();
    }
    for(unsigned menu=1;menu<=4;menu++) {
        hfMenu=menu;for(hfSelection=0;hfSelection<(menu==1?4:menu==4?2:3);hfSelection++)HFRender();
    }
    hfMenu=0;memset(waterfallHistory,0,sizeof(waterfallHistory));
    for(unsigned row=0;row<32;row++)for(unsigned x=0;x<128;x++) {
        const unsigned d=abs((int)x-64),d2=abs((int)x-25),d3=abs((int)x-104);
        unsigned v=d<6?15-d*2:d2<5?10-d2*2:d3<4?12-d3*3:1;
        if(row==0 && x%2==0)rssiHistory[x/2]=v;
        if(v>3 && (x+row*3)%16<v)waterfallHistory[row][x/8]|=1u<<(x%8);
    }
    memset(gFrameBuffer,0,sizeof(gFrameBuffer));HFRender();
    settings.modulationType=2;HFHeader();
    dump(argc>1?argv[1]:NULL,"hf-combined");
    uint8_t beforeWindow[7][128];memcpy(beforeWindow,gFrameBuffer,sizeof(beforeWindow));
    hfMenu=1;hfSelection=3;HFBandWindow();
    for(unsigned y=0;y<56;y++)for(unsigned x=0;x<128;x++)
        if(x<23 || x>105 || y>52)
            assert(((gFrameBuffer[y/8][x]^beforeWindow[y/8][x])&(1u<<(y%8)))==0);
    dump(argc>1?argv[1]:NULL,"hf-band-picker");
    // Battery icon/percentage/both/voltage never overwrite the state pill.
    for(gSetting_battery_text=0;gSetting_battery_text<4;gSetting_battery_text++) {
        uint8_t expected[24];memcpy(expected,gStatusLine+69,24);HFHeader();
        assert(memcmp(expected,gStatusLine+69,24)==0);
    }
    puts("HF: band bounds, controls, cancel/apply, PTT isolation, explicit listening and pixel bounds passed");
}
'''


def main():
    source = PREAMBLE
    source += 'static const char *const gModulationStr[]={"FM","AM","USB"};\n'
    source += declaration('App/font.c', 'gFont3x5')
    source += function('App/ui/helper.c', 'GUI_DisplaySmallest')
    for name in ('CLEARUI_DrawNameAt', 'UI_CLEARUI_DrawLargeText',
                 'CLEARUI_DrawCompactBattery', 'UI_CLEARUI_DrawBattery'):
        source += function('App/ui/clearui_main.c', name)
    for name in ('hfBands', 'hfBandNames', 'hfMenuLabels'):
        source += declaration('App/app/spectrum.c', name)
    source += re.sub(r'^#include[^\n]*\n', '', read('App/ui/clearui_text.c'), flags=re.M)
    for name in ('GetFStart', 'GetFEnd', 'ResetWaterfall', 'IsPeakOverOpenLevel',
                 'HFPixel', 'HFSmallText', 'HFHeader', 'HFBandWindow',
                 'HFClampFrequency', 'HFStartSweep', 'HFStartListening',
                 'HFMenuKey', 'HFHandleKeys', 'HFRender', 'APP_RunHFListen'):
        source += function('App/app/spectrum.c', name)
    with tempfile.TemporaryDirectory(prefix='clearui-hf-test-') as directory:
        path, binary = Path(directory)/'hf.c', Path(directory)/'hf'
        path.write_text(source + TESTS)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-variable', '-Wno-deprecated-declarations',
                        '-fsanitize=address,undefined',
                        '-I', str(Path(__file__).resolve().parents[1] / 'App'),
                        str(Path(__file__).resolve().parents[1] / 'App/clearui_font.c'),
                        str(path), '-o', str(binary)], check=True)
        if len(sys.argv) > 1:
            Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
        subprocess.run([str(binary), *sys.argv[1:]], check=True)


if __name__ == '__main__':
    main()
