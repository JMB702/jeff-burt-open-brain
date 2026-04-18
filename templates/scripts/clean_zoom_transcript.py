#!/usr/bin/env python3
"""Clean a raw Zoom transcript copy-paste into a formatted transcript file.

Reads raw text (from --input or stdin) that looks like Zoom's copy-paste:

    Jordan Park - North Region10:13:57

    about where AI fits in and the different use cases at some point.

    Alex Kim10:13:59

    That would be… that would be fantastic.

Emits a formatted transcript with YAML frontmatter + one turn per speaker:

    **Jordan Park (North Region)** [10:13:57]
    about where AI fits in and the different use cases at some point.

    **[[alex-kim|Alex Kim]]** [10:13:59]
    That would be… that would be fantastic.

Speaker names that match an entry in `entities-index.json` (by slug or full name)
are wrapped as `[[slug|Display Name]]`. Unknown speakers stay as plain text.

Usage:
    # From a file:
    python3 scripts/clean_zoom_transcript.py \\
        --input raw.txt \\
        --title "AI Workgroup" \\
        --date 2026-04-17 \\
        --start-time 12:00 \\
        --entity "events/AI Workgroup 2026-04-17"

    # From stdin:
    pbpaste | python3 scripts/clean_zoom_transcript.py \\
        --title "AI Workgroup" --date 2026-04-17

The --entity flag, if given, appends a `## Transcript` line to that entity
file pointing at the new transcript. Also stores the entity slug in the
transcript's frontmatter as `related_events` / `related_projects` so the link
is bidirectional.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
INDEX_JSON = VAULT_ROOT / "entities-index.json"
TRANSCRIPTS_DIR = VAULT_ROOT / "notes" / "transcripts"

# Zoom's copy-paste puts the timestamp IMMEDIATELY after the name
# (no separator). Examples:
#   "Alex Kim10:13:59"
#   "Jordan Park - North Region10:14:07"
#   "Priya Patel10:14:14"
SPEAKER_LINE_RE = re.compile(r"^(.+?)(\d{1,2}:\d{2}:\d{2})\s*$")

# A parenthetical location/team appended to the speaker name, separated by
# dash or comma. Strip a trailing period ("Ops Team." → "Ops Team"). Examples:
#   "Jordan Park - North Region" → name "Jordan Park", suffix "North Region"
#   "Casey Lee, Ops Team." → name "Casey Lee", suffix "Ops Team"
NAME_WITH_SUFFIX_RE = re.compile(r"^(.+?)\s*[-–,]\s*(.+?)\.?$")


def load_people_index() -> dict[str, str]:
    """Return {lowercase_full_name: slug} for every person in the index."""
    if not INDEX_JSON.exists():
        return {}
    data = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    people: dict[str, str] = {}
    for entry in data.get("entities", {}).get("people", []):
        slug = entry["stem"]
        name = entry.get("name") or slug
        people[name.lower()] = slug
        people[slug.lower()] = slug
        for alias in entry.get("aliases", []):
            people[alias.lower()] = slug
    return people


def parse_raw(raw: str) -> list[tuple[str, str | None, str, str]]:
    """Split raw Zoom text into (speaker, suffix, timestamp, body) turns."""
    turns: list[tuple[str, str | None, str, list[str]]] = []
    current: tuple[str, str | None, str, list[str]] | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        m = SPEAKER_LINE_RE.match(stripped)
        if m:
            # New turn.
            if current is not None:
                turns.append(current)
            name_part = m.group(1).strip()
            timestamp = m.group(2)

            # Extract "(Suffix)" if present (e.g. "Jordan Park - North Region",
            # "Casey Lee, Ops Team.").
            suffix: str | None = None
            suffix_match = NAME_WITH_SUFFIX_RE.match(name_part)
            if suffix_match:
                name_part = suffix_match.group(1).strip()
                suffix = suffix_match.group(2).strip()

            current = (name_part, suffix, timestamp, [])
        else:
            # Body line for the current turn.
            if current is None:
                continue
            current[3].append(stripped)

    if current is not None:
        turns.append(current)

    return [(s, suf, ts, "\n\n".join(body).strip()) for s, suf, ts, body in turns]


def merge_consecutive(turns: list[tuple[str, str | None, str, str]]) -> list[tuple[str, str | None, str, str]]:
    """Merge consecutive turns by the same speaker (no other speaker between)."""
    out: list[tuple[str, str | None, str, str]] = []
    for turn in turns:
        if out and out[-1][0] == turn[0] and out[-1][1] == turn[1]:
            prev = out[-1]
            combined = (prev[3] + "\n\n" + turn[3]).strip()
            out[-1] = (prev[0], prev[1], prev[2], combined)
        else:
            out.append(turn)
    return out


def format_speaker(name: str, suffix: str | None, people: dict[str, str]) -> str:
    """Return the formatted speaker label, wiki-linked if we have a profile."""
    slug = people.get(name.lower())
    display = name
    if suffix:
        display = f"{name} ({suffix})"
    if slug:
        return f"**[[{slug}|{display}]]**"
    return f"**{display}**"


def slugify_person(name: str) -> str:
    """Best-guess slug for a speaker not yet in the people index (for attendees)."""
    cleaned = re.sub(r"[^A-Za-z0-9\s-]", "", name).strip().lower()
    return re.sub(r"\s+", "-", cleaned)


def build_attendee_list(
    turns: list[tuple[str, str | None, str, str]], people: dict[str, str]
) -> list[str]:
    seen: list[str] = []
    for name, _suffix, _ts, _body in turns:
        slug = people.get(name.lower()) or slugify_person(name)
        if slug and slug not in seen:
            seen.append(slug)
    return seen


def render_frontmatter(
    title: str,
    date: str,
    start_time: str | None,
    timezone: str | None,
    source: str,
    attendees: list[str],
    related_events: list[str],
    related_projects: list[str],
    related_people: list[str],
    meeting_url: str | None,
) -> str:
    def yaml_bare_list(xs: list[str]) -> str:
        if not xs:
            return "[]"
        return "[" + ", ".join(xs) + "]"

    def yaml_quoted_list(xs: list[str]) -> str:
        if not xs:
            return "[]"
        quoted = ['"' + x + '"' for x in xs]
        return "[" + ", ".join(quoted) + "]"

    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f'date: "{date}"')
    lines.append(f'start_time: "{start_time}"' if start_time else "start_time: null")
    lines.append(f'timezone: "{timezone}"' if timezone else "timezone: null")
    lines.append(f"source: {source}")
    lines.append(f"meeting_url: {meeting_url if meeting_url else 'null'}")
    lines.append(f"attendees: {yaml_bare_list(attendees)}")
    lines.append(f"related_events: {yaml_quoted_list(related_events)}")
    lines.append(f"related_projects: {yaml_quoted_list(related_projects)}")
    lines.append(f"related_people: {yaml_bare_list(related_people)}")
    lines.append("---")
    return "\n".join(lines)


def render_body(
    turns: list[tuple[str, str | None, str, str]], people: dict[str, str]
) -> str:
    parts: list[str] = []
    for name, suffix, ts, body in turns:
        header = format_speaker(name, suffix, people) + f" [{ts}]"
        parts.append(header + "\n" + body)
    return "\n\n".join(parts)


SUMMARY_SCAFFOLD = """
## Summary

<!-- Human-written. Fill in after the meeting. Cite timestamps like [HH:MM:SS] so
readers can jump to the moment. Template:

1–2 paragraph narrative of what happened.

### Key decisions
- ...

### Action items
- **Name** — what they committed to [HH:MM:SS]

### Notable moments
- [HH:MM:SS] brief label
-->

## Transcript

"""


def append_transcript_link_to_entity(entity_rel_path: str, transcript_stem: str) -> bool:
    """Add a `## Transcript` section (or line) to the entity file. Returns True if written."""
    entity_path = VAULT_ROOT / entity_rel_path
    if not entity_path.suffix:
        entity_path = entity_path.with_suffix(".md")
    if not entity_path.exists():
        sys.stderr.write(f"entity file not found: {entity_path}\n")
        return False

    text = entity_path.read_text(encoding="utf-8")
    link_line = f"[[{transcript_stem}]] — Zoom transcript"
    if link_line in text:
        return False  # already linked

    if "\n## Transcript\n" in text or text.startswith("## Transcript\n"):
        # Append under the existing heading.
        new_text = re.sub(
            r"(## Transcript\n)", r"\1- " + link_line + "\n", text, count=1
        )
    else:
        # Append a new section at the end.
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + "\n## Transcript\n- " + link_line + "\n"

    entity_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", help="Path to the raw Zoom text (default: stdin)")
    parser.add_argument("--title", required=True, help='Meeting title (e.g. "AI Workgroup")')
    parser.add_argument("--date", required=True, help="Meeting date (YYYY-MM-DD)")
    parser.add_argument("--start-time", default=None, help="HH:MM (24-hour, local)")
    parser.add_argument("--timezone", default="America/New_York")
    parser.add_argument("--source", default="zoom-ai-companion")
    parser.add_argument("--meeting-url", default=None)
    parser.add_argument(
        "--entity",
        action="append",
        default=[],
        help="Related entity (e.g. 'events/AI Workgroup 2026-04-17'). "
        "Repeat for multiple. Each entity's file gets a `## Transcript` link "
        "appended (or skipped if the link is already there).",
    )
    parser.add_argument("--output", default=None, help="Output path (default: notes/transcripts/<date> <title>.md)")
    parser.add_argument("--dry-run", action="store_true", help="Print the cleaned file to stdout, don't write.")
    args = parser.parse_args()

    # Read raw text.
    if args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        sys.stderr.write("no transcript input provided\n")
        return 1

    # Parse + merge.
    turns = parse_raw(raw)
    if not turns:
        sys.stderr.write("no speaker turns recognized — check input format\n")
        return 1
    turns = merge_consecutive(turns)

    # Look up speakers.
    people = load_people_index()
    attendees = build_attendee_list(turns, people)

    # Sort --entity by folder.
    related_events: list[str] = []
    related_projects: list[str] = []
    related_other: list[str] = []
    for ent in args.entity:
        ent_stem = Path(ent).stem
        if ent.startswith("events/"):
            related_events.append(ent_stem)
        elif ent.startswith("projects/"):
            related_projects.append(ent_stem)
        else:
            related_other.append(ent_stem)

    # Render.
    fm = render_frontmatter(
        title=args.title,
        date=args.date,
        start_time=args.start_time,
        timezone=args.timezone,
        source=args.source,
        attendees=attendees,
        related_events=related_events,
        related_projects=related_projects + related_other,
        related_people=[a for a in attendees if a in {p for p in people.values()}],
        meeting_url=args.meeting_url,
    )
    body = render_body(turns, people)
    content = fm + SUMMARY_SCAFFOLD + body + "\n"

    # Emit.
    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = VAULT_ROOT / out_path
    else:
        out_path = TRANSCRIPTS_DIR / f"{args.date} {args.title}.md"

    if args.dry_run:
        sys.stdout.write(content)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"wrote {out_path.relative_to(VAULT_ROOT)}")
        print(f"  turns: {len(turns)}")
        print(f"  attendees: {', '.join(attendees) if attendees else '(none)'}")

        # Link back from every named entity.
        for ent in args.entity:
            if append_transcript_link_to_entity(ent, out_path.stem):
                print(f"  linked from {ent}")

    # Flag speakers with no known slug.
    unknown = [
        t[0]
        for t in turns
        if t[0].lower() not in people and t[0].lower() not in {p.lower() for p in people.values()}
    ]
    if unknown:
        unique_unknown = sorted(set(unknown))
        sys.stderr.write(
            f"\nNote: speakers without people profiles: {', '.join(unique_unknown)}\n"
            "Create profiles in people/ if you want future transcripts to link them.\n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
