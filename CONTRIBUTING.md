# Contributing to ClearUI

Keep changes focused, preserve upstream attribution, and include reproduction
steps or tests. ClearUI-specific behavior should be guarded by `ENABLE_CLEAR_UI`
where appropriate; the Fusion preset remains available.

Build ClearUI before running `python3 tools/test_clearui.py`: the menu harness
reads its generated Ninja feature definitions. The runner uses repository-relative
paths and synthetic data, with no radio or user backup needed. It checks font
regeneration, groups, menus, receive-only guards, storage, key timing, waterfall
logic, actual display rendering and CHIRP driver regeneration/syntax.

Also build the stock-behavior preset when modifying shared code:

```sh
cmake --preset Fusion
cmake --build --preset Fusion -j4
git diff --check
```

CI builds ClearUI and Fusion with Arm GNU Toolchain 13.3.Rel1 on Linux and runs
the host checks. CI artifacts are experimental builds, not hardware certification.
The standalone driver checks do not simulate CHIRP serial transfers; programming
and RF/audio behavior still need hardware validation before a stable release.

## Publication checklist

- Check source changes for credentials, local paths and private data.
- Keep LICENSE, NOTICE and per-component attribution with source and releases.
- List unresolved hardware issues rather than claiming host tests resolve them.
- Publish a tagged prerelease with binary, matching driver, source and checksums.
- Never commit personal radio dumps or auto-upload firmware to a radio.
- Do not replace the ClearUI C5 ABI identifier for a cosmetic version bump.

Additional local conversion/driver tests used private source memories. Those
inputs and reports are deliberately not part of this public repository.
Use synthetic fixtures for public tests.

## Regenerate the gallery

After configuring ClearUI, install Pillow 11+ in your development Python
environment and run `python3 tools/render_clearui_gallery.py`. It uses the
actual UI harnesses with synthetic data, then places unmodified screen pixels
in captioned cards. Keep previews clearly labeled; they are not radio photos.
