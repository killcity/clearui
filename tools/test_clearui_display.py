#!/usr/bin/env python3
"""Build the real display renderer with host hardware stubs and sanitizers."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--font-source', type=Path, help='Alternate generated C font for design comparison')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='clearui-display-') as tmp:
        output = args.output_dir or Path(tmp)
        output.mkdir(parents=True, exist_ok=True)
        binary = Path(tmp) / 'display-test'
        sources = ['tools/test_clearui_display.c', 'App/ui/helper.c',
                   'App/font.c', 'App/bitmaps.c',
                   'App/external/printf/printf.c']
        # macOS dead_strip / ELF gc-sections discard unrelated helper routines.
        import sys
        discard = '-Wl,-dead_strip' if sys.platform == 'darwin' else '-Wl,--gc-sections'
        subprocess.run(['cc', '-g', '-fsanitize=address,undefined',
            '-ffunction-sections', '-fdata-sections', discard,
            '-DENABLE_CLEAR_UI', '-DENABLE_FEAT_F4HWN', '-DENABLE_AUDIO_BAR',
            '-DENABLE_SMALL_BOLD', '-DENABLE_BIG_FREQ', '-I', str(ROOT / 'App'),
            *[str(ROOT / p) for p in sources],
            str(args.font_source.resolve() if args.font_source else ROOT / 'App/clearui_font.c'),
            '-o', str(binary)], check=True)
        subprocess.run([str(binary), str(output)], check=True)

if __name__ == '__main__':
    main()
