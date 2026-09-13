#!/usr/bin/env python3
"""Package a built C10 test image; never accesses the radio or publishes files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New package directory (must not exist)")
    parser.add_argument("--firmware-name", default="ClearUI-C10-test-UV-K1.bin")
    parser.add_argument("--edition", default="ClearUI C10-test")
    parser.add_argument("--build-note", default="")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
        parser.error("Commit candidate changes before packaging")
    binary = root / "build/ClearUI/f4hwn.clearui.bin"
    data = binary.read_bytes()
    sp, pc = struct.unpack_from("<II", data)
    if not (sp == 0x20004000 and pc & 1 and
            0x08002800 <= (pc & ~1) < 0x08002800 + len(data) and
            len(data) <= 120832 and b"ClearUI C10\x00" in data):
        parser.error("Invalid C10 identity, vectors or image size")
    # Rebuild and run host checks before invoking this packager. Include exact
    # committed sources so a local-only candidate remains reproducible/auditable.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    args.output.mkdir(parents=True, exist_ok=False)
    copies = {
        binary: args.firmware_name,
        root / "chirp/clearui-multiboot-c10.py": "clearui-multiboot-c10.py",
        root / "tools/migrate_clearui_multiboot.py": "migrate_clearui_multiboot.py",
        root / "chirp/COPYING": "CHIRP-COPYING",
    }
    for name in ("MULTIBOOT.md", "SAFETY.md", "LICENSE", "NOTICE"):
        copies[root / name] = name
    for notes in sorted(root.glob("RELEASE-C10*.md")):
        copies[notes] = notes.name
    for source, name in copies.items():
        shutil.copy2(source, args.output / name)
    shutil.copytree(root / "LICENSES", args.output / "LICENSES")
    if (root / "images/rx-animations").is_dir():
        shutil.copytree(root / "images/rx-animations", args.output / "rx-animations")
    subprocess.run(["git", "archive", "--format=tar.gz", "--prefix=clearui-source/",
                    "-o", str(args.output.resolve() / "clearui-source.tar.gz"), "HEAD"],
                   cwd=root, check=True)
    (args.output / "BUILD.json").write_text(json.dumps({
        "edition": args.edition, "upstream": "Fusion v6.0.0",
        "build_note": args.build_note,
        "source_commit": commit, "binary_bytes": len(data),
        "target": "UV-K1", "hardware_validated": False,
        "compiler": "Arm GNU Toolchain 13.3.Rel1", "preset": "ClearUI",
    }, indent=2) + "\n")
    paths = sorted(p for p in args.output.rglob("*") if p.is_file())
    (args.output / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(args.output)}\n"
        for p in paths))
    archive = shutil.make_archive(str(args.output), "zip", args.output.parent, args.output.name)
    print(f"Packaged {len(data)}-byte C10 test firmware from {commit}\n{archive}")


if __name__ == "__main__":
    main()
