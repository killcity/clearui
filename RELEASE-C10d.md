# ClearUI C10d — 50% receive shading

Regular UV-K1 release based on Fusion 6.0.0. Replaces C10c's dotted RX outline
with the approved darker background shade. All other C10c features are retained.

## Receive highlighting

**Display → RX frame → Off / Light shade / Inverted**

- Light shade uses a steady 50% checkerboard to simulate gray on the monochrome
  display. Text remains black, with one pixel of clear space around existing text
  and meters. The effective density is lower near content.
- Only the VFO receiving audio is shaded, regardless of which VFO is selected.
  Rounded corners, fonts, meter positions, pills and the existing layout are retained.
- No blinking, moving pattern, new separator, or added RX badge.
- Off and Inverted are unchanged. Dotted is removed; existing Dotted selections
  automatically become Light shade. Fresh/reset configurations still default Off.
- The setting persists in the active configuration bank. It applies during
  established receive/monitor audio, including scan reception, not idle,
  unqualified incoming signals or transmission.

## Scanning and programming

C10c's independent non-scanning-VFO channel browsing, optional Watch other VFO,
and PTT scan pause/resume are unchanged. Watch defaults Off each power-on; enabling
it adds fixed-VFO checks and slows scanning. The radio has one receiver, not two
simultaneous receivers or two independent scanners. See RELEASE-C10c.md for details.

Use the same `clearui-multiboot-c10.py` CHIRP driver. No reset, memory conversion
or driver update is required. Keep ClearUI's configuration bank separate from
Fusion; calibration and startup logo remain shared.

Download `clearui-c10d.zip` for firmware, exact committed source, driver, migration
utility, instructions, licenses and checksums. The standalone binary is
`ClearUI-C10d-UV-K1.bin`. Back up settings and calibration before updating your
ClearUI user slot through UV Studio's multiboot workflow. Keep Main intact and
never interrupt a slot write or restore. See MULTIBOOT.md and SAFETY.md.

## Validation and provenance

All 14 host suites passed, including exact pixel-mask checks for the full shading
pattern, clear text margins and receiving-pane isolation across both VFO
selections, receiving sides, meter styles, single/dual display, scanning and
receive/monitor/idle/incoming/transmit states. The ClearUI build and multiboot
RAM-stub isolation check passed. The user approved the appearance; comprehensive
hardware/RF validation has not been performed. Host checks are not a safety
certification.

This release preserves the tested C10-sh5 binary, built with Arm GNU 13.3.Rel1
using `cmake --preset ClearUI -DEDITION_STRING=C10-sh5`. Embedded base commit:
`266a3f50`, plus the shade changes included in this release's committed source.
Startup edition remains C10-sh5; programming identity remains ClearUI C10.
Firmware size: 115,096 bytes. SHA-256:
`da2a1dfc8c44733faf5b907baabdd081411abda08cea8eaa6869e5506241a5fc`

C10c remains available for rollback. No personal channels or calibration are
included. Flashing does not automatically disable TX on public-safety channels.

## Safety and licensing

Experimental firmware; use at your own risk. It may brick hardware, lose data or
calibration, or behave unexpectedly, including during transmission. No warranty
is provided. To the fullest extent permitted by applicable law, maintainers and
contributors disclaim liability for damage, losses, interference or unlawful use.
You are responsible for required licenses, authorizations and lawful operation.
No disclaimer overrides rights or liabilities that cannot legally be excluded.
Read SAFETY.md before installation. A regular release is not a safety certification.

For the PY32-based UV-K1, not older DP32G030 UV-K5/UV-K6 radios. Upstream licenses
and copyright notices are retained.
