# ClearUI C10e — animated receive names

Four optional effects make the receiving memory name easier to spot, on a plain
background. Liquid lettering now runs a faster **1.6-second loop**.

The vertical **Spine** signal meter is the default for fresh/reset settings and
is shown in the previews below. Existing saved meter choices are preserved;
choose **Display → Meter style → Spine** to switch an existing configuration.

## Choose an effect

**Display → RX frame → Name sweep / Marquee chase / Zipper sweep / Liquid lettering**

Off, Light shade (50%) and Inverted remain available. These are alternative
highlight styles, not stacked effects. The receiving VFO is highlighted even
when the other VFO is selected. Fonts, pane sizes, meters and pill positions
are unchanged. Animations apply to visible memory names, not frequency-only
displays, and stop outside established receive/monitor audio.

### Name sweep

A moving emphasis across the lettering. Four-second loop.

![Name sweep](https://github.com/killcity/clearui/releases/download/clearui-c10e/name-sweep.gif)

### Marquee chase

Moving dashes around the name, avoiding existing text. Four-second loop.

![Marquee chase](https://github.com/killcity/clearui/releases/download/clearui-c10e/marquee-chase.gif)

### Zipper sweep

Two bands converge and separate across the lettering. Four-second loop.

![Zipper sweep](https://github.com/killcity/clearui/releases/download/clearui-c10e/zipper-sweep.gif)

### Liquid lettering

A faster one-pixel ripple through the letters. Forty-millisecond phase updates,
with a complete cycle every 1.6 seconds.

![Liquid lettering](https://github.com/killcity/clearui/releases/download/clearui-c10e/liquid-lettering.gif)

These GIFs use actual firmware framebuffer snapshots enlarged 4×, with illustrative
channels and signal values. They are not radio recordings; LCD response and radio
workload can affect the appearance and timing. Reproduce them with
`python3 tools/render_clearui_animations.py images/rx-animations` (Pillow required).

## Updating and compatibility

Download **clearui-c10e.zip** for firmware, exact committed source, the C10 CHIRP
driver, migration utility, animated previews, instructions, licenses and checksums.
The standalone firmware is **ClearUI-C10e-UV-K1.bin**.

Use the existing **clearui-multiboot-c10.py** driver. No driver update, reset or
memory conversion is required. The effect selection persists in the active
configuration bank; fresh settings default Off. Keep ClearUI and Fusion in
separate configuration banks. Calibration and the startup logo remain shared.

Back up settings and calibration before updating the ClearUI user slot through
UV Studio's multiboot workflow. Keep Main intact and do not interrupt writes.
See MULTIBOOT.md and SAFETY.md. C10d remains available for rollback.

Scanning behavior is unchanged: independent non-scanning-VFO browsing, optional
Watch other VFO, and PTT pause/resume are retained. Watch defaults Off each boot;
enabling it slows scanning. This is one receiver, not simultaneous dual reception
or two independent scanners. See RELEASE-C10c.md for scanning details.

## Validation and provenance

All 14 host suites passed, including animation bounds and pixel isolation over
both receiving/selected sides, single/dual layouts, display modes and meter styles,
plus persistence and animation timing. ClearUI and Fusion builds passed;
multiboot RAM-stub isolation passed (924 bytes, 85 branches).
Hardware/RF performance of the new animations has not been comprehensively tested.

Built with Arm GNU 13.3.Rel1 using
`cmake --preset ClearUI -DEDITION_STRING=C10e`. This preserves the tested binary
with embedded base commit `55e3157b` plus the animation changes included in the
exact committed source archive. Startup edition: C10e; programming identity:
ClearUI C10. Firmware size: 116,776 bytes. SHA-256:
`c34726c322dac4e7a1fc111bd74a5dcda86946593eccb9e345ba182cdaf3dbcb`

## Safety and licensing

Experimental firmware for the PY32-based **UV-K1**, not older DP32G030 UV-K5/UV-K6
radios. Use at your own risk: flashing may brick hardware, lose settings or
calibration, or cause unexpected behavior, including transmission. No warranty
is provided. To the fullest extent permitted by applicable law, maintainers and
contributors disclaim liability for damage, loss, interference or unlawful use.
You are responsible for required licenses, authorizations and lawful operation.
No disclaimer overrides rights or liabilities that cannot legally be excluded.
A regular release and host tests are not a safety certification.

No personal channels or calibration are included. Flashing does not automatically
disable TX on public-safety channels. Read SAFETY.md before installation.
Upstream licenses and copyright notices are retained.
