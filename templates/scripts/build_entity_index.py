#!/usr/bin/env python3
"""Build a static entity index from the Open Brain vault.

Generates:
  - entities-index.json  (machine-readable, for scripts and validation)
  - entities-index.md    (agent-readable, catted in the updater preflight)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

METADATA_LINE_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*)$")

INDEXED_FOLDERS: dict[str, str] = {
    "projects": "project",
    "Other Entities": "other",
    "events": "event",
    "Medical": "medical",
}

PEOPLE_FOLDER = "people"


def parse_entity_metadata(path: Path) -> dict:
    """Extract Priority and Aliases from an entity file.
    Handles both YAML frontmatter and legacy bold-markdown formats."""
    lines = path.read_text(encoding="utf-8").splitlines()
    priority = ""
    aliases: list[str] = []

    if lines and lines[0].strip() == "---":
        # YAML frontmatter
        for line in lines[1:]:
            if line.strip() == "---":
                break
            stripped = line.strip()
            if stripped.startswith("priority:"):
                priority = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            elif stripped.startswith("aliases:"):
                raw = stripped.split(":", 1)[1].strip()
                if raw.startswith("["):
                    inner = raw.strip("[]")
                    aliases = [a.strip().strip('"').strip("'") for a in inner.split(",") if a.strip()]
    else:
        # Legacy bold-markdown format
        for line in lines[:10]:
            m = METADATA_LINE_RE.match(line.strip())
            if not m:
                continue
            label = m.group(1).strip()
            value = m.group(2).strip()
            if label == "Priority":
                priority = value.lower()
            elif label == "Aliases":
                aliases = [a.strip() for a in value.split(",") if a.strip()]

    return {"priority": priority, "aliases": aliases}


def parse_person_metadata(path: Path) -> dict:
    """Extract name and aliases from a people profile's YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    name = path.stem
    aliases: list[str] = []

    if not lines or lines[0].strip() != "---":
        return {"name": name, "aliases": aliases}

    in_aliases = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            name = stripped[len("name:"):].strip().strip('"').strip("'")
        elif stripped.startswith("aliases:"):
            rest = stripped[len("aliases:"):].strip()
            if rest.startswith("["):
                # Inline list: [alias1, alias2]
                inner = rest.strip("[]")
                aliases = [a.strip().strip('"').strip("'") for a in inner.split(",") if a.strip()]
            elif not rest:
                in_aliases = True
            continue
        elif in_aliases:
            if stripped.startswith("- "):
                aliases.append(stripped[2:].strip().strip('"').strip("'"))
            else:
                in_aliases = False

    return {"name": name, "aliases": aliases}


def build_index(root: Path) -> dict:
    entities_by_type: dict[str, list[dict]] = {}
    alias_map: dict[str, dict] = {}

    # Process entity folders (projects, Other Entities, events, Medical)
    for folder, entity_type in INDEXED_FOLDERS.items():
        folder_path = root / folder
        if not folder_path.exists():
            continue

        entries = []
        for path in sorted(folder_path.glob("*.md")):
            meta = parse_entity_metadata(path)
            stem = path.stem
            rel_path = str(path.relative_to(root))

            entry = {
                "filename": path.name,
                "stem": stem,
                "priority": meta["priority"],
                "aliases": meta["aliases"],
                "path": rel_path,
            }
            entries.append(entry)

            # Implicit alias: filename stem
            alias_map[stem.lower()] = {
                "entity": stem,
                "type": entity_type,
                "path": rel_path,
            }
            # Explicit aliases
            for alias in meta["aliases"]:
                alias_map[alias.lower()] = {
                    "entity": stem,
                    "type": entity_type,
                    "path": rel_path,
                }

        entities_by_type[entity_type] = entries

    # Process people
    people_path = root / PEOPLE_FOLDER
    if people_path.exists():
        entries = []
        for path in sorted(people_path.glob("*.md")):
            meta = parse_person_metadata(path)
            stem = path.stem
            rel_path = str(path.relative_to(root))

            entry = {
                "filename": path.name,
                "stem": stem,
                "name": meta["name"],
                "aliases": meta["aliases"],
                "path": rel_path,
            }
            entries.append(entry)

            # Implicit alias: filename stem
            alias_map[stem.lower()] = {
                "entity": stem,
                "type": "person",
                "path": rel_path,
            }
            # Explicit aliases
            for alias in meta["aliases"]:
                normalized = alias.lower()
                if normalized and normalized not in alias_map:
                    alias_map[normalized] = {
                        "entity": stem,
                        "type": "person",
                        "path": rel_path,
                    }

        entities_by_type["people"] = entries

    return {
        "entities": entities_by_type,
        "alias_map": alias_map,
    }


def write_json(index: dict, path: Path) -> None:
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(index: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append("<!-- Auto-generated by scripts/build_entity_index.py — do not edit -->")
    lines.append("")

    type_labels = {
        "project": "Projects",
        "other": "Other Entities",
        "event": "Events",
        "medical": "Medical",
        "people": "People",
    }

    for type_key, label in type_labels.items():
        entries = index["entities"].get(type_key, [])
        if not entries:
            continue

        lines.append(f"## {label}")
        lines.append("")

        if type_key == "people":
            lines.append("| Person | Slug | Aliases |")
            lines.append("|--------|------|---------|")
            for e in entries:
                aliases_str = ", ".join(e["aliases"]) if e["aliases"] else ""
                lines.append(f"| {e['name']} | {e['stem']} | {aliases_str} |")
        else:
            lines.append("| Entity | Priority | Aliases |")
            lines.append("|--------|----------|---------|")
            for e in entries:
                aliases_str = ", ".join(e["aliases"]) if e["aliases"] else ""
                lines.append(f"| {e['stem']} | {e['priority']} | {aliases_str} |")

        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    index = build_index(root)

    json_path = root / "entities-index.json"
    md_path = root / "entities-index.md"

    write_json(index, json_path)
    write_markdown(index, md_path)

    entity_count = sum(len(v) for v in index["entities"].values())
    alias_count = len(index["alias_map"])
    print(f"Entity index built: {entity_count} entities, {alias_count} aliases")
    print(f"  -> {json_path.relative_to(root)}")
    print(f"  -> {md_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
