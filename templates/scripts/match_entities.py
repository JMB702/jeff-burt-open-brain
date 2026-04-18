#!/usr/bin/env python3
"""Alias pre-matcher: produce an entity/people shortlist per paragraph.

Reads a daily (or historical) note and, for each paragraph, matches aliases
from `entities-index.json` against the paragraph text using case-insensitive
whole-word regex. Emits JSON that the updater can use as a shortlist so the
LLM doesn't have to walk the full alias map for every paragraph.

The shortlist is advisory, not authoritative — the updater step still reads
every paragraph and catches indirect references the regex can't.

Usage:
    python3 scripts/match_entities.py <note-path>        # JSON to stdout
    python3 scripts/match_entities.py <note-path> --pretty
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
INDEX_JSON = VAULT_ROOT / "entities-index.json"


def load_alias_map() -> dict:
    if not INDEX_JSON.exists():
        sys.stderr.write(
            "entities-index.json not found — run: python3 scripts/build_entity_index.py\n"
        )
        sys.exit(1)
    return json.loads(INDEX_JSON.read_text(encoding="utf-8"))["alias_map"]


def compile_patterns(alias_map: dict) -> list[tuple[re.Pattern, str, dict]]:
    """Return (compiled_regex, alias_text, entity_record) tuples."""
    patterns: list[tuple[re.Pattern, str, dict]] = []
    # Longer aliases first so a compound name like "Recipe App" matches before
    # a short alias like "Recipe" that would otherwise consume the same span.
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        record = alias_map[alias]
        pattern = re.compile(
            r"(?i)(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"
        )
        patterns.append((pattern, alias, record))
    return patterns


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def match_paragraph(paragraph: str, patterns: list[tuple[re.Pattern, str, dict]]) -> dict:
    entities: dict[str, dict] = {}
    people: dict[str, dict] = {}
    for regex, alias, record in patterns:
        if regex.search(paragraph):
            bucket = people if record["type"] == "person" else entities
            key = record["entity"]
            if key not in bucket:
                bucket[key] = {
                    "entity": record["entity"],
                    "type": record["type"],
                    "path": record["path"],
                    "matched_aliases": [alias],
                }
            else:
                if alias not in bucket[key]["matched_aliases"]:
                    bucket[key]["matched_aliases"].append(alias)
    return {
        "entities": list(entities.values()),
        "people": list(people.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", help="Path to a daily or historical note")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    note_path = Path(args.note)
    if not note_path.is_absolute():
        note_path = (VAULT_ROOT / args.note).resolve()
    if not note_path.exists():
        sys.stderr.write(f"note not found: {note_path}\n")
        return 1

    alias_map = load_alias_map()
    patterns = compile_patterns(alias_map)
    paragraphs = split_paragraphs(note_path.read_text(encoding="utf-8"))

    output = []
    for i, para in enumerate(paragraphs):
        matches = match_paragraph(para, patterns)
        output.append(
            {
                "paragraph_index": i,
                "text": para,
                "candidate_entities": matches["entities"],
                "candidate_people": matches["people"],
                "unmatched": not matches["entities"] and not matches["people"],
            }
        )

    payload = {
        "note": str(note_path.relative_to(VAULT_ROOT))
        if VAULT_ROOT in note_path.parents
        else str(note_path),
        "paragraph_count": len(output),
        "paragraphs": output,
    }

    indent = 2 if args.pretty else None
    print(json.dumps(payload, indent=indent, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
