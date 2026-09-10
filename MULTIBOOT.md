# ClearUI C10 multiboot test candidate

For the stock Quansheng UV-K1, based on upstream Fusion v6.0.0. This is a local
test candidate: builds and host tests pass, but no C10 hardware boot, firmware
switch, or CHIRP transfer has been validated. Do not treat it as a stable release.
Never use this image on older DP32G030 UV-K5/UV-K6 radios.

## What is separate, and what is shared

Fusion 6 stores a protected Main image and four user images in external flash.
Selecting an image restores it to the internal application flash; it does not
run two firmwares at once. Hold Menu during power-on to open the selector.
Never interrupt power while a restore is running.

Configuration banks 0–4 are independent of firmware slots. Give ClearUI its own
bank and leave Fusion in another bank. ClearUI's **System → Configuration bank**
setting changes the active bank and reboots. Do not deliberately share a bank
between ClearUI and stock Fusion: custom settings and channel bits differ.
Channel records, settings and ClearUI long group names now stay within the
selected bank. Calibration and the startup logo remain shared across all banks.
Do not replace the shared logo expecting it to affect ClearUI only.

## Before testing

1. Read SAFETY.md. Use a charged battery and keep a known-good recovery image.
2. Save the old radio image using its matching CHIRP module. Separately back up
   calibration using the supported tools. Keep these originals unchanged.
3. Establish official Fusion 6.0.0 as the working Main firmware, following its
   upstream instructions. Confirm its multiboot selector works before proceeding.
4. Through the UV Studio multiboot slot workflow, upload the raw
   `ClearUI-C10-test-UV-K1.bin` into an unused user slot (1–4). Do not overwrite
   protected Main or a slot you need to keep. This file is an application binary,
   not a complete external-flash image and not a bootloader.
5. Hold Menu at power-on, select ClearUI and allow the restore to finish. Verify
   the active configuration bank before editing channels or settings. Select a
   dedicated bank if needed; changing banks reboots the radio.
6. Use the bundled `clearui-multiboot-c10.py` CHIRP module. Its model is
   **Quansheng → UV-K1 & UV-K5 V3 (ClearUI Multiboot C10)**. The model name is
   inherited from upstream; this candidate is not claimed validated on UV-K5 V3.

These steps still need an end-to-end hardware trial. If the slot workflow rejects
the file or the radio reports a different firmware identity, stop; do not bypass
the checks or force a write. Use upstream recovery instructions if boot fails.

## Move existing memories and groups

Do not upload a legacy C8/C9 image directly using C10 or the stock driver. Fusion
6 changed side-key action IDs, and legacy global settings are not interchangeable.
The C10 driver requires the radio handshake `ClearUI C10` and rejects older builds.

First download and save a fresh image from the dedicated ClearUI C10 bank using
the C10 driver. Then run the bundled migration tool:

```sh
python3 migrate_clearui_multiboot.py old-clearui.img fresh-c10.img migrated-c10.img
```

In a source checkout the script is under `tools/`. The new output must not exist.
The tool copies memory channels, channel names, receive-only flags, persistent
skip flags, group memberships and group names. It clears temporary skip flags.
It preserves the fresh C10 image's VFO state, global settings, calibration, logo
and CHIRP metadata. Reconfigure side keys and display preferences in C10.
Only legacy ClearUI images with the recognized CHIRP model and size are accepted.
No radio is accessed by this script.

Open the migrated image with the C10 module, review it, then upload while C10 is
running in its dedicated bank. Confirm receive-only flags before any TX testing.
Flashing ClearUI does not automatically identify or disable TX on public-safety
channels. No personal memories or calibration are included in this package.

## Return to Fusion

Hold Menu at power-on, select Main and let the restore finish. Verify its bank
before using it. Preserve Main and backups throughout testing. Older ClearUI
standalone binaries do not gain multiboot return support just by being put in a slot.

## Validation still required before release

- Boot ClearUI, return to Main, and repeat; check firmware identity each time.
- Set distinct test channels/settings in each bank and verify neither overwrites
  the other, including long group names and bank switching after reboot.
- Download/upload with C10 CHIRP, verify the migration, and reject legacy drivers.
- Check A/B reception and signal meters, scanning, group browsing, HF listening,
  key holds, and receive-only protection on appropriate test equipment.
- Confirm calibration remains unchanged. Do not test power-loss recovery by
  deliberately interrupting a flash restore on your working radio.

Host tests cover image CRC/bounds rejection, protected Main writes, redundant
state recovery, bank address isolation, driver bounds, migration and existing UI
regressions. Builds also verify the restore routine executes from RAM. These
checks do not establish RF safety or replace physical testing.

Upstream: https://github.com/armel/uv-k1-k5v3-firmware-custom/releases/tag/v6.0.0
UV Studio: https://armel.github.io/uvstudio/
