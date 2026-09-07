#!/usr/bin/env python3
"""Dependency-free CHIRP source checks; no serial operations or private fixtures."""
from pathlib import Path
import ast
import hashlib
from build_clearui_driver import build

ROOT = Path(__file__).resolve().parents[1]

def main():
    upstream = ROOT / 'chirp/upstream/f4hwn.fusion.chirp.v5.9.0.py'
    assert hashlib.sha256(upstream.read_bytes()).hexdigest() == (
        '09d23891a6dc44478cb3e8fd16e1f00fdf33673b4e2faffae765ad812b3a0ff2')
    driver = ROOT / 'chirp/fusion-clearui-chirp-c8.py'
    source = driver.read_text()
    assert source == build(upstream, meter_styles=True, battery_styles=True)
    tree = ast.parse(source, filename=driver.name)
    constants = {}
    for item in tree.body:
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
            try:
                constants[item.targets[0].id] = ast.literal_eval(item.value)
            except (ValueError, TypeError):
                pass
    assert constants['MEM_SIZE'] == 0xD200
    assert constants['BAT_TXT_LIST'] == ['Icon', 'Voltage', 'Percentage', 'Icon + percentage']
    assert constants['WELCOME_LIST'][4] == 'ClearUI logo (C5)'
    assert constants['FIRMWARE_VERSION_UPDATE'] == 'https://github.com/killcity/clearui/releases'
    assert 'GNU General Public License' in source
    assert 'clearui_rx_only' in source and 'Receive-only channels require ClearUI C5' in source
    print('CHIRP source: pinned upstream, reproducible generation, syntax, labels and ABI checks passed.')

if __name__ == '__main__':
    main()
