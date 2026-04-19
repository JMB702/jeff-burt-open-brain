#!/usr/bin/env python3
"""
Materialize a single photo from Apple Photos so Claude can view it.

Single UUID only, by design — every export is a deliberate tool call.
This mechanically enforces the "one photo at a time" rule in the Vision
policy (see .claude/skills/what-did-i-see/SKILL.md).

Writes to tmp/photo-exports/<uuid>.<ext> (gitignored) and prints the
absolute path to stdout. The caller (a skill) is expected to then use
the Read tool to feed the file into Claude's multimodal context.

If "Optimize Mac Storage" is active and the original isn't on disk,
falls back to the preview derivative that's always present locally.

Usage:
  python3 scripts/photos_export.py <uuid>
  python3 scripts/photos_export.py <uuid> --size preview
  python3 scripts/photos_export.py <uuid> --size original
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "tmp" / "photo-exports"


def find_photo(uuid: str):
    try:
        import osxphotos  # type: ignore
    except ImportError:
        print("error: osxphotos is not installed. Run `pip3 install osxphotos`.", file=sys.stderr)
        sys.exit(3)
    try:
        db = osxphotos.PhotosDB()
    except Exception as e:
        print(
            f"error: could not open Photos library ({e}).\n"
            "Most common cause: Full Disk Access is not granted to this terminal.",
            file=sys.stderr,
        )
        sys.exit(4)
    matches = db.photos(uuid=[uuid])
    if not matches:
        print(f"error: no photo with UUID {uuid}", file=sys.stderr)
        sys.exit(5)
    return matches[0]


def export_preview(photo, dest: Path) -> Path | None:
    """Copy a derivative (preview) to dest. Returns the path or None."""
    derivatives = getattr(photo, "path_derivatives", None) or []
    if not derivatives:
        return None
    # osxphotos orders derivatives smallest → largest; pick the last (largest preview).
    src = Path(derivatives[-1])
    if not src.exists():
        return None
    final = dest.with_suffix(src.suffix)
    shutil.copy2(src, final)
    return final


def export_original(photo, dest: Path) -> Path | None:
    src_path = getattr(photo, "path", None)
    if not src_path:
        return None
    src = Path(src_path)
    if not src.exists():
        return None
    final = dest.with_suffix(src.suffix)
    shutil.copy2(src, final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("uuid", help="UUID of the photo to export")
    parser.add_argument("--size", choices=["preview", "original"], default="preview",
                        help="preview = ~1 MB derivative, always local. original = full resolution, may require iCloud fetch.")
    args = parser.parse_args()

    photo = find_photo(args.uuid)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    dest_base = EXPORT_DIR / args.uuid

    if args.size == "original":
        result = export_original(photo, dest_base)
        if result is None:
            print(
                f"warn: original for {args.uuid} not on disk (likely Optimize Mac Storage). "
                "Falling back to preview.",
                file=sys.stderr,
            )
            result = export_preview(photo, dest_base)
    else:
        result = export_preview(photo, dest_base)
        if result is None:
            # Some libraries have no cached preview; try the original as a fallback.
            result = export_original(photo, dest_base)

    if result is None:
        print(
            f"error: could not export {args.uuid}. Neither preview nor original was reachable.",
            file=sys.stderr,
        )
        return 6

    print(str(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
