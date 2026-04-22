#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
ENTRY_HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})$")
UNFILLED_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
CONDITIONAL_MARKER_RE = re.compile(r"<!-- (?:IF BRIEFING_METHOD|IF SLACK|END (?:slack|imessage|email|file|SLACK)) -->")
DATE_LINK_RE = re.compile(r"^— \[\[(.+)\]\]$")
DAILY_NOTE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:-.+)?$")
SUMMARY_START_RE = re.compile(r"^<!-- HUMAN SUMMARY — AI: do not read, reference, or regenerate from this section -->$")
SUMMARY_LINE_RE = re.compile(r"^\*\*Summary \((\d{4}-\d{2}-\d{2})\):\*\* .+")
SUMMARY_END_RE = re.compile(r"^<!-- END HUMAN SUMMARY -->$")
MANIFEST_LINE_RE = re.compile(r"^(.+\.md)\|([0-9a-f]{32})$")
METADATA_LINE_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*)$")

ENTITY_FOLDERS = ("projects", "Other Entities", "events", "Medical", "places", "people")
FOLDERS_WITH_ENTRIES = ("projects", "Other Entities", "events")
SUMMARY_OPTIONAL_FOLDERS = ("projects", "Other Entities", "events", "Medical")

YAML_FRONTMATTER_FOLDERS = {"projects", "Other Entities", "events", "Medical"}

REQUIRED_METADATA: dict[str, tuple[str, ...]] = {
    "projects": ("**Priority:**", "**Aliases:**"),
    "Other Entities": ("**Priority:**", "**Aliases:**"),
    "events": ("**Priority:**", "**Aliases:**"),
    "Medical": (),
    "places": (),
}

ALLOWED_UNRESOLVED = {
    "CLAUDE",
}
ALLOWED_PRIORITIES = {"active", "background", "archive"}


@dataclass
class Finding:
    severity: str
    path: Path
    line: int
    message: str

    def render(self, root: Path) -> str:
        rel_path = self.path.relative_to(root)
        return f"{self.severity}: {rel_path}:{self.line}: {self.message}"


# Folders whose notes are organized in subdirectories — require recursive search.
# raw-daily-notes uses year/month subdirs; historical-notes uses year subdirs.
RECURSIVE_NOTE_FOLDERS = {"notes/raw-daily-notes", "notes/historical-notes"}


def iter_markdown_files(root: Path, folders: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for folder in folders:
        base = root / folder
        if not base.exists():
            continue
        if folder in RECURSIVE_NOTE_FOLDERS:
            files.extend(sorted(base.rglob("*.md")))
        else:
            files.extend(sorted(base.glob("*.md")))
    return files


def split_top_section(lines: list[str]) -> tuple[list[str], list[str]]:
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if (
            ENTRY_HEADER_RE.match(stripped)
            or SUMMARY_START_RE.match(stripped)
            or stripped == "---"
            or stripped.startswith(">")
        ):
            return lines[:idx], lines[idx:]
    return lines[:], []


def normalize_blank_lines(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    blank_pending = False
    for line in lines:
        if line.strip():
            if blank_pending and normalized:
                normalized.append("")
            normalized.append(line)
            blank_pending = False
        else:
            blank_pending = True
    return normalized


def fix_entity_file(path: Path, write: bool) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    original_lines = list(lines)
    folder = path.parent.name
    required = REQUIRED_METADATA.get(folder, ())

    if not lines:
        return False

    # Skip YAML frontmatter files — they don't need bold-markdown normalization
    if lines[0].strip() == "---":
        return False

    top_lines, rest_lines = split_top_section(lines)
    metadata_pairs: list[tuple[str, str]] = []
    other_top_lines: list[str] = []
    priority_value: str | None = None
    aliases_value: str | None = None

    for line in top_lines:
        stripped = line.strip()
        metadata_match = METADATA_LINE_RE.match(stripped)
        if metadata_match:
            label = metadata_match.group(1).strip()
            value = metadata_match.group(2).strip()
            if label == "Priority":
                if required:
                    priority_value = value.lower()
                else:
                    metadata_pairs.append((label, value.lower()))
                continue
            if label == "Aliases":
                if required:
                    aliases_value = value
                else:
                    metadata_pairs.append((label, value))
                continue
            metadata_pairs.append((label, value))
            continue
        other_top_lines.append(line)

    rebuilt_top: list[str] = []
    if required and priority_value is not None:
        rebuilt_top.append(f"**Priority:** {priority_value}")
    if required and aliases_value is not None:
        rebuilt_top.append(f"**Aliases:** {aliases_value}")

    if rebuilt_top and metadata_pairs:
        rebuilt_top.append("")

    rebuilt_top.extend(f"**{label}:** {value}".rstrip() for label, value in metadata_pairs)

    normalized_other = normalize_blank_lines(other_top_lines)
    if rebuilt_top and normalized_other:
        rebuilt_top.append("")
    rebuilt_top.extend(normalized_other)

    new_lines = rebuilt_top + rest_lines
    if new_lines != original_lines:
        if not write:
            return True
        new_text = "\n".join(new_lines)
        if original_lines or path.read_text(encoding="utf-8").endswith("\n"):
            new_text += "\n"
        path.write_text(new_text, encoding="utf-8")
        return True

    return False


def apply_fixes(root: Path, write: bool) -> list[Path]:
    changed: list[Path] = []
    for path in iter_markdown_files(root, ENTITY_FOLDERS):
        if fix_entity_file(path, write=write):
            changed.append(path)
    return changed


def collect_link_targets(root: Path) -> dict[str, Path]:
    targets: dict[str, Path] = {}

    for path in sorted(root.glob("*.md")):
        targets[path.stem.lower()] = path

    for folder in (*ENTITY_FOLDERS, "notes/raw-daily-notes", "notes/historical-notes", "notes/transcripts", "research"):
        for path in iter_markdown_files(root, (folder,)):
            targets[path.stem.lower()] = path

    return targets


def first_content_line(lines: list[str]) -> tuple[int, str] | None:
    for idx, line in enumerate(lines, start=1):
        if line.strip():
            return idx, line.strip()
    return None


def parse_yaml_priority_aliases(lines: list[str]) -> tuple[str | None, list[str], int]:
    """Extract priority and aliases from YAML frontmatter.
    Returns (priority, alias_list, aliases_line_no)."""
    if not lines or lines[0].strip() != "---":
        return None, [], 0

    priority = None
    alias_list: list[str] = []
    aliases_line = 0

    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            break
        stripped = line.strip()
        if stripped.startswith("priority:"):
            priority = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        elif stripped.startswith("aliases:"):
            aliases_line = i
            raw = stripped.split(":", 1)[1].strip()
            if raw.startswith("["):
                inner = raw.strip("[]")
                alias_list = [a.strip().strip('"').strip("'") for a in inner.split(",") if a.strip()]

    return priority, alias_list, aliases_line


def collect_entities(root: Path) -> tuple[dict[str, Path], dict[str, tuple[str, Path, int]], list[Finding]]:
    findings: list[Finding] = []
    entity_targets: dict[str, Path] = collect_link_targets(root)
    aliases: dict[str, tuple[str, Path, int]] = {}

    for path in iter_markdown_files(root, ENTITY_FOLDERS):
        lines = path.read_text(encoding="utf-8").splitlines()
        folder = path.parent.name
        has_yaml = lines and lines[0].strip() == "---"

        if folder in YAML_FRONTMATTER_FOLDERS:
            if not has_yaml:
                findings.append(
                    Finding("ERROR", path, 1, "entity file should use YAML frontmatter (starts with ---)")
                )
                continue

            priority, alias_list, alias_line_no = parse_yaml_priority_aliases(lines)

            if priority is None:
                findings.append(Finding("ERROR", path, 1, "YAML frontmatter missing 'priority' field"))
            elif priority.lower() not in ALLOWED_PRIORITIES:
                findings.append(
                    Finding("ERROR", path, 1, f"priority must be one of {sorted(ALLOWED_PRIORITIES)}, got {priority!r}")
                )

            # Register aliases
            for alias in alias_list:
                normalized = alias.lower()
                owner = (path.stem, path, alias_line_no)
                existing = aliases.get(normalized)
                if existing and existing[0] != path.stem:
                    findings.append(
                        Finding("ERROR", path, alias_line_no, f"duplicate alias {alias!r} already claimed by {existing[1].relative_to(root)}")
                    )
                else:
                    aliases[normalized] = owner

            # Implicit alias from filename
            implicit_name = path.stem.lower()
            owner = (path.stem, path, 1)
            existing = aliases.get(implicit_name)
            if existing and existing[0] != path.stem:
                findings.append(
                    Finding("ERROR", path, 1, f"entity filename alias {path.stem!r} conflicts with {existing[1].relative_to(root)}")
                )
            else:
                aliases[implicit_name] = owner

        elif folder == "people":
            # People use YAML frontmatter — handled by validate_people_profiles
            if has_yaml:
                _, alias_list, alias_line_no = parse_yaml_priority_aliases(lines)
                # People don't have priority in the same way, but register aliases
                # Read name from frontmatter for alias
                for i, line in enumerate(lines[1:], start=2):
                    if line.strip() == "---":
                        break
                    if line.strip().startswith("name:"):
                        name_val = line.split(":", 1)[1].strip().strip('"').strip("'")
                        if name_val and name_val.lower() != "null":
                            name_norm = name_val.lower()
                            existing = aliases.get(name_norm)
                            if not existing or existing[0] == path.stem:
                                aliases[name_norm] = (path.stem, path, i)
                        if line.strip().startswith("aliases:"):
                            raw = line.split(":", 1)[1].strip()
                            if raw.startswith("["):
                                inner = raw.strip("[]")
                                for a in [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]:
                                    norm = a.lower()
                                    existing = aliases.get(norm)
                                    if not existing or existing[0] == path.stem:
                                        aliases[norm] = (path.stem, path, i)

                # Register people aliases from their frontmatter
                for alias in alias_list:
                    normalized = alias.lower()
                    existing = aliases.get(normalized)
                    if not existing or existing[0] == path.stem:
                        aliases[normalized] = (path.stem, path, alias_line_no)

                # Implicit alias from filename
                implicit_name = path.stem.lower()
                existing = aliases.get(implicit_name)
                if not existing or existing[0] == path.stem:
                    aliases[implicit_name] = (path.stem, path, 1)

        else:
            # Legacy bold-markdown format for other folders
            required = REQUIRED_METADATA.get(folder, ())
            for position, expected in enumerate(required, start=1):
                line = lines[position - 1].strip() if len(lines) >= position else ""
                if not line.startswith(expected):
                    findings.append(
                        Finding("ERROR", path, max(position, 1), f"missing required metadata line starting with {expected!r}")
                    )

    return entity_targets, aliases, findings


def validate_links(root: Path, entity_targets: dict[str, Path]) -> list[Finding]:
    findings: list[Finding] = []
    markdown_files = iter_markdown_files(root, ENTITY_FOLDERS + ("notes/raw-daily-notes", "notes/historical-notes", "notes/transcripts"))
    daily_note_names = {path.stem.lower() for path in iter_markdown_files(root, ("notes/raw-daily-notes", "notes/historical-notes"))}

    for path in markdown_files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in WIKI_LINK_RE.finditer(line):
                target = match.group(1).strip()
                normalized_target = target.lower()
                if (
                    normalized_target in entity_targets
                    or normalized_target in daily_note_names
                    or DAILY_NOTE_RE.match(target)
                    or target in ALLOWED_UNRESOLVED
                ):
                    continue
                findings.append(Finding("ERROR", path, line_no, f"unresolved wiki link target {target!r}"))

    return findings


def validate_entry_blocks(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    for folder in FOLDERS_WITH_ENTRIES:
        for path in iter_markdown_files(root, (folder,)):
            lines = path.read_text(encoding="utf-8").splitlines()
            current_date: str | None = None
            blockquote_seen = False

            for line_no, line in enumerate(lines, start=1):
                stripped = line.strip()
                header_match = ENTRY_HEADER_RE.match(stripped)
                if header_match:
                    current_date = header_match.group(1)
                    blockquote_seen = False
                    continue

                if current_date is None:
                    continue

                if stripped.startswith(">"):
                    blockquote_seen = True
                    continue

                date_link = DATE_LINK_RE.match(stripped)
                if date_link:
                    link_target = date_link.group(1)
                    if not blockquote_seen:
                        findings.append(
                            Finding(
                                "ERROR",
                                path,
                                line_no,
                                f"entry for {current_date} is missing blockquoted content before date backlink",
                            )
                        )
                    if link_target != current_date and not link_target.startswith(f"{current_date}-"):
                        findings.append(
                            Finding(
                                "ERROR",
                                path,
                                line_no,
                                f"entry date {current_date} does not match backlink target {link_target}",
                            )
                        )
                    current_date = None
                    blockquote_seen = False
                    continue

                if stripped and not stripped.startswith("<!--"):
                    findings.append(
                        Finding(
                            "ERROR",
                            path,
                            line_no,
                            f"unexpected content inside entry for {current_date!r}; expected blockquotes or a date backlink",
                        )
                    )

            if current_date is not None:
                findings.append(
                    Finding(
                        "ERROR",
                        path,
                        len(lines) or 1,
                        f"entry for {current_date} is missing closing date backlink",
                    )
                )

    return findings


def validate_summary_blocks(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    for folder in SUMMARY_OPTIONAL_FOLDERS:
        for path in iter_markdown_files(root, (folder,)):
            lines = path.read_text(encoding="utf-8").splitlines()
            start_lines = [idx for idx, line in enumerate(lines, start=1) if SUMMARY_START_RE.match(line.strip())]
            end_lines = [idx for idx, line in enumerate(lines, start=1) if SUMMARY_END_RE.match(line.strip())]

            if not start_lines and not end_lines:
                continue

            if len(start_lines) != 1 or len(end_lines) != 1:
                findings.append(
                    Finding(
                        "ERROR",
                        path,
                        start_lines[0] if start_lines else (end_lines[0] if end_lines else 1),
                        "summary block must contain exactly one start marker and one end marker",
                    )
                )
                continue

            start_line = start_lines[0]
            end_line = end_lines[0]
            if end_line != start_line + 2:
                findings.append(
                    Finding(
                        "ERROR",
                        path,
                        start_line,
                        "summary block must be exactly three lines: start marker, summary line, end marker",
                    )
                )
                continue

            summary_line = lines[start_line].strip()
            if not SUMMARY_LINE_RE.match(summary_line):
                findings.append(
                    Finding(
                        "ERROR",
                        path,
                        start_line + 1,
                        "summary line must match '**Summary (YYYY-MM-DD):** ...'",
                    )
                )

    return findings


def validate_manifest(root: Path, fresh_install: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    manifest_path = root / "notes/.manifest"
    raw_notes_dir = root / "notes/raw-daily-notes"

    if not manifest_path.exists():
        if fresh_install:
            return findings
        findings.append(Finding("ERROR", manifest_path, 1, "manifest file is missing"))
        return findings

    if not raw_notes_dir.exists():
        findings.append(Finding("ERROR", raw_notes_dir, 1, "raw daily notes directory is missing"))
        return findings

    raw_note_names = {path.name for path in raw_notes_dir.rglob("*.md")}
    historical_notes_dir = root / "notes/historical-notes"
    historical_note_names = {path.name for path in historical_notes_dir.rglob("*.md")} if historical_notes_dir.exists() else set()
    all_note_names = raw_note_names | historical_note_names
    seen_manifest_names: set[str] = set()

    for line_no, raw_line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        match = MANIFEST_LINE_RE.match(line)
        if not match:
            findings.append(
                Finding(
                    "ERROR",
                    manifest_path,
                    line_no,
                    "manifest lines must match 'filename.md|md5hash'",
                )
            )
            continue

        filename = match.group(1)
        if filename in seen_manifest_names:
            findings.append(
                Finding(
                    "ERROR",
                    manifest_path,
                    line_no,
                    f"duplicate manifest entry for {filename!r}",
                )
            )
            continue

        seen_manifest_names.add(filename)
        if filename not in all_note_names:
            findings.append(
                Finding(
                    "ERROR",
                    manifest_path,
                    line_no,
                    f"manifest references missing note {filename!r}",
                )
            )

    if not fresh_install:
        for missing_name in sorted(raw_note_names - seen_manifest_names):
            findings.append(
                Finding(
                    "ERROR",
                    manifest_path,
                    1,
                    f"raw daily note {missing_name!r} is missing from manifest",
                )
            )

    return findings


def validate_event_metadata(root: Path) -> list[Finding]:
    findings: list[Finding] = []

    for path in iter_markdown_files(root, ("events",)):
        lines = path.read_text(encoding="utf-8").splitlines()

        if not lines or lines[0].strip() != "---":
            findings.append(Finding("ERROR", path, 1, "event files must use YAML frontmatter"))
            continue

        # Parse YAML frontmatter for required event fields
        required_fields = {"date": False, "location": False}
        for line in lines[1:]:
            if line.strip() == "---":
                break
            stripped = line.strip()
            for field in required_fields:
                if stripped.startswith(f"{field}:"):
                    value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                    if value and value != "null":
                        required_fields[field] = True

        for field, present in required_fields.items():
            if not present:
                findings.append(Finding("ERROR", path, 1, f"event YAML frontmatter missing required field: {field}"))

    return findings


PEOPLE_REQUIRED_FIELDS = {"name", "tier"}
PEOPLE_STANDARD_FIELDS = {"name", "aliases", "roles", "phone", "email", "location", "tier", "connection"}


def validate_people_profiles(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    people_dir = root / "people"
    if not people_dir.exists():
        return findings

    for path in sorted(people_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            findings.append(Finding("ERROR", path, 1, "people profile missing YAML frontmatter"))
            continue

        fields_found: set[str] = set()
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if re.match(r"^[a-z_]+:", line) and not line.startswith("  "):
                key = line.split(":")[0].strip()
                fields_found.add(key)

        for field in PEOPLE_REQUIRED_FIELDS:
            if field not in fields_found:
                findings.append(Finding("ERROR", path, 1, f"people profile missing required field: {field}"))

        for field in PEOPLE_STANDARD_FIELDS - PEOPLE_REQUIRED_FIELDS:
            if field not in fields_found:
                findings.append(Finding("WARN", path, 1, f"people profile missing standard field: {field}"))

    return findings


_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def validate_no_leftover_placeholders(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    check_files = [
        root / "CLAUDE.md",
        root / "OPEN BRAIN UPDATER.md",
    ]
    for path in check_files:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            # Strip inline-code spans before scanning. Prose that documents a
            # placeholder by example (e.g. `{{USER_FIRST_NAME}}`) is not a real
            # unfilled placeholder and shouldn't fail the build.
            scannable = _INLINE_CODE_RE.sub("", line)
            if UNFILLED_PLACEHOLDER_RE.search(scannable):
                findings.append(Finding("ERROR", path, line_no, "unfilled template placeholder found"))
            if CONDITIONAL_MARKER_RE.search(scannable):
                findings.append(Finding("ERROR", path, line_no, "leftover conditional marker from template"))
    return findings


def validate_entity_index_freshness(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    index_path = root / "entities-index.json"

    if not index_path.exists():
        findings.append(Finding("WARN", index_path, 1, "entity index not found — run: python3 scripts/build_entity_index.py"))
        return findings

    index_mtime = index_path.stat().st_mtime
    for path in iter_markdown_files(root, ENTITY_FOLDERS):
        if path.stat().st_mtime > index_mtime:
            findings.append(
                Finding(
                    "WARN",
                    index_path,
                    1,
                    f"entity index is stale — {path.relative_to(root)} was modified after last index build",
                )
            )
            break

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Open Brain vault structure.")
    parser.add_argument(
        "--root",
        default=".",
        help="Path to the vault root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply low-risk structural fixes before validating.",
    )
    parser.add_argument(
        "--check-fix",
        action="store_true",
        help="Preview which files would be changed by --fix without writing anything.",
    )
    parser.add_argument(
        "--fresh-install",
        action="store_true",
        help="Tolerate empty manifest and empty entity folders (fresh vault setup).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings: list[Finding] = []

    if args.fix and args.check_fix:
        print("Use either --fix or --check-fix, not both.", file=sys.stderr)
        return 2

    if args.fix:
        changed_paths = apply_fixes(root, write=True)
        if changed_paths:
            print("Applied low-risk fixes to:")
            for path in changed_paths:
                print(f"- {path.relative_to(root)}")
            print()
    elif args.check_fix:
        changed_paths = apply_fixes(root, write=False)
        if changed_paths:
            print("Low-risk fixes would be applied to:")
            for path in changed_paths:
                print(f"- {path.relative_to(root)}")
            print()
        else:
            print("No low-risk fixes needed.\n")

    entity_targets, _, metadata_findings = collect_entities(root)
    findings.extend(metadata_findings)
    findings.extend(validate_links(root, entity_targets))
    findings.extend(validate_entry_blocks(root))
    findings.extend(validate_summary_blocks(root))
    findings.extend(validate_manifest(root, fresh_install=args.fresh_install))
    findings.extend(validate_event_metadata(root))
    findings.extend(validate_people_profiles(root))
    findings.extend(validate_no_leftover_placeholders(root))
    findings.extend(validate_entity_index_freshness(root))

    findings.sort(key=lambda item: (item.path.as_posix(), item.line, item.message))

    if findings:
        for finding in findings:
            print(finding.render(root))
        error_count = sum(1 for finding in findings if finding.severity == "ERROR")
        if error_count:
            print(f"\nValidation failed with {error_count} error(s).", file=sys.stderr)
            return 1

    print("Open Brain validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
