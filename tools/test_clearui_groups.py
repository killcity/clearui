#!/usr/bin/env python3
"""Run production group navigation/storage logic with bounded flash stubs."""
from pathlib import Path
import subprocess
import tempfile
from test_clearui_algorithms import function

ROOT = Path(__file__).resolve().parents[1]
PREAMBLE = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "settings.h"
#include "misc.h"
#define DRIVER_GPIO_H /* No physical audio path is exercised by these tests. */
#include "audio.h"
#include "app/clearui.h"
#include "app/chFrScanner.h"
#include "ui/ui.h"
EEPROM_Config_t gEeprom;
bool gRequestSaveSettings, gRequestSaveVFO, gUpdateDisplay;
uint8_t gVfoConfigureMode;
int8_t gScanStateDir;
GUI_DisplayType_t gRequestDisplayScreen;
BEEP_Type_t gBeepToPlay;
static ChannelAttributes_t attributes[MR_CHANNELS_MAX];
static uint8_t flash[512];
static unsigned writes;
static char toast[32];
uint16_t gNextMrChannel;
volatile uint16_t gScanPauseDelayIn_10ms;
static unsigned stops, tunes;
ChannelAttributes_t *MR_GetChannelAttributes(uint16_t channel) {
    assert(channel < MR_CHANNELS_MAX);
    return &attributes[channel];
}
void PY25Q16_ReadBuffer(uint32_t address, void *buffer, uint32_t size) {
    assert(address == 0x121A0 && size == 8);
    memcpy(buffer, flash + 0x1A0, size);
}
void PY25Q16_WriteBuffer(uint32_t address, const void *buffer, uint32_t size, bool append) {
    assert(address == 0x121A0 && size == 8 && !append);
    memcpy(flash + 0x1A0, buffer, size);
    writes++;
}
void UI_CLEARUI_ShowToast(const char *text) { strcpy(toast, text); }
void CHFRSCANNER_Stop(void) { stops++; gScanStateDir=SCAN_OFF; }
void RADIO_ConfigureChannel(unsigned int vfo, unsigned int configure) {
    (void)vfo; (void)configure;
    assert(CLEARUI_ChannelInGroup(gNextMrChannel,gEeprom.SCAN_LIST_DEFAULT));
    assert(!attributes[gNextMrChannel].exclude && !attributes[gNextMrChannel].unused_2);
    tunes++;
}
void RADIO_SetupRegisters(bool switchToFunctionForeground) { (void)switchToFunctionForeground; }
enum { SCAN_NEXT_CHAN_SCANLIST1, SCAN_NEXT_CHAN_SCANLIST2,
       SCAN_NEXT_CHAN_DUAL_WATCH, SCAN_NEXT_CHAN_MR, SCAN_NEXT_NUM };
static unsigned currentScanList;
#ifdef ENABLE_FEAT_F4HWN_SCAN_FASTER
static bool scanFastLastFullTuneCandidate;
static void ScanFastResetState(void) {}
static bool ScanFastEnabled(void) { return true; }
static bool MemChannelFastPrecheck(uint16_t channel) {
    assert(CLEARUI_ChannelInGroup(channel,gEeprom.SCAN_LIST_DEFAULT));
    return true;
}
static void SetMemScanProgressChannel(uint16_t channel) {
    gEeprom.ScreenChannel[gEeprom.RX_VFO]=channel;
    gEeprom.MrChannel[gEeprom.RX_VFO]=channel;
}
static void AdvanceMemScanList(bool enabled) {
    if(enabled && ++currentScanList>=SCAN_NEXT_NUM) currentScanList=SCAN_NEXT_CHAN_SCANLIST1;
}
#endif
'''
TESTS = r'''
static void reboot(void) {
    loaded = false;
    groups[0] = groups[1] = MR_CHANNELS_LIST + 1;
}
static void channel(unsigned n, unsigned group) {
    attributes[n].band = BAND3_137MHz;
    attributes[n].scanlist = group;
}
int main(void) {
    memset(flash, 0xff, sizeof(flash));
    for (unsigned i = 0; i < MR_CHANNELS_MAX; i++) attributes[i].band = 7;
    assert(CLEARUI_GetGroup(0) == 25 && CLEARUI_GetGroup(1) == 25);
    channel(0,1); channel(255,2); channel(256,1); channel(1023,1);
    channel(900,0); // No list assignment: still accessible through All channels.
    attributes[256].unused_2 = 1;
    attributes[1023].exclude = 1;
    assert(CLEARUI_ChannelInGroup(256,1));
    assert(!RADIO_CheckValidChannel(256,true,1));
    assert(CLEARUI_ChannelInGroup(1023,1));
    assert(!RADIO_CheckValidChannel(1023,true,1));
    assert(!CLEARUI_ChannelInGroup(255,1));
    assert(CLEARUI_ChannelInGroup(900,25));
    assert(RADIO_CheckValidChannel(900,true,25));
    assert(!CLEARUI_ChannelInGroup(1024,25));
    assert(!RADIO_CheckValidChannel(65535,true,1));
    assert(CLEARUI_FindGroupChannel(1,1,1)==256);
    assert(CLEARUI_FindGroupChannel(257,1,1)==1023);
    assert(CLEARUI_FindGroupChannel(1024,1,1)==0);
    assert(CLEARUI_FindGroupChannel(65535,-1,1)==1023);
    assert(CLEARUI_FindGroupChannel(255,-1,1)==0);
    assert(CLEARUI_FindGroupChannel(0,1,24)==65535);
    assert(!CLEARUI_ChannelInGroup(0,0) && !CLEARUI_ChannelInGroup(0,26));

    gEeprom.ScreenChannel[0] = 255;
    assert(CLEARUI_SelectGroup(1));
    assert(gEeprom.ScreenChannel[0] == 256 && gRequestSaveVFO);
    assert(gVfoConfigureMode == VFO_CONFIGURE_RELOAD);
    assert(gEeprom.SCAN_LIST_DEFAULT == 1 && writes == 1);
    assert(CLEARUI_GetGroup(1) == 25);
    assert(CLEARUI_SelectGroup(1) && writes == 1); // No flash wear on reselect.
    assert(!CLEARUI_SelectGroup(24));
    assert(!strcmp(toast,"Group is empty"));
    assert(CLEARUI_GetGroup(0) == 1 && gEeprom.ScreenChannel[0] == 256);
    gEeprom.TX_VFO = 1; gEeprom.ScreenChannel[1] = 0;
    assert(CLEARUI_SelectGroup(2));
    assert(gEeprom.ScreenChannel[1] == 255 && CLEARUI_GetGroup(0) == 1);
    assert(writes == 2);
    for (unsigned i = 0; i < sizeof(flash); i++)
        if (i < 0x1A0 || i >= 0x1A8) assert(flash[i] == 0xff);
    reboot();
    assert(CLEARUI_GetGroup(0)==1 && CLEARUI_GetGroup(1)==2);
    gEeprom.TX_VFO = 0; CLEARUI_SyncGroup(); assert(gEeprom.SCAN_LIST_DEFAULT==1);
    gEeprom.TX_VFO = 1; CLEARUI_SyncGroup(); assert(gEeprom.SCAN_LIST_DEFAULT==2);
    flash[0x1A6] ^= 1; reboot();
    assert(CLEARUI_GetGroup(0)==25 && CLEARUI_GetGroup(1)==2);
    flash[0x1A3] = 255; reboot();
    assert(CLEARUI_GetGroup(0)==25 && CLEARUI_GetGroup(1)==25);

    // Scan filtering and shared membership use exactly the same group IDs.
    assert(RADIO_CheckValidList(1) && RADIO_CheckValidList(2));
    attributes[0].unused_2 = 1;
    assert(!RADIO_CheckValidList(1)); // Members exist, but all are skipped.
    assert(CLEARUI_FindGroupChannel(0,1,1) == 0);
    channel(777,25); // Fusion shared/All member is available in every group.
    assert(CLEARUI_ChannelInGroup(777,1) && CLEARUI_ChannelInGroup(777,24));
    assert(RADIO_CheckValidList(24));
    assert(RADIO_CheckValidChannel(777,true,24));
    attributes[777].unused_2 = 1;
    assert(!RADIO_CheckValidList(24));
    // Priority slots outside the group cannot be selected by the scanner.
    gEeprom.SCAN_LIST_ENABLED = true;
    gEeprom.SCANLIST_PRIORITY_CH[0] = 255;
    assert(!CLEARUI_ChannelInGroup(255,1));
    assert(!RADIO_CheckValidChannel(255,true,1));
    // Per-VFO choices can be changed during a scan without a queued retune.
    gScanStateDir=1; gRequestSaveVFO=false;
    gEeprom.ScreenChannel[1]=0;
    assert(CLEARUI_SelectGroup(2));
    assert(gEeprom.ScreenChannel[1]==0 && !gRequestSaveVFO);
    // Exercise the actual scan advancement, including priority-only groups.
    for (unsigned i=0;i<MR_CHANNELS_MAX;i++) { attributes[i].__val=0; attributes[i].band=7; }
    channel(10,1); channel(20,1); channel(255,2);
    gEeprom.SCAN_LIST_DEFAULT=1; gEeprom.SCAN_LIST_ENABLED=true;
    gEeprom.SCANLIST_PRIORITY_CH[0]=255; gEeprom.SCANLIST_PRIORITY_CH[1]=10;
    currentScanList=SCAN_NEXT_CHAN_SCANLIST1; gNextMrChannel=10; gScanStateDir=1;
    for(unsigned i=0;i<40;i++) {
        NextMemChannel();
        assert(gNextMrChannel==10 || gNextMrChannel==20);
        assert(stops==0);
    }
    assert(tunes>0);
    attributes[20].unused_2=1;
    for(unsigned i=0;i<12;i++) { NextMemChannel(); assert(gNextMrChannel==10); }
    attributes[10].exclude=1;
    NextMemChannel();
    assert(stops==1 && gScanStateDir==SCAN_OFF);
    assert(!strcmp(toast,"Nothing to scan"));
    puts("Groups passed: membership, bidirectional wrap, 1024 channels, skips, empty groups, independent A/B persistence, bounded writes and corrupt records.");
}
'''

def main():
    source = PREAMBLE
    for name in ('RADIO_CheckValidChannel','RADIO_CheckValidList','RADIO_FindNextChannel'):
        source += function('App/radio.c',name)
    source += '\n#include "app/clearui_groups.c"\n'
    source += function('App/app/chFrScanner.c','NextMemChannel')
    source += TESTS
    with tempfile.TemporaryDirectory(prefix='clearui-groups-') as tmp:
        path, binary = Path(tmp)/'test.c', Path(tmp)/'test'
        path.write_text(source)
        for extra in ([], ['-DENABLE_FEAT_F4HWN_SCAN_FASTER']):
            # The upstream range macro retains a >= 0 check for signed callers.
            # GCC warns when these tests pass uint16_t; keep that warning visible
            # without treating this harmless specialization as a build failure.
            subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-error=type-limits',
                        '-DENABLE_CLEAR_UI','-DENABLE_FEAT_F4HWN','-DENABLE_FASTER_CHANNEL_SCAN',
                        '-fsanitize=address,undefined','-I',str(ROOT/'App'),
                        *extra,str(path),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)

if __name__ == '__main__':
    main()
