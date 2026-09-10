#!/usr/bin/env python3
"""Run portable host checks after configuring/building the ClearUI preset."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ['build_clearui_font.py', '--check'],
    ['test_clearui_driver.py'],
    ['test_clearui_c10_driver.py'],
    ['test_clearui_multiboot.py'],
    ['test_clearui_groups.py'],
    ['test_clearui_algorithms.py'],
    ['test_clearui_storage.py'],
    ['test_clearui_receive_only.py'],
    ['test_clearui_menus.py'],
    ['test_clearui_scope.py'],
    ['test_clearui_hf.py'],
    ['test_clearui_key_holds.py'],
    ['test_clearui_display.py'],
]

def main():
    if not (ROOT / 'build/ClearUI/build.ninja').is_file():
        raise SystemExit('First run: cmake --preset ClearUI && cmake --build --preset ClearUI')
    for script, *arguments in CHECKS:
        print(f'Running {script}', flush=True)
        subprocess.run([sys.executable, str(ROOT / 'tools' / script), *arguments],
                       cwd=ROOT, check=True)
    print('All ClearUI host checks passed; no radio accessed.')

if __name__ == '__main__':
    main()
