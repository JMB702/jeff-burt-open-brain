#!/usr/bin/env python3
"""Print the list of daily and historical notes needing updater processing.

A note needs processing when either:
  - its filename is not in `notes/.manifest`, or
  - its current MD5 hash differs from the stored hash.

Output format (stdout, one per line):
  <relative-path>|<status>|<current-md5>|<stored-md5-or-NEW>

status is `new` or `modified`. Notes up-to-date with the manifest are omitted.
Exit code is always 0 — downstream readers branch on empty output.

Usage:
    python3 scripts/notes_to_process.py
    python3 scripts/notes_to_process.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = VAULT_ROOT / "notes" / ".manifest"
DAILY_DIR = VAULT_ROOT / "notes" / "raw-daily-notes"
HISTORICAL_DIR = VAULT_ROOT / "notes" / "historical-notes"


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, str]:
    if not MANIFEST_PATH.exists():
        return {}
    out: dict[str, str] = {}
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if "|" not in line:
            continue
        name, _, hash_ = line.partition("|")
        out[name.strip()] = hash_.strip()
    return out


def iter_notes():
    if DAILY_DIR.exists():
        for p in sorted(DAILY_DIR.rglob("*.md")):
            yield p
    if HISTORICAL_DIR.exists():
        for p in sorted(HISTORICAL_DIR.rglob("*.md")):
            yield p


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    pending: list[dict] = []

    for path in iter_notes():
        current = md5_file(path)
        stored = manifest.get(path.name)
        if stored is None:
            status = "new"
        elif stored != current:
            status = "modified"
        else:
            continue
        pending.append(
            {
                "path": str(path.relative_to(VAULT_ROOT)),
                "name": path.name,
                "status": status,
                "current_md5": current,
                "stored_md5": stored or "NEW",
            }
        )

    if args.json:
        print(json.dumps({"pending": pending, "count": len(pending)}, indent=2))
    else:
        for entry in pending:
            print(f"{entry['path']}|{entry['status']}|{entry['current_md5']}|{entry['stored_md5']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
