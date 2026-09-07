# ClearUI Instrument bitmap family

C5 uses original pixel artwork in `radio-sans.txt`, under Apache-2.0. It aims
for utilitarian instrument-panel legibility; it does not reproduce a specific
military font or claim compliance with a military display standard.

Large capitals are 11 pixels high, with an eight-pixel lowercase x-height and
three dedicated descender rows. All strokes are drawn directly on the pixel
grid, without bitmap stretching, outline rasterization, or antialiasing.
The zero has a center dot, capital I has crossbars, 1 has a flag and foot, and
lowercase l has a curved foot. Numbers have a stable nine-pixel advance;
letters and punctuation have proportional spacing. C5 adds a one-pixel
rightward stroke to the C4 master in both radio font sizes, leaving one
blank column and keeping the same character advances. Menu text stays regular.
Memory names and single/dual VFO frequencies use the same generated tables.

The compact radio face derives from the original seven-pixel ClearUI menu
artwork in `App/ui/clearui_text.c`, with an eighth row for true descenders.
Both sizes include all 95 printable ASCII characters. The compact face keeps
its seven-pixel pitch so existing metadata/layout geometry does not move.

The old `radio-source-14b.bdf` and `radio-source-12n.bdf` files are retained as
historical C2/C3 sources, but are no longer inputs to the generator. They are
unmodified Terminus Font 4.49.1 sources, under the OFL license and original
copyright notice in `LICENSES/Radio-SIL-OFL-1.1.txt`. Upstream Fusion font
tables and their licensing are unchanged.

To regenerate or verify the committed C tables, from the firmware directory:

```sh
python3 tools/build_clearui_font.py
python3 tools/build_clearui_font.py --check
python3 tools/test_clearui_display.py
```
