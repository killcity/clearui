#!/usr/bin/env python3
"""Run production bank/slot/state logic against simulated external flash."""
from pathlib import Path
import subprocess
import tempfile
from test_clearui_menus import function

ROOT = Path(__file__).resolve().parents[1]
PREAMBLE = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "driver/mb_flash.h"
#include "driver/py25q16.h"
static uint8_t flash[0x200000];
static uint32_t BankBase;
static uint8_t mb_spi_err;
static bool fail_read;
static unsigned erases, writes, invalidates;
#define MB_EXT_SECTOR 4096u
static void mb_spi_polled_mode(void) {}
void PY25Q16_InvalidateCache(void) {invalidates++;}
static void mb_ext_read(uint32_t a, uint8_t *b, uint32_t n) {
    assert(a+n<=sizeof(flash));
    if(fail_read) {mb_spi_err=1; return;} memcpy(b,flash+a,n);
}
static bool mb_ext_sector_erase(uint32_t a) {
    assert(a%4096==0 && a+4096<=sizeof(flash));
    memset(flash+a,255,4096); erases++; return true;
}
static bool mb_ext_program(uint32_t a,const uint8_t *b,uint32_t n) {
    assert(a+n<=sizeof(flash)); memcpy(flash+a,b,n); writes++; return true;
}
'''
TESTS = r'''
static void marker(uint32_t base,uint32_t generation,uint8_t slot,uint8_t bank) {
    mb_state_t s={.magic=MB_STATE_MAGIC,.generation=generation,.image_size=256,
        .firmware_slot=slot,.slot_inv=(uint8_t)~slot,.config_bank=bank,.bank_inv=(uint8_t)~bank};
    s.state_crc32=MB_Crc32Bytes((uint8_t*)&s,20); memcpy(flash+base,&s,sizeof(s));
}
int main(void) {
    memset(flash,255,sizeof(flash));
    assert(MB_Crc32Bytes((uint8_t*)"123456789",9)==0xCBF43926);
    for(unsigned bank=0;bank<5;bank++) {
        PY25Q16_SetBankBase(MB_BankBase(bank));
        uint8_t b[8]; memset(b,bank+1,8);
        EEPROM_WriteBuffer(0xD000,b,8); // actual logical-to-physical mapping
        assert(!memcmp(flash+MB_BankBase(bank)+0xD000,b,8));
        assert(BankMap(0x10000)==0x10000); // calibration shared, not remapped
        assert(BankMap(0x11000)==0x11000); // logo shared
        assert(BankMap(MB_STATE_A_BASE)==MB_STATE_A_BASE);
        assert(BankMap(MB_SLOT0_EXT_BASE)==MB_SLOT0_EXT_BASE);
    }
    for(unsigned bank=0;bank<5;bank++) {
        PY25Q16_SetBankBase(MB_BankBase(bank));
        uint8_t b[8]; EEPROM_ReadBuffer(0xD000,b,8);
        for(unsigned k=0;k<8;k++) assert(b[k]==bank+1);
    }
    unsigned old=erases;
    assert(MB_BankErase(0)==MB_ERR_SLOT && MB_BankErase(5)==MB_ERR_SLOT);
    assert(erases==old);
    assert(MB_BankErase(2)==MB_OK && invalidates==1);
    assert(flash[MB_BankBase(2)+0xD000]==255 && flash[MB_BankBase(1)+0xD000]==2);
    assert(flash[0x10000]==255 && flash[0x11000]==255);
    assert(MB_SlotErase(0)==MB_ERR_SLOT && MB_SlotErase(5)==MB_ERR_SLOT);
    uint8_t b[8]={0}; old=writes;
    assert(MB_SlotWrite(0,0,b,8)==MB_ERR_SLOT);
    assert(MB_SlotWrite(1,MB_SLOT_STRIDE-7,b,8)==MB_ERR_SIZE);
    assert(MB_SlotWrite(1,0xffffffff,b,8)==MB_ERR_SIZE && writes==old);
    mb_slot_header_t h={.magic=MB_SLOT_MAGIC,.hdr_version=1,.flags=MB_FLAG_COMMITTED,.image_size=256};
    uint32_t base=MB_SLOT0_EXT_BASE+MB_SLOT_STRIDE;
    h.image_crc32=MB_Crc32Bytes(flash+base+MB_SLOT_IMG_OFFSET,256);
    memcpy(flash+base,&h,sizeof(h));
    assert(MB_ValidateSlot(1,NULL,NULL)==MB_OK);
    flash[base+MB_SLOT_IMG_OFFSET]^=1;
    assert(MB_ValidateSlot(1,NULL,NULL)==MB_ERR_CRC);
    h.flags=0; memcpy(flash+base,&h,sizeof(h));
    assert(MB_ValidateSlot(1,NULL,NULL)==MB_ERR_NOT_COMMITTED);
    h.flags=1; h.image_size=MB_INT_APP_SIZE+1; memcpy(flash+base,&h,sizeof(h));
    assert(MB_ValidateSlot(1,NULL,NULL)==MB_ERR_SIZE);
    fail_read=true; assert(MB_ValidateSlot(1,NULL,NULL)==MB_ERR_SPI); fail_read=false;
    mb_state_t s;
    assert(MB_ReadActiveState(&s)==MB_MARK_MISSING);
    marker(MB_STATE_A_BASE,10,1,1); marker(MB_STATE_B_BASE,11,2,3);
    assert(MB_ReadActiveState(&s)==MB_MARK_VALID && s.firmware_slot==2 && s.config_bank==3);
    flash[MB_STATE_B_BASE+20]^=1; // torn newer record: recover older valid bank
    assert(MB_ReadActiveState(&s)==MB_MARK_VALID && s.config_bank==1);
    fail_read=true; assert(MB_ReadActiveState(&s)==MB_MARK_IO); fail_read=false;
    flash[MB_STATE_A_BASE+20]^=1; assert(MB_ReadActiveState(&s)==MB_MARK_CORRUPT);
    marker(MB_STATE_A_BASE,0xffffffff,1,1); marker(MB_STATE_B_BASE,0,2,2);
    assert(MB_ReadActiveState(&s)==MB_MARK_VALID && s.config_bank==2);
    puts("Multiboot: five isolated banks, shared-region protection, CRC rejection, slot bounds, redundant state recovery passed.");
}
'''


def main():
    source = PREAMBLE
    for name in ('MB_Crc32Bytes', 'MB_BankBase'):
        source += function('App/driver/mb_flash.c', name)
    source += function('App/driver/py25q16.c', 'PY25Q16_SetBankBase')
    source += function('App/driver/py25q16.c', 'BankMap')
    source += r'''
void PY25Q16_ReadBuffer(uint32_t a,void *b,uint32_t n) {mb_ext_read(BankMap(a),b,n);}
void PY25Q16_WriteBuffer(uint32_t a,const void *b,uint32_t n,bool append) {
    (void)append; mb_ext_program(BankMap(a),b,n);
}
#include "driver/eeprom_compat.c"
static uint32_t mb_ext_image_crc32(uint32_t a,uint32_t n) {return MB_Crc32Bytes(flash+a,n);}
'''
    for name in ('mb_read_header', 'mb_validate', 'MB_ValidateSlot', 'MB_SlotErase',
                 'MB_SlotWrite', 'MB_BankErase', 'mb_read_state_copy',
                 'mb_generation_newer', 'mb_read_active_state', 'MB_ReadActiveState'):
        source += function('App/driver/mb_flash.c', name)
    with tempfile.TemporaryDirectory(prefix='clearui-multiboot-') as tmp:
        path, binary = Path(tmp)/'test.c', Path(tmp)/'test'
        path.write_text(source + TESTS)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Werror', '-fsanitize=address,undefined',
                        '-DENABLE_CLEAR_UI', '-DENABLE_FEAT_F4HWN_MULTIBOOT',
                        '-I', str(ROOT/'App'), str(path), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    # Ensure both call paths and reset use banked storage; no shared-name writes.
    assert '#define CLEARUI_LIST_STORE_ADDRESS 0x00D000u' in (ROOT/'App/app/clearui.c').read_text()
    assert 'PY25Q16_SectorErase(0x00D000)' in (ROOT/'App/settings.c').read_text()
    startup = (ROOT/'App/main.c').read_text()
    assert startup.index('PY25Q16_SetBankBase') < startup.index('SETTINGS_InitEEPROM();')


if __name__ == '__main__':
    main()
