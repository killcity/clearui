#!/usr/bin/env python3
"""Exercise actual TX gating and channel save/scan decode with host RF stubs."""
from pathlib import Path
import subprocess
import tempfile
from test_clearui_algorithms import function

ROOT=Path(__file__).resolve().parents[1]
PREAMBLE=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "settings.h"
#include "misc.h"
#include "functions.h"
#define BEEP_500HZ_60MS_DOUBLE_BEEP_OPTIONAL 1
EEPROM_Config_t gEeprom;
VFO_Info_t *gTxVfo, *gRxVfo, *gCurrentVfo;
FUNCTION_Type_t gCurrentFunction;
volatile bool gScheduleDualWatch, gTxTimeoutReached, gTxTimeoutReachedAlert;
volatile uint16_t gDualWatchCountdown_10ms, gTxTimerCountdown_500ms, gTxTimerCountdownAlert_500ms;
volatile uint8_t gSerialConfigCountDown_500ms;
const uint16_t dual_watch_count_after_tx_10ms=20;
bool gDualWatchActive, gRxVfoIsActive, gFlagEndTransmission;
uint8_t gUpdateStatus;
uint8_t gVfoConfigureMode, gBatteryDisplayLevel=3, gRTTECountdown_10ms;
static unsigned tx_started, gates, pa_off, gpio_off, beeps, freq_checks;
static VfoState_t state;
static uint8_t flash[0x9200];
const uint16_t gStepFrequencyTable[STEP_N_ELEM]={0};
const char* const gSubMenu_PTT_ID[5]={0};
int32_t TX_freq_check(uint32_t frequency) {(void)frequency; ++freq_checks; return 0;}
void FUNCTION_Select(FUNCTION_Type_t value) {assert(value==FUNCTION_TRANSMIT); ++tx_started;}
void RADIO_SetVfoState(VfoState_t value) {state=value; ++gates;}
void BK4819_SetupPowerAmplifier(uint8_t bias,uint32_t frequency) {assert(bias==0 && frequency==0); ++pa_off;}
void BK4819_ToggleGpioOut(BK4819_GPIO_PIN_t pin,bool value) {assert(pin==BK4819_GPIO1_PIN29_PA_ENABLE && !value); ++gpio_off;}
void AUDIO_PlayBeep(unsigned beep) {(void)beep; ++beeps;}
void PY25Q16_ReadBuffer(uint32_t address,void *data,uint32_t size) {assert(address+size<=sizeof(flash)); memcpy(data,flash+address,size);}
void PY25Q16_WriteBuffer(uint32_t address,const void *data,uint32_t size,bool append) {(void)append; assert(address+size<=sizeof(flash)); memcpy(flash+address,data,size);}
void SETTINGS_UpdateChannel(uint16_t c,const VFO_Info_t *v,bool keep) {(void)c;(void)v;(void)keep;}
void SETTINGS_SaveChannelName(uint16_t c,const char *n) {(void)c;(void)n;}
void RADIO_ValidateAndSetCode(FREQ_Config_t *f,uint8_t c) {f->Code=c;}
'''
TESTS=r'''
int main(void) {
    for(unsigned v=0;v<2;v++) {
        gEeprom.VfoInfo[v].pTX=&gEeprom.VfoInfo[v].freq_config_TX;
        gEeprom.VfoInfo[v].pRX=&gEeprom.VfoInfo[v].freq_config_RX;
        gEeprom.VfoInfo[v].freq_config_RX.Frequency=15680000;
        gEeprom.VfoInfo[v].freq_config_TX.Frequency=15680000;
    }
    for(unsigned active=0;active<2;active++)
    for(unsigned dual=0;dual<2;dual++)
    for(unsigned cross=0;cross<2;cross++)
    for(unsigned lock=0;lock<2;lock++) {
        gEeprom.RX_VFO=gEeprom.TX_VFO=active;
        gEeprom.DUAL_WATCH=dual ? DUAL_WATCH_CHAN_A : DUAL_WATCH_OFF;
        gEeprom.CROSS_BAND_RX_TX=cross ? CROSS_BAND_CHAN_A : CROSS_BAND_OFF;
        gTxVfo=gRxVfo=&gEeprom.VfoInfo[active];
        gRxVfoIsActive=false;
        gTxVfo->TX_LOCK=lock;
        gTxVfo->RECEIVE_ONLY=true;
        unsigned old=tx_started, checked=freq_checks;
        RADIO_PrepareTX();
        assert(tx_started==old && freq_checks==checked && state==VFO_STATE_TX_DISABLE);
        assert(pa_off && gpio_off && beeps);
        assert(RADIO_BlockReceiveOnly());
        gTxVfo->RECEIVE_ONLY=false;
        assert(!RADIO_BlockReceiveOnly());
        RADIO_PrepareTX();
        assert(tx_started==old+1);
    }
    VFO_Info_t v={.RECEIVE_ONLY=true,.OUTPUT_POWER=OUTPUT_POWER_LOW1};
    v.freq_config_RX.Frequency=15680000;
    for(unsigned a=0;a<2;a++) {
        SETTINGS_SaveChannel(FREQ_CHANNEL_FIRST,a,&v,2);
        assert(flash[0x9000+a*16+15]==CLEARUI_RECEIVE_ONLY_MARKER);
    }
    SETTINGS_SaveChannel(106,0,&v,2);
    assert(flash[106*16+15]==CLEARUI_RECEIVE_ONLY_MARKER);
    ChannelScanDisplayInfo_t info;
    assert(SETTINGS_FetchChannelScanDisplayInfo(106,&info) && info.receiveOnly);
    v.RECEIVE_ONLY=false;
    SETTINGS_SaveChannel(106,0,&v,2);
    assert(SETTINGS_FetchChannelScanDisplayInfo(106,&info) && !info.receiveOnly);
    flash[106*16+15]=0xff;
    assert(SETTINGS_FetchChannelScanDisplayInfo(106,&info) && !info.receiveOnly);
    puts("Receive-only: TX bypass/dual/crossband blocked; normal TX preserved; channel/VFO saves and fast-scan decode passed.");
}
'''

def main():
    setup=function('App/radio.c','RADIO_SetTxParameters')
    assert setup.index('RADIO_BlockReceiveOnly()')<setup.index('BK4819_FilterBandwidth_t')
    radio=(ROOT/'App/radio.c').read_text()
    assert 'pVfo->RECEIVE_ONLY = data[7] == CLEARUI_RECEIVE_ONLY_MARKER;' in radio
    scan=(ROOT/'App/app/chFrScanner.c').read_text()
    assert 'scanFastDisplayVfo.RECEIVE_ONLY = info.receiveOnly;' in scan
    routines=''.join(function(p,n) for p,n in [
        ('App/radio.c','RADIO_SelectCurrentVfo'),('App/radio.c','RADIO_BlockReceiveOnly'),
        ('App/radio.c','RADIO_PrepareTX'),('App/settings.c','SETTINGS_SaveChannel'),
        ('App/settings.c','SETTINGS_FetchChannelScanDisplayInfo')])
    with tempfile.TemporaryDirectory(prefix='clearui-rxonly-') as tmp:
        source=Path(tmp)/'test.c'; binary=Path(tmp)/'test'
        source.write_text(PREAMBLE+routines+TESTS)
        subprocess.run(['cc','-g','-fsanitize=address,undefined','-DENABLE_CLEAR_UI',
                        '-DENABLE_FEAT_F4HWN','-I',str(ROOT/'App'),
                        str(source),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)

if __name__=='__main__': main()
