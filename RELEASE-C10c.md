# ClearUI C10c — Independent channel browsing and RX highlights

Regular release for the UV-K1, based on Fusion 6.0.0. Includes the complete source,
firmware, matching C10 CHIRP driver, migration utility, licenses and checksums.

## Channel navigation while scanning

When one VFO scans, selecting the other VFO now lets the arrow keys change its
channel within its own selected group, without stopping or redirecting the scan.
This works with Watch other VFO Off or On. Frequency-mode tuning is supported too;
frequency changes are saved on key release. If the receiver is currently watching
the edited VFO, it retunes to that VFO's new channel. Browsing does not deliberately
interrupt reception on the scanning VFO.

## Optional receive highlighting

**Display → RX frame → Off / Dotted / Inverted**:

- Off: original display, and the default for fresh/reset configurations.
- Dotted: a steady rounded outline around the VFO receiving audio. Dots avoid
  existing edge-aligned text and meters, so the outline may have gaps near content.
- Inverted: reverses the receiving pane with rounded corners. The other VFO and
  top status bar remain unchanged.

The highlight follows reception, not selection. Works during established receive
or monitor audio, including scan reception. Idle, unqualified incoming signals and
transmit do not activate it. No fonts, meter positions, pills or layout were moved;
no new separator, RX badge or flashing animation was added. Existing test-build
RX frame On settings become Dotted. The choice persists in the active config bank.

## Scan capabilities retained

- A/B selection does not stop the original scan.
- Watch other VFO is optional, session-only and defaults to Off at power-on.
  On adds a 200 ms fixed-VFO listening window between scan advances and can
  substantially reduce scan speed. Off retains normal scanning without those checks.
- Qualifying fixed-VFO audio holds reception until it ends; scan-side hits use the
  scan-resume policy. One receiver interleaves reception; this is not simultaneous
  dual reception or two independent scans, and short transmissions may be missed.
- PTT on the non-scanning VFO pauses the scan and resumes it after unkey and normal
  TX/tail shutdown. PTT on the scanning VFO still cancels scanning. Existing TX
  protections remain in place. Holding A/B changes single/dual mode and stops scan.

## Installation and programming

Download `clearui-c10c.zip` for the full bundle, or `ClearUI-C10c-UV-K1.bin` alone.
Back up settings and calibration first. Use UV Studio's multiboot slot-writing
workflow to update your ClearUI user slot while retaining Main. Keep ClearUI's
configuration bank separate from Fusion. See MULTIBOOT.md for details; never
interrupt a slot write or restore.

The same `clearui-multiboot-c10.py` CHIRP driver works. No configuration reset is
required. It preserves the reserved fields used for the new display setting.
Calibration and startup logo remain shared. No personal channels or calibration
are bundled; flashing does not automatically disable TX on public-safety channels.

## Validation and build provenance

All 14 host test suites pass. Added coverage exercises non-scanning-VFO memory
and frequency edits, watch On/Off, setting migration and persistence, and exact
pixel changes across both VFO selections, receiving sides, meter styles,
single/dual display, scanning and receive/monitor/idle/incoming/transmit states.
ClearUI and reference Fusion builds pass, including multiboot RAM-stub isolation.
**These changes have not yet been hardware-tested.** Host tests are not RF or
hardware-safety certification.

This release preserves the exact tested C10-rxi binary, built with Arm GNU
13.3.Rel1 and `cmake --preset ClearUI -DEDITION_STRING=C10-rxi`. The embedded base
commit is `674a9db4` plus the local changes included in this release's committed
source archive. Startup edition: C10-rxi; programming identity: ClearUI C10.
Firmware: 114,972 bytes. SHA-256:
`778261cdf78703822959b50fece65b540ab207483744eb2d6104ed959074f37e`

C10b remains available for rollback. The inherited voltage splash may display
upstream branding; this release does not redesign startup screens.

## Safety and licensing

Experimental firmware; use at your own risk. It may brick hardware, lose settings
or calibration, or behave unexpectedly, including during transmission. No warranty
is provided. To the fullest extent permitted by applicable law, maintainers and
contributors disclaim liability for damage, losses, interference or unlawful use.
You are responsible for required licenses, authorizations and lawful operation.
No disclaimer overrides rights or liabilities that cannot legally be excluded.
Read SAFETY.md before installation. A regular release is not a safety certification.

For the PY32-based UV-K1, not older DP32G030 UV-K5/UV-K6 radios. Upstream licenses
and copyright notices are retained.
