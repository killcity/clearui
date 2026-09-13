#!/usr/bin/env python3
"""Render release GIFs from real firmware host-test framebuffer snapshots.

Requires Pillow. Usage: python3 tools/render_clearui_animations.py OUTPUT_DIR
"""
import pathlib
import subprocess
import sys
import tempfile
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="clearui-animation-") as temporary:
    subprocess.run([sys.executable, str(ROOT / "tools/test_clearui_display.py"),
                    "--output-dir", temporary], cwd=ROOT, check=True)
    for mode, name in ((3, "name-sweep"), (4, "marquee-chase"),
                       (5, "zipper-sweep"), (6, "liquid-lettering")):
        frames = []
        for phase in range(40):
            source = pathlib.Path(temporary) / f"animation-{mode}-selected-1-phase-{phase:02}.pgm"
            frame = Image.open(source).convert("L")
            frame = frame.point(lambda value: 1 if value < 128 else 0).convert("P")
            frame.putpalette([242, 242, 221, 41, 38, 56] + [0] * 762)
            frames.append(frame.resize((512, 256), Image.Resampling.NEAREST))
        duration = 40 if mode == 6 else 100
        target = out / f"{name}.gif"
        frames[0].save(target, save_all=True, append_images=frames[1:],
                       duration=duration, loop=0, optimize=False, disposal=2)
        with Image.open(target) as gif:
            elapsed = 0
            for index in range(gif.n_frames):
                gif.seek(index)
                elapsed += gif.info["duration"]
            assert elapsed == 40 * duration, (target, elapsed)
        print(target)
