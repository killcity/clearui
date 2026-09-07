# Installation and recovery

> [!WARNING]
> **Use at your own risk.** Flashing can brick your radio or destroy settings and
> calibration. No warranty, recovery or compensation is promised. Liability is
> disclaimed to the fullest extent permitted by law. You are responsible for
> required licenses, authorizations and compliance before transmitting.
> Read [SAFETY.md](SAFETY.md) before proceeding.

This experimental build is intended for the **UV-K1 with PY32F071 MCU**.
It is not the older UV-K5/UV-K6 build. Do not infer compatibility from the
radio's appearance or from the upstream repository's other supported models.

## Before flashing

- Save a configuration image and a separate calibration backup using tools
  appropriate for the firmware currently installed on your radio.
- Keep a known-good firmware binary and the upstream recovery instructions.
- Charge the battery and use a reliable programming cable/USB connection.
- Do not interrupt power during flashing or upload another radio's calibration.

Flash `Fusion-v5.9.0-ClearUI-C8c-UV-K1.bin` using the normal UV-K1/Fusion
flashing workflow. Upstream documents its tooling in
[README-UPSTREAM.md](README-UPSTREAM.md#flashing-the-firmware-with-uv-studio).
Do not use the legacy K5 V1 recovery utility in the upstream tools directory
as a UV-K1 recovery procedure.

## CHIRP

Use `chirp/fusion-clearui-chirp-c8.py` from this repository or the matching
release attachment. Load it as a custom CHIRP module, then select
**Quansheng → UV-K1 & UV-K5 V3 (Fusion ClearUI)**. Its inherited model label
does not establish hardware testing on the UV-K5 V3.

Download a fresh image from the radio with this module before editing and
uploading. Keep an untouched copy. Stock Fusion images lack ClearUI's extended
group-name region; do not bypass an image-size or firmware-compatibility error.

The programming format intentionally identifies as **ClearUI C5**, even when
the displayed build is C8c. A C8 driver works with C8c; an old C1-only driver
does not. The ABI identifier is not the UI release number.

Group names are editable in the CHIRP scan-list settings and support up to
16 ASCII characters. Group number N corresponds to scan list N. Channels have
a **Receive only** setting; check it explicitly where transmission must be
disabled. Flashing does not classify frequencies, set channel power, or make
an existing channel list receive-only.

Updating C8/C8a/C8b to C8c needs no factory reset or channel re-upload. The
vertical Spine meter defaults on fresh/full-reset settings; upgrades keep the
saved choice. Select Meter style → Spine to switch without resetting.
Back up first regardless. When returning to stock firmware,
restore an appropriate stock-format backup; do not assume it honors ClearUI's
receive-only marker or extended group names.

## Reporting problems

Include hardware revision, build version, exact reproduction steps and whether
single or dual VFO is active. Avoid attaching personal configuration/calibration
dumps publicly. Screenshots and a minimal synthetic example help.
