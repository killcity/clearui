# ClearUI C10a — Scan control and optional VFO watch

A regular release of our experimental UV-K1 project, based on Fusion 6.0.0.
This is the same toggle-enabled binary tested by the user; it does not include
the proposed "Fast watch" optimization. C10 remains available for rollback.

## Scanning changes

- **Tap A/B without stopping the scan.** The VFO that started scanning keeps its
  scan while the selected VFO changes. The scan header identifies A or B.
- **Optional fixed-VFO listening:** while scanning, tap **Menu → Watch other VFO
  → Off / On**. Available for both memory and frequency scanning.
- **Off is the default:** no added checks of the other VFO, preserving normal
  scan speed. Selecting the other VFO alone does not make the receiver listen there.
- **On:** with dual watch enabled, the fixed VFO gets a full tune and a 200 ms
  listening window between scan advances. This can substantially slow scanning.
- A qualifying fixed-channel signal gets speaker audio and holds reception until
  it ends, followed by a short delay before the scan resumes. A/B selection does
  not interrupt that audio. Fixed-channel hits do not overwrite the scan result.
- Scan-side hits retain the configured scan-resume policy, including stop mode.
- Turning watch Off during fixed-channel reception allows that audio to finish.
- The watch preference is session-only: it resets to Off at power-on.
- Holding A/B changes single/dual mode and stops the scan. PTT retains its existing
  behavior: the first press cancels a running scan rather than transmitting.

This radio has one receiver. It checks the two sides in turn, not simultaneously;
short transmissions can be missed. This is **one scanning VFO plus one fixed VFO**,
not two concurrent scans. Normal dual watch still applies outside scanning.

## Installation and CHIRP

Download `clearui-c10a.zip` for firmware, driver, migration tool, exact sources,
instructions, licenses and checksums. The `.bin` is also attached separately.

Back up settings and calibration first. In UV Studio, with compatible multiboot
firmware running normally (not DFU), use **Multiboot → Write to slot** to install
`ClearUI-C10a-UV-K1.bin` in your ClearUI user slot. Keep Main intact. Hold Menu at
power-on to select/restore it; never interrupt power during a write or restore.

Use the same **C10 CHIRP module**, `clearui-multiboot-c10.py`. No programming-format
change or reset is required for existing C10 users. Keep ClearUI on its own bank.
Fusion's Main channels do not automatically appear in ClearUI's separate bank;
see MULTIBOOT.md for legacy ClearUI channel/group migration. Calibration and the
startup logo remain shared. Do not upload an old standalone image directly.

## Test status and known limitations

- All 14 local host regression suites pass, including scan ownership, A/B focus,
  watch Off/On, fixed-channel audio hold, scan resume, tone rejection and stop
  isolation. ClearUI and reference Fusion builds pass.
- The multiboot RAM restore routine passes its build-time isolation check.
- The user reports this build works well on their UV-K1. RF timing, sensitivity,
  tone detection and every combination of settings are not comprehensively tested.
- The binary retains the short startup edition label `C10-scan` and C10 protocol
  identity. The inherited voltage startup screen may still show F4HWN branding.
  No startup-screen redesign or general text-renderer fix is included.
- Dual-watch meter behavior still warrants testing. Report reproducible display
  or reception issues with the chosen bank, scan mode and watch setting.

Firmware SHA-256:
`25963b8a71d6c4fea3a6575df77bf4ec15dcbd348f4fba30b5ca2cc25c62ffa5`

The binary was built before the release commit with the scan/watch changes in the
working tree, using Arm GNU 13.3.Rel1 and `-DEDITION_STRING=C10-scan`. Its embedded
base commit is `510b867d`; the release tag and bundled source archive include those
changes. This preserves the exact tested binary rather than silently rebuilding it.

## Safety and licensing

**Experimental firmware; use at your own risk.** It may brick your radio, lose
settings/calibration or behave unexpectedly, including during transmission.
No warranty is provided. To the fullest extent permitted by applicable law,
maintainers and contributors disclaim liability for damage, losses, interference
or unlawful use. You are responsible for licenses, authorizations and lawful
operation. No disclaimer overrides rights or liabilities that cannot legally be
excluded. Read SAFETY.md. A regular release is not a certification of safety.

For the PY32-based UV-K1, not older DP32G030 UV-K5/UV-K6 radios. No personal
channels or calibration are distributed. Flashing does not automatically make
public-safety channels receive-only. Upstream licenses and notices are retained.
