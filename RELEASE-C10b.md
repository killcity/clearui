# ClearUI C10b — Resume scanning after PTT

Regular release of this experimental UV-K1 project, based on Fusion 6.0.0.
This adds PTT pause/resume to C10a's scan ownership and optional fixed-VFO watch.

## New PTT behavior

When one VFO is scanning and the **other VFO is selected**:

1. PTT pauses the scan and requests transmission on the selected VFO through the
   existing transmit-safety checks.
2. Releasing PTT resumes the original scan after normal TX/tail shutdown finishes.
3. The scan retains its original VFO, direction, group, cursor and saved result.

Receive-only and TX-lock protections remain enforced. If a transmission request
is rejected, the scan can resume after PTT release. Resume waits for physical PTT
release, inactive transmission, no pending TX request and completion of repeater
tail elimination. A configured tail delay means resume may not be instantaneous.

**PTT on the scanning VFO still cancels the scan**, as before. C10b does not add
scanning during transmission, change transmit permissions or implement two scans.

## Scan/watch behavior retained

- Tapping A/B changes selection without stopping the original VFO's scan.
- While scanning: **Menu → Watch other VFO → Off / On**.
- Off is the power-on default: no extra fixed-channel checks, for normal scan speed.
- On checks the fixed VFO between scan advances using a 200 ms listening window;
  this can substantially slow scanning. The proposed Fast watch mode is not included.
- A qualifying fixed-channel reception holds speaker audio until it ends, then
  scanning resumes. Scan-side hits follow the selected scan-resume policy.
- Watch is session-only and resets to Off at power-on. PTT resume works with watch
  Off or On. Holding A/B changes single/dual mode and stops the scan.
- The radio has a single receiver: reception is interleaved, not simultaneous,
  and short transmissions may be missed.

## Install and program

Download `clearui-c10b.zip` for the firmware, full source, matching driver,
migration utility, instructions, licenses and checksums. A standalone binary is
also attached.

Back up settings and calibration first. With multiboot firmware running normally,
use **UV Studio → Multiboot → Write to slot** to update your ClearUI user slot
with `ClearUI-C10b-UV-K1.bin`. Keep Main intact. Hold Menu at power-on to select
and restore ClearUI. Never interrupt power during slot writes or restores.

Use the **same C10 CHIRP driver**, `clearui-multiboot-c10.py`. The programming format
and configuration banks are unchanged; existing C10 users do not need a reset.
Keep ClearUI's bank separate from Fusion. Calibration and startup logo remain
shared; see MULTIBOOT.md for installation and legacy ClearUI memory migration.

## Validation and limitations

All 14 local host test suites pass, including the actual PTT handler's routing,
scan pause/resume transitions, both VFO owners, both scan directions, memory and
frequency scans, cancellation, and existing receive-only/TX-gating checks.
Both ClearUI and reference Fusion builds pass; the multiboot RAM-restore isolation
check passes. **The new PTT-resume behavior has not yet been tested on the radio.**
These tests do not establish RF performance or hardware safety.

The startup edition is `C10-PTT`; the programming identity remains `ClearUI C10`.
The inherited voltage splash may display F4HWN branding. No startup-screen redesign,
general text-renderer repair or unrelated meter fix is included. C10a remains
available for rollback.

Firmware size: 114,100 bytes. SHA-256:
`69d0be03ea5030e25b3a6237b8b9bf39fa4c6bad723512c57e3736263d9dcfc4`

This release preserves the local host-tested binary, built with Arm GNU 13.3.Rel1
and `cmake --preset ClearUI -DEDITION_STRING=C10-PTT`. Its embedded base commit is
`72f959a2`, plus the PTT-resume changes now committed in the release tag. The bundled
source archive includes those changes. Package metadata marks hardware validation
false because the complete hardware validation cycle has not been performed.

## Safety and licensing

**Experimental firmware; use at your own risk.** It may brick a radio, lose data
or calibration, or behave unexpectedly, including during transmission. No warranty
is provided. To the fullest extent permitted by applicable law, maintainers and
contributors disclaim liability for damage, losses, interference or unlawful use.
You are responsible for required licenses, authorizations and lawful operation.
No disclaimer overrides rights or liabilities that cannot legally be excluded.
Read SAFETY.md before installation. A regular release is not a safety certification.

For the PY32-based UV-K1, not older DP32G030 UV-K5/UV-K6 radios. No personal channels
or calibration are included. Flashing does not automatically make public-safety
channels receive-only. Upstream licenses and copyright notices are retained.
