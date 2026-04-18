#!/usr/bin/env python3
"""Backfill `last_entry_date` into every entity file's YAML frontmatter.

Scans entity files in projects/, Other Entities/, events/, Medical/. For each
file, finds the most recent `## YYYY-MM-DD` (or `## YYYY-MM-DD (historical ...)`)
entry header in the body and writes that date into the frontmatter as
`last_entry_date: "YYYY-MM-DD"`.

Idempotent: existing `last_entry_date` values are overwritten with the current
truth. Files with no dated entries are left unchanged.

Usage:
    python3 scripts/backfill_last_entry_date.py            # write changes
    python3 scripts/backfill_last_entry_date.py --dry-run  # preview only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
ENTITY_FOLDERS = ("projects", "Other Entities", "events", "Medical")

ENTRY_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})(?:\s|$)")


def split_frontmatter(text: str) -> tuple[list[str], list[str]] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1 :]
    return None


def find_last_entry_date(body_lines: list[str]) -> str | None:
    latest: str | None = None
    for line in body_lines:
        m = ENTRY_HEADER_RE.match(line.strip())
        if not m:
            continue
        date = m.group(1)
        if latest is None or date > latest:
            latest = date
    return latest


def rewrite_frontmatter(fm_lines: list[str], date: str) -> list[str]:
    out: list[str] = []
    replaced = False
    for line in fm_lines:
        if line.strip().startswith("last_entry_date:"):
            out.append(f'last_entry_date: "{date}"')
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f'last_entry_date: "{date}"')
    return out


def process_file(path: Path, dry_run: bool) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    split = split_frontmatter(text)
    if split is None:
        return False, "no frontmatter"
    fm_lines, body_lines = split
    date = find_last_entry_date(body_lines)
    if date is None:
        return False, "no dated entries"

    current = None
    for line in fm_lines:
        if line.strip().startswith("last_entry_date:"):
            current = line.split(":", 1)[1].strip().strip('"').strip("'")
            break

    if current == date:
        return False, f"already {date}"

    new_fm = rewrite_frontmatter(fm_lines, date)
    new_text = "---\n" + "\n".join(new_fm) + "\n---\n" + "\n".join(body_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    status = f"{current or '(missing)'} -> {date}"
    return True, status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed = 0
    skipped = 0
    for folder in ENTITY_FOLDERS:
        base = VAULT_ROOT / folder
        if not base.exists():
            continue
        for path in sorted(base.glob("*.md")):
            did_change, note = process_file(path, args.dry_run)
            rel = path.relative_to(VAULT_ROOT)
            if did_change:
                changed += 1
                marker = "WOULD UPDATE" if args.dry_run else "updated"
                print(f"  {marker}: {rel}: {note}")
            else:
                skipped += 1

    verb = "would update" if args.dry_run else "updated"
    print(f"\n{verb} {changed} files, skipped {skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
