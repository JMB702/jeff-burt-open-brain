---
name: photos-for-event
description: "Find photos in Jeff's Apple Photos library that match an Open Brain entity (event, project, or other entity) by date — and by GPS radius when coordinates are supplied. Triggers on phrases like 'photos from the X event', 'any pictures from X', 'photos of X project', 'find photos tied to X'. Metadata-only by default; defers to the Vision policy for any pixel analysis."
user-invocable: true
---

# /photos-for-event — Match Photos to Entities by Date (and Optionally GPS)

You are finding which photos in Jeff's library relate to a specific Open Brain entity — an event, project, medical condition, or other entity file. This is a **metadata-only** skill by default.

## Step 1: Resolve the entity

The user will name the entity informally ("the April AI workgroup," "DEC Expo," "Rob's Intake System"). Resolve it to a file path:

1. Read `entities-index.md` to find the entity. Aliases are listed there.
2. Pick the matching path:
   - Events → `events/<Name>.md`
   - Projects → `projects/<Name>.md`
   - Other Entities → `Other Entities/<Name>.md`
   - Medical → `Medical/<Name>.md`

If the entity name is ambiguous, ask which one Jeff means before continuing.

## Step 2: Run the resolver

```bash
python3 scripts/photos_for_entity.py "<entity-file.md>" [--date-fuzz-days N] [--json]
```

The script reads the entity's YAML frontmatter. Behavior:

- **Events:** uses the `date` field, padded by `--date-fuzz-days` (default 1) on each side. So an event on 2026-04-18 returns photos from 2026-04-17 through 2026-04-19.
- **Projects / Other / Medical:** uses `first_mention` and `last_entry_date` to form the window, padded by fuzz days. For long-running projects this can be months of photos — prefer `--summary` in a follow-up query, or ask Jeff for a narrower date range.

Entity `location` is free text (e.g., "Zoom", "Tampa, FL") and doesn't carry lat/lng. If Jeff has specific GPS coordinates in mind — or the entity happened at a known place — pass `--lat`, `--lng`, and `--radius-km` to the script for a tighter filter. Without those, matching is date-only.

## Step 3: Present candidates from metadata

Report the photos the script returned. Each line will have UUID, timestamp, GPS, macOS Places name, albums, face-cluster persons, filename. That is almost always enough to answer "did Jeff take photos at this event."

Do **not** invent what's in the photos from filenames. `IMG_2041.HEIC` at the right time and place is a **candidate** for the event — not proof Jeff photographed the event itself. Say "3 candidate photos match the date and location" rather than "3 photos from the event."

Also correlate with:
- The entity file's own verbatim paragraph entries (`## YYYY-MM-DD` sections).
- Any `## Transcript` link at the bottom of the entity.
- The daily note(s) covering the date window.

## Step 3b: Narrow large windows with the candidate ranker

If the script returns more than ~15 candidates (common for long-running projects or multi-day events), run the date range through `photos_candidates.py` to get a ranked shortlist using Apple's ML signals. Use the entity's `date` (for events) or `first_mention`/`last_entry_date` (for projects) as the window:

```bash
python3 scripts/photos_candidates.py <start> <end> --top 5
python3 scripts/photos_candidates.py <start> <end> --person "Tom" --top 5
python3 scripts/photos_candidates.py <start> <end> --location "Siesta" --top 5
```

Present the ranked set instead of the full candidate list. See `.claude/skills/what-did-i-see/SKILL.md` for full flag semantics.

## Step 4: Defer to the Vision policy for pixels

Opening a photo's pixels is **expensive and slow** — and is the job of `/what-did-i-see`, not this skill. The full rubric lives in `.claude/skills/what-did-i-see/SKILL.md`. Short version:

- **Default:** metadata only. No `photos_export.py` calls.
- **If Jeff asks to verify a specific candidate** ("is the whiteboard in `<uuid>` from the orientation meeting?"): announce the UUID, run `photos_export.py`, Read the result. One photo.
- **If Jeff asks to verify many candidates at once:** refuse to batch. Propose one to start with.
- **If no photo with pixel content is requested:** stop at metadata.

## Example flows

**Event with clear date match:**

```
Jeff: Any photos from the AI Workgroup on the 18th?
You: [reads entities-index.md, finds events/AI Workgroup 2026-04-18.md]
     [runs] python3 scripts/photos_for_entity.py "events/AI Workgroup 2026-04-18.md"
You: 2 candidates match 2026-04-17 through 2026-04-19:
     - 2026-04-18 1:15 PM  <uuid1>  (no GPS — likely indoors)  — IMG_2044.HEIC
     - 2026-04-18 2:48 PM  <uuid2>  (27.3804, -82.5246)  Home — IMG_2045.HEIC
     Note: the meeting was on Zoom, so photos from that day are probably not *of*
     the meeting. Want me to open one to confirm?
```

**Long-running project — narrow first:**

```
Jeff: Find all the photos tied to the Garden project.
You: [reads entities-index.md → Other Entities/Garden.md]
     The Garden entity spans 2025-09-10 → 2026-04-12. That's hundreds of
     candidate photos. Want me to:
       1. Run the full range (metadata only, no pixel analysis)
       2. Narrow to a specific month or week
       3. Pass GPS coords of the yard (27.3804, -82.5246) and a small radius
```

**Explicit pixel verification (edge into vision policy):**

```
Jeff: Is the whiteboard in <uuid> from the orientation?
You: Opening <uuid> to check.
     [runs] python3 scripts/photos_export.py <uuid>
     [reads the exported file]
     The whiteboard shows "Phase 1 / Phase 2 / ..." — this lines up with
     the orientation agenda.
```

## Handle "no candidates"

- If the script returns zero matches, say so plainly. Suggest widening `--date-fuzz-days` or checking whether photos were taken on a different device.
- If `photos-index.json` is missing, ask Jeff to run `python3 scripts/photos_update_index.py`.
- If the entity has no date fields (`date`, `first_mention`, `last_entry_date`), the resolver errors out. Tell Jeff which field is missing and suggest adding it to the frontmatter.
