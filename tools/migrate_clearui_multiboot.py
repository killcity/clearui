#!/usr/bin/env python3
"""Copy legacy ClearUI memories/groups into a fresh C10 CHIRP image, offline.

Requires a C8/C9 ClearUI .img and a freshly downloaded C10 .img template.
Does not copy global settings, action IDs, VFO state, calibration or logo.
CHIRP trailer format: chirp/chirp_common.py, CloneModeRadio (kk7ds/chirp).
"""
import argparse
import base64
import json
from pathlib import Path

MAGIC = b'\x00\xffchirp\xeeimg\x00\x01'
SIZE = 0xD200
OLD_MODEL = 'UV-K1 & UV-K5 V3 (Fusion ClearUI)'
NEW_MODEL = 'UV-K1 & UV-K5 V3 (ClearUI Multiboot C10)'


def unpack(data, model):
    if len(data) <= SIZE or data[SIZE:SIZE + len(MAGIC)] != MAGIC:
        raise ValueError('Expected a complete ClearUI CHIRP .img with metadata')
    metadata = json.loads(base64.b64decode(data[SIZE + len(MAGIC):], validate=True))
    if metadata.get('vendor') != 'Quansheng' or metadata.get('model') != model:
        raise ValueError(f'Wrong image model; expected {model}')
    return bytearray(data[:SIZE]), data[SIZE:]


def migrate(source, template):
    old, _ = unpack(source, OLD_MODEL)
    new, trailer = unpack(template, NEW_MODEL)
    # Memory records preserve frequency, offset, tone, power and RX-only byte.
    new[:0x8000] = old[:0x8000]
    new[0x8000:0x8800] = old[0x8000:0x8800]
    for address in range(0x8000, 0x8800, 2):
        if new[address:address + 2] != b'\xff\xff':
            new[address] &= 0x7F  # clear only the temporary scan exclusion
    new[0x880E:0x886E] = old[0x880E:0x886E]
    if old[0xD000:0xD004] == b'CUI\x01':
        new[0xD000:0xD200] = old[0xD000:0xD200]
    else:
        aliases = bytearray(b'CUI\x01')
        for index in range(24):
            name = old[0x880E + index * 4:0x8812 + index * 4]
            name = name.split(b'\0')[0].split(b'\xff')[0][:3]
            aliases.extend(bytes(c for c in name if 32 <= c <= 126).ljust(17, b'\0'))
        new[0xD000:0xD200] = aliases.ljust(512, b'\0')
    return bytes(new) + trailer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('legacy', type=Path)
    parser.add_argument('fresh_c10', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = migrate(args.legacy.read_bytes(), args.fresh_c10.read_bytes())
    # Never overwrite either input, an existing backup or an earlier result.
    with args.output.open('xb') as out:
        out.write(result)
    print(f'Created {args.output}: memories/groups migrated; template settings and calibration preserved.')


if __name__ == '__main__':
    main()
