#!/usr/bin/env python3
"""Render repo gallery cards from production C UI harnesses, not AI artwork.

Requires Pillow 11+ in addition to the build/host-test dependencies.
Menu backgrounds and channel/RSSI/waterfall data are synthetic examples.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'images'

def font(size):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)

def sheet(directory, filename, heading, subheading, cards):
    canvas = Image.new('RGB', (1536, 1680), '#10151e')
    draw = ImageDraw.Draw(canvas)
    draw.text((64, 40), 'ClearUI', font=font(52), fill='#f6f8fb')
    draw.text((65, 106), heading, font=font(27), fill='#70d9c4')
    draw.text((65, 151), subheading, font=font(20), fill='#aeb8c8')
    for index, (source, title, caption) in enumerate(cards):
        x, y = 64 + (index % 2) * 720, 224 + (index // 2) * 460
        draw.rounded_rectangle((x, y, x+688, y+424), radius=18, fill='#1b2431')
        draw.text((x+24, y+18), title, font=font(25), fill='#ffffff')
        screen = Image.open(directory / source).convert('RGB')
        assert screen.size == (128, 64)
        # Integer nearest-neighbor scaling preserves every original LCD pixel.
        canvas.paste(screen.resize((640, 320), Image.Resampling.NEAREST), (x+24, y+64))
        draw.text((x+24, y+397), caption, font=font(16), fill='#aeb8c8')
    draw.text((64, 1632), '128 x 64 UI renders | Example data | Experimental UV-K1 firmware',
              font=font(20), fill='#aeb8c8')
    canvas.save(OUT / filename)

def main():
    with tempfile.TemporaryDirectory(prefix='clearui-gallery-') as temp:
        directory = Path(temp)
        subprocess.run([sys.executable, str(ROOT / 'tools/test_clearui_display.py'),
                        '--output-dir', temp], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / 'tools/test_clearui_menus.py'),
                        str(directory / 'menu')], cwd=ROOT, check=True)
        sheet(directory, 'clearui-gallery.png', 'A simpler way to use your UV-K1',
              'The actual UI drawing code, with synthetic channel and signal data.', [
            ('spine-0-dual.pgm', 'Dual VFO', 'The active pane gets more room.'),
            ('spine-0-single.pgm', 'Single VFO', 'Name first. Frequency below. Compact status.'),
            ('menu.icons.pgm', 'Main menu', 'Six categories, with icon-based navigation.'),
            ('menu.groups.pgm', 'Named groups', 'Browse and scan the group you choose.'),
            ('menu.mode.pgm', 'Readable choices', 'Lists instead of cryptic one-value screens.'),
            ('menu.scope-quick.pgm', 'Waterfall controls', 'Contextual options over sample history.'),
        ])
        sheet(directory, 'clearui-vfo-gallery.png', 'Your display, your preference',
              'Fixed A/B order. Active-pane emphasis. Two signal-meter styles.', [
            ('spine-0-dual.pgm', 'A active', 'Vertical Spine meter: the fresh-settings default.'),
            ('spine-1-dual.pgm', 'B active', 'Same A/B order, different emphasis.'),
            ('spine-0-single.pgm', 'Single memory', 'A focused name-and-frequency layout.'),
            ('single-frequency.pgm', 'Single frequency', 'The frequency takes priority in VFO mode.'),
            ('ribbon-0-dual.pgm', 'Horizontal alternative', 'Ribbon remains available as a saved preference.'),
            ('ribbon-0-single.pgm', 'Ribbon, single VFO', 'One radio, a choice of presentation.'),
        ])
        for source, output in [('spine-0-dual.pgm', 'clearui-dual.png'),
                               ('spine-0-single.pgm', 'clearui-single.png'),
                               ('menu.icons.pgm', 'clearui-menu.png'),
                               ('menu.groups.pgm', 'clearui-groups.png')]:
            Image.open(directory / source).resize((1024, 512), Image.Resampling.NEAREST).save(OUT / output)
    print('Gallery images saved under images/. All data is synthetic; no radio accessed.')

if __name__ == '__main__':
    main()
