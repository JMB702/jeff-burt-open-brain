#!/usr/bin/env python3
"""Build a dry-run ingestion report for one Open Brain note.

This script is a Claude Code helper, not an updater replacement. It does not
edit daily notes, entity files, people profiles, the manifest, or run-delta.
It gives the updater session deterministic paragraph matching, duplicate
checks, and manifest status before Claude Code makes the final judgment calls.

Usage:
    python3 scripts/process_note.py notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md
    python3 scripts/process_note.py <note-path> --json
    python3 scripts/process_note.py <note-path> --output tmp/process-note-report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from match_entities import compile_patterns, load_alias_map, match_paragraph, split_paragraphs

VAULT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = VAULT_ROOT / "notes" / ".manifest"
DAILY_DIR = VAULT_ROOT / "notes" / "raw-daily-notes"
HISTORICAL_DIR = VAULT_ROOT / "notes" / "historical-notes"
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
ENTRY_HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?:\s+\(.+\))?\s*$")


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


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


def resolve_note_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = (VAULT_ROOT / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"note not found: {path}")
    if path.suffix.lower() != ".md":
        raise ValueError(f"note must be a markdown file: {path}")
    return path


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(VAULT_ROOT))
    except ValueError:
        return str(path)


def note_kind(path: Path) -> str:
    if path.is_relative_to(DAILY_DIR):
        return "daily"
    if path.is_relative_to(HISTORICAL_DIR):
        return "historical"
    return "unknown"


def note_date(path: Path) -> str | None:
    match = DATE_RE.match(path.stem)
    return match.group(1) if match else None


def normalize_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            stripped = stripped[1:].strip()
        lines.append(stripped)
    return re.sub(r"\s+", " ", "\n".join(lines)).strip().lower()


def section_for_date(entity_path: Path, date: str | None) -> str:
    if not date or not entity_path.exists():
        return ""
    lines = entity_path.read_text(encoding="utf-8").splitlines()
    capture = False
    out: list[str] = []
    for line in lines:
        header = ENTRY_HEADER_RE.match(line.strip())
        if header:
            if capture:
                break
            capture = header.group(1) == date
            if capture:
                out.append(line)
            continue
        if capture:
            out.append(line)
    return "\n".join(out)


def already_captured(entity_rel_path: str, date: str | None, paragraph: str) -> bool:
    entity_path = VAULT_ROOT / entity_rel_path
    section = section_for_date(entity_path, date)
    if not section:
        return False
    return normalize_text(paragraph) in normalize_text(section)


def manifest_status(path: Path, current_md5: str) -> dict[str, str | None]:
    manifest = load_manifest()
    stored = manifest.get(path.name)
    if stored is None:
        status = "new"
        action = "add"
    elif stored != current_md5:
        status = "modified"
        action = "replace"
    else:
        status = "up_to_date"
        action = "no_op"
    return {
        "status": status,
        "stored_md5": stored,
        "current_md5": current_md5,
        "action": action,
    }


def build_report(note_path: Path) -> dict[str, Any]:
    current_md5 = md5_file(note_path)
    date = note_date(note_path)
    kind = note_kind(note_path)
    alias_map = load_alias_map()
    patterns = compile_patterns(alias_map)
    paragraphs = split_paragraphs(note_path.read_text(encoding="utf-8"))

    paragraph_reports: list[dict[str, Any]] = []
    proposed_appends: list[dict[str, Any]] = []
    people_updates: dict[str, dict[str, Any]] = {}
    unmatched: list[dict[str, Any]] = []
    run_delta_entities: dict[str, dict[str, Any]] = {}

    for index, paragraph in enumerate(paragraphs):
        matches = match_paragraph(paragraph, patterns)
        paragraph_hash = sha1_text(normalize_text(paragraph))
        preview = re.sub(r"\s+", " ", paragraph).strip()
        if len(preview) > 180:
            preview = preview[:177] + "..."

        entity_matches = matches["entities"]
        person_matches = matches["people"]
        is_unmatched = not entity_matches and not person_matches

        paragraph_reports.append(
            {
                "index": index,
                "hash": paragraph_hash,
                "preview": preview,
                "text": paragraph,
                "candidate_entities": entity_matches,
                "candidate_people": person_matches,
                "unmatched": is_unmatched,
            }
        )

        if is_unmatched:
            unmatched.append({"paragraph_index": index, "hash": paragraph_hash, "preview": preview})

        for person in person_matches:
            key = person["entity"]
            people_updates.setdefault(
                key,
                {
                    "person": key,
                    "path": person["path"],
                    "paragraph_indexes": [],
                    "matched_aliases": [],
                },
            )
            people_updates[key]["paragraph_indexes"].append(index)
            for alias in person["matched_aliases"]:
                if alias not in people_updates[key]["matched_aliases"]:
                    people_updates[key]["matched_aliases"].append(alias)

        for entity in entity_matches:
            duplicate = already_captured(entity["path"], date, paragraph)
            append = {
                "entity": entity["entity"],
                "type": entity["type"],
                "path": entity["path"],
                "paragraph_index": index,
                "paragraph_hash": paragraph_hash,
                "matched_aliases": entity["matched_aliases"],
                "duplicate": duplicate,
            }
            proposed_appends.append(append)
            if not duplicate:
                delta = run_delta_entities.setdefault(
                    entity["path"],
                    {
                        "name": entity["entity"],
                        "path": entity["path"],
                        "appended_dates": [],
                        "new_paragraphs": 0,
                    },
                )
                if date and date not in delta["appended_dates"]:
                    delta["appended_dates"].append(date)
                delta["new_paragraphs"] += 1

    manifest = manifest_status(note_path, current_md5)
    active_entity_count = sum(1 for item in proposed_appends if not item["duplicate"])
    would_process_note = (
        manifest["status"] != "up_to_date"
        or active_entity_count > 0
        or bool(people_updates)
        or bool(unmatched)
    )

    return {
        "note": {
            "path": relative_path(note_path),
            "name": note_path.name,
            "kind": kind,
            "date": date,
            "md5": current_md5,
            "manifest": manifest,
        },
        "paragraph_count": len(paragraph_reports),
        "paragraphs": paragraph_reports,
        "proposed_entity_appends": proposed_appends,
        "proposed_people_updates": list(people_updates.values()),
        "missing_profile_warnings": [],
        "unmatched_paragraphs": unmatched,
        "run_delta_preview": {
            "run_date": date,
            "entities": list(run_delta_entities.values()),
            "people": sorted(people_updates.keys()),
            "notes_processed": [note_path.name] if date and would_process_note else [],
        },
        "dry_run": True,
        "claude_code_responsibilities": [
            "read every paragraph and catch indirect references",
            "decide whether unmatched paragraphs need new entities or aliases",
            "add wiki links to daily notes",
            "append verbatim paragraphs to entity files",
            "update people profiles and notes/.manifest",
            "emit tmp/run-delta.json after actual writes",
        ],
    }


def format_human(report: dict[str, Any]) -> str:
    note = report["note"]
    manifest = note["manifest"]
    lines = [
        "Open Brain note processing dry run",
        "",
        f"Note: {note['path']}",
        f"Type: {note['kind']}",
        f"Date: {note['date'] or '(unknown)'}",
        f"MD5: {note['md5']}",
        f"Manifest: {manifest['status']} -> {manifest['action']}",
        f"Paragraphs: {report['paragraph_count']}",
        "",
    ]

    appends = report["proposed_entity_appends"]
    active_appends = [a for a in appends if not a["duplicate"]]
    duplicates = [a for a in appends if a["duplicate"]]
    lines.append(f"Proposed entity appends: {len(active_appends)}")
    if active_appends:
        for append in active_appends:
            aliases = ", ".join(append["matched_aliases"])
            lines.append(
                f"- p{append['paragraph_index']} -> {append['path']} "
                f"({append['entity']}; matched: {aliases})"
            )
    if duplicates:
        lines.append("")
        lines.append(f"Duplicate direct matches skipped: {len(duplicates)}")
        for append in duplicates:
            lines.append(f"- p{append['paragraph_index']} already appears in {append['path']}")

    lines.append("")
    people = report["proposed_people_updates"]
    lines.append(f"People profile candidates: {len(people)}")
    for person in people:
        indexes = ", ".join(f"p{i}" for i in person["paragraph_indexes"])
        aliases = ", ".join(person["matched_aliases"])
        lines.append(f"- {person['person']} ({person['path']}): {indexes}; matched: {aliases}")

    lines.append("")
    unmatched = report["unmatched_paragraphs"]
    lines.append(f"Unmatched paragraphs needing Claude Code review: {len(unmatched)}")
    for item in unmatched:
        lines.append(f"- p{item['paragraph_index']}: {item['preview']}")

    lines.append("")
    lines.append("Run-delta preview:")
    lines.append(json.dumps(report["run_delta_preview"], indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("No files were edited. Claude Code still owns indirect reasoning and final writes.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("note", help="Path to a daily or historical note")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    parser.add_argument("--output", help="Write the full JSON report to this path")
    args = parser.parse_args()

    try:
        note_path = resolve_note_path(args.note)
        report = build_report(note_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = VAULT_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
