#!/usr/bin/env python3
"""Exercise production scan/watch transitions and A/B selection with host stubs."""
import subprocess
import tempfile
from pathlib import Path
from test_clearui_menus import function, ROOT


def main():
    source = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ENABLE_CLEAR_UI
#define ENABLE_FEAT_F4HWN
#define SCAN_OFF 0
#define DUAL_WATCH_OFF 0
#define CROSS_BAND_OFF 0
#define CODE_TYPE_OFF 0
#define FUNCTION_FOREGROUND 0
#define FUNCTION_INCOMING 1
#define FUNCTION_RECEIVE 2
#define FUNCTION_MONITOR 3
#define RX_MODE_NONE 0
#define VFO_CONFIGURE_NONE 0
#define VFO_CONFIGURE_RELOAD 2
#define DISPLAY_MAIN 0
#define IS_MR_CHANNEL(c) ((c)<1024)
#define IS_FREQ_CHANNEL(c) ((c)>=1024)
#define scan_pause_delay_in_5_10ms 10
typedef struct { unsigned Frequency; } Freq;
typedef struct { unsigned CHANNEL_SAVE; Freq freq_config_RX; } VFO;
static struct { unsigned RX_VFO, TX_VFO, DUAL_WATCH, CROSS_BAND_RX_TX;
 unsigned SCAN_RESUME_MODE, MrChannel[2], ScreenChannel[2]; VFO VfoInfo[2]; } gEeprom;
static VFO *gRxVfo,*gTxVfo,*gCurrentVfo;
static uint8_t scanOwner;
static bool scanWatchingOther, gScanKeepResult, gScanPauseMode, gScheduleScanListen;
static bool gClearUIScanWatch;
static bool gMonitor, gUpdateDisplay, gUpdateStatus, gHasVfoBackup;
static bool gFlagReconfigureVfos,gScheduleDualWatch;
static unsigned gInputBoxIndex, gVfoConfigureMode,gRequestDisplayScreen,gRequestSaveSettings;
static unsigned gCurrentFunction,gCurrentCodeType,gScanPauseDelayIn_10ms,gRxReceptionMode;
static int gScanStateDir;
static unsigned gNextMrChannel,lastFoundFrqOrChan,lastFoundFrqOrChanOld,initialFrqOrChan;
static unsigned initialCROSS_BAND_RX_TX, tunes, steps, savedVfo, groupSyncs;
static void RADIO_SetupRegisters(bool fg) {(void)fg; ++tunes; gCurrentFunction=FUNCTION_FOREGROUND;}
static void NextMemChannel(void) { assert(gEeprom.RX_VFO==scanOwner); ++steps; ++gNextMrChannel; }
static void NextFreqChannel(void) { assert(gEeprom.RX_VFO==scanOwner); ++steps; }
static void RADIO_SelectVfos(void) {gEeprom.RX_VFO=gEeprom.TX_VFO;gTxVfo=&gEeprom.VfoInfo[gEeprom.TX_VFO];gRxVfo=gTxVfo;gCurrentVfo=gRxVfo;}
static void RADIO_ConfigureChannel(unsigned v,unsigned mode) {(void)mode;savedVfo=v;gEeprom.VfoInfo[v].CHANNEL_SAVE=gEeprom.ScreenChannel[v];}
static void SETTINGS_SaveVfoIndices(void) {}
static void RADIO_ApplyOffset(VFO *v) {(void)v;}
static void RADIO_ConfigureSquelchAndOutputPower(VFO *v) {(void)v;}
static void SETTINGS_SaveChannel(unsigned ch,unsigned v,VFO *p,unsigned mode) {(void)ch;(void)p;(void)mode;savedVfo=v;}
static void CLEARUI_SyncGroup(void) {++groupSyncs;}
static void CHFRSCANNER_AbortActiveReception(void) {gCurrentFunction=FUNCTION_FOREGROUND;}
void CHFRSCANNER_Found(void);
static void APP_StartListening(unsigned f) {gCurrentFunction=f;CHFRSCANNER_Found();}
'''
    scanner = 'App/app/chFrScanner.c'
    for name in ['CHFRSCANNER_Owner', 'CHFRSCANNER_IsWatchingOther', 'ScanSelectReceiver',
                 'CHFRSCANNER_Found', 'CHFRSCANNER_ContinueScanning', 'CHFRSCANNER_Stop']:
        source += function(scanner, name)
    source += function('App/app/common.c', 'COMMON_SwitchVFOs')
    source += r'''
static void begin(unsigned owner, bool memory) {
 memset(&gEeprom,0,sizeof(gEeprom)); scanOwner=owner;scanWatchingOther=false;
 gEeprom.TX_VFO=owner;gEeprom.RX_VFO=owner;gEeprom.DUAL_WATCH=owner+1;gClearUIScanWatch=true;
 gEeprom.SCAN_RESUME_MODE=1;gScanStateDir=1;gCurrentFunction=FUNCTION_FOREGROUND;
 gEeprom.VfoInfo[owner].CHANNEL_SAVE=memory?20:1024;
 gEeprom.VfoInfo[!owner].CHANNEL_SAVE=9;
 gEeprom.ScreenChannel[!owner]=9;gEeprom.MrChannel[!owner]=9;
 gNextMrChannel=memory?20:1024;initialFrqOrChan=20;lastFoundFrqOrChan=21;
 gRxVfo=&gEeprom.VfoInfo[owner];gTxVfo=gRxVfo;gCurrentVfo=gRxVfo;
 gScanKeepResult=false;gScanPauseMode=false;gCurrentCodeType=0;
 gFlagReconfigureVfos=false;gRequestSaveSettings=0;gVfoConfigureMode=2;
 tunes=steps=groupSyncs=0;savedVfo=99;
}
int main(void) {
 for(unsigned owner=0;owner<2;owner++) for(unsigned memory=0;memory<2;memory++) {
  begin(owner,memory);
  COMMON_SwitchVFOs();
  assert(gEeprom.TX_VFO==!owner && gEeprom.RX_VFO==owner);
  assert(gTxVfo==&gEeprom.VfoInfo[!owner] && gScanStateDir==1);
  assert(!tunes && !groupSyncs && !gFlagReconfigureVfos && !gRequestSaveSettings);
  assert(gVfoConfigureMode==VFO_CONFIGURE_NONE);
  CHFRSCANNER_ContinueScanning();
  assert(CHFRSCANNER_IsWatchingOther() && gEeprom.RX_VFO==!owner && !steps);
  assert(gScanPauseDelayIn_10ms==20);
  /* First audio on the fixed side holds RX; selection cannot interrupt it. */
  gCurrentFunction=FUNCTION_INCOMING;
  CHFRSCANNER_ContinueScanning();
  assert(gCurrentFunction==FUNCTION_RECEIVE && !gScanKeepResult && lastFoundFrqOrChan==21);
  unsigned before=tunes;COMMON_SwitchVFOs();
  assert(tunes==before && gCurrentFunction==FUNCTION_RECEIVE && gEeprom.RX_VFO==!owner);
  CHFRSCANNER_ContinueScanning();assert(!steps && CHFRSCANNER_IsWatchingOther());
  /* Receiver end-of-audio schedules a resume; cursor stays on the owner. */
  gCurrentFunction=FUNCTION_FOREGROUND;CHFRSCANNER_ContinueScanning();
  assert(!CHFRSCANNER_IsWatchingOther() && gEeprom.RX_VFO==owner && steps==1);
  assert(gEeprom.ScreenChannel[!owner]==9);
  /* A scanner hit is recorded; stopping while probing must save to owner. */
  CHFRSCANNER_Found();assert(gScanKeepResult);
  gCurrentFunction=FUNCTION_FOREGROUND;CHFRSCANNER_ContinueScanning();
  assert(CHFRSCANNER_IsWatchingOther());
  COMMON_SwitchVFOs();CHFRSCANNER_Stop();
  assert(!gScanStateDir && !CHFRSCANNER_IsWatchingOther());
  assert(gEeprom.ScreenChannel[!owner]==9 && gEeprom.RX_VFO==gEeprom.TX_VFO);
  if(memory) assert(savedVfo==owner);
  /* Squelch with a mismatched tone is not enough to open fixed-VFO audio. */
  begin(owner,memory);CHFRSCANNER_ContinueScanning();gCurrentFunction=FUNCTION_INCOMING;gCurrentCodeType=1;
  CHFRSCANNER_ContinueScanning();assert(steps==1 && gCurrentFunction!=FUNCTION_RECEIVE);
  /* Single watch retains ordinary scan stepping. */
  begin(owner,memory);gEeprom.DUAL_WATCH=0;CHFRSCANNER_ContinueScanning();
  assert(steps==1 && !CHFRSCANNER_IsWatchingOther());
  /* Off keeps dual display but removes all fixed-channel dwell overhead. */
  begin(owner,memory);gClearUIScanWatch=false;COMMON_SwitchVFOs();
  CHFRSCANNER_ContinueScanning();
  assert(steps==1 && !CHFRSCANNER_IsWatchingOther() && gEeprom.RX_VFO==owner);
  /* Disable during a probe: return to owner, then remain on normal scan. */
  begin(owner,memory);CHFRSCANNER_ContinueScanning();gClearUIScanWatch=false;
  CHFRSCANNER_ContinueScanning();CHFRSCANNER_ContinueScanning();
  assert(steps==2 && !CHFRSCANNER_IsWatchingOther());
 }
 puts("Scan/watch: A/B ownership, fixed-channel hold, scan resume, tone rejection and stop isolation passed.");
}
'''
    with tempfile.TemporaryDirectory(prefix='clearui-scan-watch-') as tmp:
        src = Path(tmp) / 'test.c'
        src.write_text(source)
        exe = Path(tmp) / 'test'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', str(src), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
