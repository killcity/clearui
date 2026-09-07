#!/usr/bin/env python3
"""Apply audited ClearUI extensions to the official Fusion 5.9.0 GPL driver."""
from pathlib import Path
import argparse
import hashlib

def build(source, meter_styles=False, battery_styles=False):
    text=Path(source).read_text()
    def replace(old,new):
        nonlocal text
        if text.count(old)!=1:
            raise ValueError(f'Unexpected upstream driver: anchor count for {old[:70]!r}')
        text=text.replace(old,new)
    replace('DRIVER_VERSION = "Quansheng UV-K1 / UV-K5 V3 driver ver: 2026/08/14 (c) F4HWN v5.9.0"',
        'DRIVER_VERSION = "Fusion 5.9.0 ClearUI C5: named groups and receive-only (2026-09-05)"')
    replace('MEM_SIZE =      0x00B190    # size of all memory',
        '# ClearUI virtual D000..D200 maps to external flash 012000..012200.\n'
        'MEM_SIZE =      0x00D200\nCAL_END =       0x00B190\nALIAS_START =   0x00D000\nALIAS_END =     0x00D200')
    replace('} cal;','} cal;\n\n#seekto 0x00D000;\nstruct {\n  char magic[3];\n  u8 version;\n  struct { char name[17]; } list[24];\n} clearui;')
    replace('MODEL = "UV-K1 & UV-K5 V3 (F4HWN Fusion)"','MODEL = "UV-K1 & UV-K5 V3 (Fusion ClearUI)"\n    _memsize = MEM_SIZE')
    hello='    if f:\n        radio.FIRMWARE_VERSION = f'
    if text.count(hello)!=2:
        raise ValueError('Unexpected upstream handshake paths')
    text=text.replace(hello,
        '    if f:\n'
        '        if f not in ("ClearUI C1", "ClearUI C5"):\n'
        '            raise errors.RadioError("This driver requires ClearUI C1 or C5 firmware; detected " + f)\n'
        '        radio.FIRMWARE_VERSION = f')
    replace('    else:\n        return False\n\n    while True:',
        '    else:\n        return False\n\n'
        '    if f != "ClearUI C5":\n'
        '        raw = radio.get_mmap().get_packed()\n'
        '        addresses = list(range(0, 0x4000, 16)) + list(range(0x9000, 0x90E0, 16))\n'
        '        if any(raw[a+15] == 0xA5 and raw[a:a+4] not in (b"\\xff"*4, b"\\x00"*4) for a in addresses):\n'
        '            raise errors.RadioError("Receive-only channels require ClearUI C5 firmware; flash C5 before uploading this image")\n\n'
        '    while True:')
    replace('u8 __UNUSED03;', 'u8 clearui_rx_only;')
    replace('"Picture (LOGO)"', '"ClearUI logo (C5)"')
    replace('FIRMWARE_VERSION_UPDATE = "https://github.com/armel/uv-k1-k5v3-firmware-custom/releases"',
            'FIRMWARE_VERSION_UPDATE = "https://github.com/killcity/clearui/releases"')
    replace('CHIRP_DRIVER_VERSION_UPDATE = "https://github.com/armel/uv-k1-k5v3-firmware-custom/releases"',
            'CHIRP_DRIVER_VERSION_UPDATE = "https://github.com/killcity/clearui/releases"')
    replace('u8 __UNUSED07;', 'u8 clearui_rx_only;')
    replace('        # TXLock\n',
        '        val = RadioSettingValueBoolean(int(_mem.clearui_rx_only) == 0xA5)\n'
        '        rs = RadioSetting("receiveOnly", "Receive only (requires C5)", val)\n'
        '        rs.set_doc("Disables transmitting regardless of band unlock or TX Lock; requires ClearUI C5")\n'
        '        mem.extra.append(rs)\n\n'
        '        # TXLock\n')
    replace('            # actually the step and duplex are overwritten by chirp based on',
        '            mem.extra.append(RadioSetting("receiveOnly", "Receive only (requires C5)", RadioSettingValueBoolean(False)))\n\n'
        '            # actually the step and duplex are overwritten by chirp based on')
    replace('        _mem_chan.txLock = get_setting("txLock", 0)',
        '        _mem_chan.clearui_rx_only = 0xA5 if get_setting("receiveOnly", False) else 0\n'
        '        _mem_chan.txLock = get_setting("txLock", 0)')
    replace('stop_addr  = MEM_SIZE','stop_addr  = CAL_END')
    replace('        else:\n            break  # done',
        '        elif step == 1:\n            step += 1\n            continue\n'
        '        elif step == 2:\n'
        '            start_addr, stop_addr = ALIAS_START, ALIAS_END\n'
        '            status.max = stop_addr - start_addr\n'
        '            status.cur = 0\n'
        '            status.msg = "Uploading ClearUI list names"\n'
        '            radio.status_fn(status)\n'
        '        else:\n            break  # done')
    replace('        self._memobj = bitwise.parse(MEM_FORMAT, self._mmap)',
        '        if len(self._mmap) != MEM_SIZE:\n'
        '            raise errors.RadioError("Download a fresh image with the ClearUI driver first")\n'
        '        if self._mmap[ALIAS_START:ALIAS_START + 4] != b"CUI\\x01":\n'
        '            aliases = b"CUI\\x01"\n'
        '            for index in range(24):\n'
        '                raw = self._mmap[0x880E + index * 4:0x8812 + index * 4]\n'
        '                name = raw.split(b"\\x00")[0].split(b"\\xff")[0][:3]\n'
        '                name = bytes(c for c in name if 32 <= c <= 126)\n'
        '                aliases += name.ljust(17, b"\\x00")\n'
        '            self._mmap[ALIAS_START] = aliases\n'
        '        self._memobj = bitwise.parse(MEM_FORMAT, self._mmap)')
    replace('name_obj = self._memobj.listname[index].name','name_obj = self._memobj.clearui.list[index].name')
    start=text.index('                    val_str = str(element.value)  # Plus de strip()')
    end=text.index('\n            # Shortcuts',start)
    text=text[:start]+'''                    name = str(element.value).encode('ascii')[:16].rstrip(b' ')
                    _mem.clearui.list[idx].name = name.ljust(17, b'\\x00')
                    _mem.listname[idx].name = name[:3].ljust(4, b'\\x00')
'''+text[end:]
    start=text.index('            # Get the character array object from memory\n            name_obj = _mem.listname[i].name')
    end=text.index('            listname_setting = RadioSetting(',start)
    text=text[:start]+'''            listname = self._get_scanlist_name(i)
            val = RadioSettingValueString(0, 16, listname)
'''+text[end:]
    replace("f'Maximum 3 characters'","f'Maximum 16 ASCII characters; requires ClearUI firmware'")
    replace('tag = memory.name.ljust(10) + "\\x00"*6','tag = memory.name[:16].ljust(16, "\\x00")')
    replace('rf.valid_name_length = 10','rf.valid_name_length = 16')
    replace('CHANNELDISP_LIST = ["Frequency (FREQ)", "CHANNEL NUMBER", "NAME", "Name + Frequency (NAME + FREQ)"]',
        'CHANNELDISP_LIST = ["Frequency only", "Frequency large + name (C5)", "Name only", "Name large + frequency"]')
    replace('u8 __UNUSED04:3,\n     compander:2,','u8 temporary_exclude:1,\n     skip:1,\n     __UNUSED04:1,\n     compander:2,')
    replace('rf.valid_skips = [""]','rf.valid_skips = ["", "S"]')
    replace('            tmpscn = _mem3.scanlist','            tmpscn = _mem3.scanlist\n            mem.skip = "S" if _mem3.skip else ""')
    replace('        _mem_attr.compander = 0','        _mem_attr.compander = 0\n        _mem_attr.skip = memory.skip == "S"\n        _mem_attr.temporary_exclude = 0')
    if meter_styles:
        replace('Fusion 5.9.0 ClearUI C5: named groups and receive-only (2026-09-05)',
                'Fusion 5.9.0 ClearUI C5/C6: named groups, receive-only, C6 meters')
        replace('SET_MET_LIST = ["TINY", "CLASSIC"]',
                'SET_MET_LIST = ["Spine", "Ribbon"]\nSET_GUI_LIST = ["TINY", "CLASSIC"]')
        replace('tmpsetgui = list_def(_mem.set_gui, SET_MET_LIST, 0)\n        val = RadioSettingValueList(SET_MET_LIST, SET_MET_LIST[tmpsetgui])',
                'tmpsetgui = list_def(_mem.set_gui, SET_GUI_LIST, 0)\n        val = RadioSettingValueList(SET_GUI_LIST, SET_GUI_LIST[tmpsetgui])')
        replace('"S-Meter Display Style (SetMet)"', '"Meter style (C6: Spine / Ribbon)"')
        begin=text.index("        SetMetSetting.set_doc(")
        end=text.index('        # Set_gui f4hwn',begin)
        text=text[:begin]+"        SetMetSetting.set_doc('C6: Spine uses a vertical meter; Ribbon uses a horizontal strip. C5 retains its original meter.')\n"+text[end:]
    if battery_styles:
        replace('BAT_TXT_LIST = ["NONE", "VOLTAGE", "PERCENT"]',
                'BAT_TXT_LIST = ["Icon", "Voltage", "Percentage", "Icon + percentage"]')
        begin = text.index('        bat_txt_setting.set_doc(')
        end = text.index('        tmpback =', begin)
        text = text[:begin] + "        bat_txt_setting.set_doc('C8: Icon, Voltage, Percentage, or Icon + percentage. Earlier firmware may not display these choices correctly.')\n" + text[end:]
    # Keep all upstream copyright/license notices and distinguish modifications.
    return '# ClearUI modifications: named groups, bounded transfers, C5 receive-only channels.\n'+text

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--meter-styles', action='store_true', help='C6 UI labels; same C5 programming format')
    parser.add_argument('--battery-styles', action='store_true', help='C8 battery format choices')
    args=parser.parse_args()
    args.output.write_text(build(args.upstream, args.meter_styles, args.battery_styles))
    print(f'Upstream SHA256: {hashlib.sha256(args.upstream.read_bytes()).hexdigest()}')
    print(args.output)
