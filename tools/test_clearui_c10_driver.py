#!/usr/bin/env python3
"""C10 driver handshake/upload and offline migration tests; synthetic data only."""
import ast
import base64
import json
import re
from pathlib import Path
from types import SimpleNamespace
from build_clearui_driver import build
from migrate_clearui_multiboot import MAGIC, SIZE, OLD_MODEL, NEW_MODEL, migrate

ROOT = Path(__file__).resolve().parents[1]


def image(model, fill):
    metadata = {'vendor': 'Quansheng', 'model': model, 'variant': '', 'rclass': 'UVK5RadioEgzumer'}
    return bytes([fill])*SIZE + MAGIC + base64.b64encode(json.dumps(metadata).encode())


def main():
    text = (ROOT/'chirp/clearui-multiboot-c10.py').read_text()
    assert text == build(ROOT/'chirp/upstream/f4hwn.chirp.v6.0.0.py', True, True, True)
    tree = ast.parse(text)
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    assert constants['MEM_SIZE'] == SIZE
    assert len(constants['KEYACTIONS_LIST']) == 24
    ids = dict(re.findall(r'(ACTION_OPT_\w+)\s*=\s*(\d+)', (ROOT/'App/settings.h').read_text()))
    for name, label in [('FM', 'FM RADIO'), ('PTT', 'PTT'), ('RXTX_LOG', 'RF LOG'), ('BEAM', 'BEAM'), ('BEACON', 'BEACON')]:
        assert constants['KEYACTIONS_LIST'][int(ids['ACTION_OPT_'+name])] == label
    assert constants['SET_MET_LIST'] == ['Spine', 'Ribbon']
    class RadioError(Exception):
        pass
    writes, resets = [], []
    env = dict(constants, errors=SimpleNamespace(RadioError=RadioError),
               chirp_common=SimpleNamespace(Status=SimpleNamespace),
               _writemem=lambda pipe, data, address: writes.append((address, bytes(data))),
               _resetradio=lambda pipe: resets.append(True))
    functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                               and n.name in ('do_download', 'do_upload')], type_ignores=[])
    exec(compile(functions, '<C10 driver>', 'exec'), env)
    radio = SimpleNamespace(pipe=SimpleNamespace(), status_fn=lambda status: None,
                            upload_calibration=False, get_mmap=lambda: bytes(SIZE))
    for wrong in ('ClearUI C5', 'ClearUI C1', 'F4HWN v6.0.0'):
        env['_sayhello'] = lambda pipe, value=wrong: value
        for operation in ('do_upload', 'do_download'):
            try:
                env[operation](radio)
                raise AssertionError('wrong firmware accepted')
            except RadioError:
                pass
    assert not writes and not resets
    env['_sayhello'] = lambda pipe: 'ClearUI C10'
    assert env['do_upload'](radio)
    touched = set()
    for address, data in writes:
        touched.update(range(address, address+len(data)))
    assert touched == set(range(constants['PROG_SIZE'])) | set(range(0xD000, 0xD200))
    assert not (set(range(0xB000, 0xD000)) & touched) # no calibration or logo
    assert len(resets) == 1
    old = bytearray(image(OLD_MODEL, 0x11))
    fresh = image(NEW_MODEL, 0x22)
    old[15] = 0xA5  # receive-only marker
    old[0x8000] = 0xC1  # temporary exclude + permanent skip + group metadata
    old[0xD000:0xD004] = b'CUI\x01'
    old[0xD004:0xD015] = b'Long group name\0\0'
    result = migrate(bytes(old), fresh)
    assert result[:0x8000] == old[:0x8000] and result[15] == 0xA5
    assert result[0x8000] == 0x41  # permanent skip preserved, temporary cleared
    assert result[0xD000:SIZE] == old[0xD000:SIZE]
    assert result[0x886E:0xD000] == fresh[0x886E:0xD000] # settings, VFO, cal, logo
    assert result[SIZE:] == fresh[SIZE:]
    for source, target in [(fresh, fresh), (bytes(old), bytes(old)), (b'bad', fresh)]:
        try:
            migrate(source, target)
            raise AssertionError('invalid migration accepted')
        except ValueError:
            pass
    print('C10 driver: pinned generation, v6 action IDs, wrong-driver rejection, bounded upload and safe memory/group migration passed.')


if __name__ == '__main__':
    main()
