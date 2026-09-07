# ClearUI CHIRP module

`fusion-clearui-chirp-c8.py` is the editable Python source loaded by CHIRP.
It is derived from F4HWN Fusion 5.9.0's module and is licensed under
**GPL-2.0-or-later**, with all original author notices retained. See [COPYING](COPYING).

The upstream input is kept in `upstream/f4hwn.fusion.chirp.v5.9.0.py` so
regeneration does not depend on a temporary file or private radio backup.
Its SHA-256 is `09d23891a6dc44478cb3e8fd16e1f00fdf33673b4e2faffae765ad812b3a0ff2`.
It came from the upstream Fusion 5.9.0 release distribution; no radio data
is embedded in either driver.

From the repository root:

```sh
python3 tools/build_clearui_driver.py chirp/upstream/f4hwn.fusion.chirp.v5.9.0.py chirp/fusion-clearui-chirp-c8.py --meter-styles --battery-styles
python3 tools/test_clearui_driver.py
```

These dependency-free checks verify syntax and regeneration, not CHIRP GUI,
serial transfers or hardware compatibility. See [installation notes](../INSTALL.md).
