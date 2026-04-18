#!/usr/bin/env python3
"""List dormant entities based on `last_entry_date` frontmatter.

Dormancy thresholds match OPEN BRAIN UPDATER.md Step 3b:

| Priority   | Projects     | Other Entities | Events                | Medical |
|------------|--------------|----------------|-----------------------|---------|
| active     | > 7 days     | > 14 days      | upcoming within 7d    | never   |
| background | > 14 days    | > 28 days      | upcoming within 7d    | never   |
| archive    | never        | never          | never                 | never   |

Reads `last_entry_date` from YAML frontmatter. Entities without the field are
treated as "no entries" and reported separately.

Usage:
    python3 scripts/list_dormant.py                 # human-readable
    python3 scripts/list_dormant.py --json          # JSON to stdout
    python3 scripts/list_dormant.py --today 2026-04-16
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent

FOLDER_TYPES = {
    "projects": "project",
    "Other Entities": "other",
    "events": "event",
    "Medical": "medical",
}

THRESHOLDS_DAYS = {
    ("project", "active"): 7,
    ("project", "background"): 14,
    ("other", "active"): 14,
    ("other", "background"): 28,
    # Events: handled separately by presence of a future date
    # Medical: never dormant by time
}


def parse_frontmatter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def days_since(d: str, today: date) -> int:
    return (today - datetime.strptime(d, "%Y-%m-%d").date()).days


def classify(entity_type: str, priority: str, last: str | None, today: date) -> tuple[bool, int | None]:
    """Returns (is_dormant, days_since_last)."""
    if priority == "archive":
        return False, None
    if entity_type == "medical":
        return False, None
    if not last:
        return False, None

    try:
        d = days_since(last, today)
    except ValueError:
        return False, None

    threshold = THRESHOLDS_DAYS.get((entity_type, priority))
    if threshold is None:
        return False, d
    return d > threshold, d


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--today", default=None, help="Override today's date (YYYY-MM-DD)")
    args = parser.parse_args()

    today = (
        datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else date.today()
    )

    dormant: list[dict] = []
    unknown: list[dict] = []

    for folder, entity_type in FOLDER_TYPES.items():
        base = VAULT_ROOT / folder
        if not base.exists():
            continue
        for path in sorted(base.glob("*.md")):
            fm = parse_frontmatter(path)
            priority = fm.get("priority", "")
            last = fm.get("last_entry_date") or None
            is_dormant, days = classify(entity_type, priority, last, today)
            if not last and priority not in {"archive"} and entity_type != "medical":
                unknown.append(
                    {
                        "name": path.stem,
                        "type": entity_type,
                        "priority": priority,
                        "path": str(path.relative_to(VAULT_ROOT)),
                    }
                )
                continue
            if is_dormant:
                dormant.append(
                    {
                        "name": path.stem,
                        "type": entity_type,
                        "priority": priority,
                        "last_entry_date": last,
                        "days_since": days,
                        "path": str(path.relative_to(VAULT_ROOT)),
                    }
                )

    dormant.sort(key=lambda e: e["days_since"], reverse=True)

    payload = {"today": today.isoformat(), "dormant": dormant, "unknown": unknown}

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if not dormant and not unknown:
        print(f"No dormant entities as of {today.isoformat()}.")
        return 0

    if dormant:
        print(f"Dormant entities (as of {today.isoformat()}):")
        for e in dormant:
            print(
                f"  {e['days_since']:>3}d since {e['last_entry_date']}  "
                f"[{e['priority']}]  {e['type']}: {e['name']}"
            )
    if unknown:
        print("\nEntities with no `last_entry_date` set:")
        for e in unknown:
            print(f"  [{e['priority']}]  {e['type']}: {e['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
