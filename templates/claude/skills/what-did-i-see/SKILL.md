---
name: what-did-i-see
description: "Query {{USER_FIRST_NAME}}'s Apple Photos library for a specific date or date range. Triggers on phrases like 'what photos did I take on X', 'what did I see on X', 'show me my photos from X', 'what was I photographing on X'. Answers from metadata (GPS, albums, keywords, people, timestamps) by default. Only analyzes a photo's pixels when explicitly asked or when the user agrees it's necessary."
user-invocable: true
---

# /what-did-i-see — Query Apple Photos Metadata (and Pixels, Sparingly)

You are answering a question about what {{USER_FIRST_NAME}} photographed on a given date or date range, using the Photos library metadata cached at `Photos/photos-index.json`.

## Arguments

- **Date** (required): A single date (`YYYY-MM-DD`) or a range (`YYYY-MM-DD YYYY-MM-DD`). Natural-language dates ("yesterday", "last Tuesday", "March 15") must be resolved to `YYYY-MM-DD` before running the script — use today's date from the system context.
- **--summary** (optional): One-line-per-day output. Use this for ranges of more than 3 days.
- **--gps-only** (optional): Only include photos with GPS. Useful for location reconstruction.

## Step 1: Resolve the date

Convert whatever the user said into an ISO `YYYY-MM-DD`. If the user asks for a span ("last week", "March"), convert to explicit start/end dates. If the phrasing is ambiguous, ask for the exact date before running.

## Step 2: Run the metadata query

```bash
python3 scripts/photos_query.py <start> [<end>] [--summary] [--gps-only]
```

The script reads `Photos/photos-index.json` and returns per-photo metadata: UUID, timestamp, GPS, macOS Places name, albums, keywords, face-cluster persons, favorite/screenshot flags, original filename, dimensions.

If the script says `Photos/photos-index.json does not exist`, ask {{USER_FIRST_NAME}} to run `python3 scripts/photos_update_index.py` first. Do not fall back to `--live` without asking.

## Step 2b: For multi-photo dates, prefer the candidate ranker

If `photos_query.py` returns more than ~15 photos and the user's question is "show me / which ones / anything good," switch to `photos_candidates.py`. It uses Apple's own ML scoring (curation, overall, failure) plus the favorite flag, face-tag count, burst dedup, and temporal/GPS clustering to return a ranked shortlist instead of a firehose.

```bash
python3 scripts/photos_candidates.py <date> --top 5
python3 scripts/photos_candidates.py <date> --top 5 --explain   # show scoring breakdown
```

Use flags when the user's phrasing implies a filter:

- **Scene-type query** ("paddleboarding / beach / sunset / indoor / food") → `--labels "Water,Beach"` (or trust the unfiltered rank). Scene labels come from Apple's on-device ML. Check a couple of candidate photos' `scene_labels` in the index first if you're not sure which labels to pass.
- **Text search** ("find the receipt with / the sign that said / the whiteboard from") → `--text "substring"`. This reads Apple's pre-OCR'd `detected_text`, so no vision call is needed to find it.
- **Person** ("photos of Tom") → `--person "Tom"`. Substring match, smart-quote tolerant, so both "Tom" and `Tom "Ace" Crowley` work.
- **Location** ("photos at Siesta Key / the bay / Gulf") → `--location "Siesta"`. Matches bodies_of_water, venues, neighborhoods, and place_name.

Present the ranker's top 5 with a one-line summary each: time, place, why it ranked (favorite / high curation / people). The ranker narrows candidates — it does **not** override the Vision policy below. Opening a photo is still a separate, announced step.

**`detected_text` caveat:** Apple's OCR sometimes returns noisy fragments (e.g., texture lines read as numbers). If you cite detected_text to {{USER_FIRST_NAME}}, flag it as "OCR said X, would need to open the photo to verify."

## Step 3: Answer from metadata

The metadata answers most questions. Quote the times, places, albums, and people the script returned. **Do not fabricate image contents from filenames** — `IMG_1234.HEIC` tells you nothing about what's in the photo.

Treat face-cluster `persons` as Apple's best guess, not ground truth. If {{USER_FIRST_NAME}} asks "were there photos of Tom on Saturday," say "Photos' face clustering tagged N photos as Tom" — not "there are N photos of Tom."

Correlate with the daily note at `notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md`. If {{USER_FIRST_NAME}} wrote about that day, quote one or two relevant lines to add context.

## Vision policy — when to open a photo and read its pixels

Exporting a photo and reading it with Claude's multimodal vision is **token-heavy and slow**. The cached metadata already answers most questions. Use the rubric below in order.

### Step A — Can metadata alone answer this?

If yes, **stop**. Do not export. Answer from the script output. Examples that stop here:
- "Where was I on X" → GPS + timestamp.
- "How many photos on X" → count.
- "Show me photos from DEC Expo" → date + GPS + album match.
- "Did I take any photos at Rob's place" → date + GPS radius.
- "Photos with Tom" → face-cluster `persons` field.
- "Any favorites that week" → `favorite` flag.

### Step B — Did the user explicitly request pixel content?

If yes, analyze **the specific photo(s) named**. Trigger phrases:
- "What's in this photo" / "describe the photo" / "what do you see"
- "Read the text in" / "OCR this" / "what does the sign say" / "what does the receipt say"
- "Show me" followed by a specific UUID or singular photo reference
- "Look at [specific photo]"

Go to Step D for the mechanics.

### Step C — Would pixels resolve ambiguity that metadata left open?

If yes, **ask before escalating**. Propose a specific UUID. Don't batch.

Example: user asks "what happened that night" on a date with thin daily notes and a cluster of unlabeled photos. Show the metadata first, then offer:

> "There are 4 photos between 8–10pm with no album, place, or people tagged. Want me to open one of them to get more context? If so I'd start with `<uuid>`."

Only proceed to Step D after {{USER_FIRST_NAME}} confirms.

### Step D — Export and read the photo

Exactly one photo at a time. Announce before the tool call:

> "Opening `<uuid>` to check `<specific thing>`."

Then:

```bash
python3 scripts/photos_export.py <uuid>          # preview (~1 MB), usually enough
python3 scripts/photos_export.py <uuid> --size original   # full resolution, for OCR / fine detail
```

The script prints an absolute path. Use the `Read` tool on that path — it's an image, so Claude will see it.

After reading, describe what's in the photo factually. Don't invent context beyond what's visible.

### Step E — Bulk requests ("describe every photo from yesterday")

**Stop and negotiate.** Surface the cost and propose narrowing:

> "There are 47 photos from yesterday. Opening each one is a lot of context and time. Want to narrow by time window (e.g., 'the ones around dinner'), by album, or by a specific moment you want described?"

Never loop through >3 photos without explicit confirmation per batch.

### Hard limits

- **Default: zero vision calls.** Most turns should end without any `photos_export.py` invocation.
- **At most 1 photo per turn without asking.**
- **Never auto-analyze inside a list or summary.** Listings are metadata-only, always.
- **Announce before each vision call.** Give {{USER_FIRST_NAME}} a chance to interrupt.

### Not vision triggers (never auto-open)

- Location, date, time, or count queries.
- Listing or filtering by any metadata field.
- Daily-note enrichment.
- Anything phrased as "find / list / how many."

## Example flows

**Metadata-only — location reconstruction:**

```
User: Where was I on March 13?
You: [runs] python3 scripts/photos_query.py 2026-03-13 --gps-only
You: You took 6 photos that day — 4 near a park (around 2pm),
     2 at home (evening). No vision needed, GPS tells us.
```

**Metadata-only — listing:**

```
{{USER_FIRST_NAME}}: Show me my photos from last Saturday.
You: [runs] python3 scripts/photos_query.py 2026-04-12
You: [relays the 12 photos with time, UUID, place, albums]
     I'm stopping at the metadata — let me know if you want me to
     open a specific one.
```

**Explicit vision request:**

```
{{USER_FIRST_NAME}}: What does the whiteboard in the photo at 2:14 pm say?
You: Opening <uuid> to read the whiteboard.
     [runs] python3 scripts/photos_export.py <uuid>
     [uses Read on the exported file]
     The whiteboard shows: "Phase 1 / Phase 2 / ..." [faithful transcription]
```

**Ambiguity — ask first:**

```
{{USER_FIRST_NAME}}: What happened the night of April 10?
You: [runs] python3 scripts/photos_query.py 2026-04-10
     Your daily note that day is brief. There are 5 photos between
     7–11pm with no album, place, or people tagged — just timestamps.
     Want me to open one to get more context? I'd start with <uuid>
     (the earliest, 7:42pm).
```

**Bulk refused:**

```
{{USER_FIRST_NAME}}: Describe every photo from yesterday.
You: There are 47 photos from yesterday. Opening each one is heavy —
     want to narrow it down? Options: a time window, a specific album,
     or photos with no metadata (the ones most likely to be new context).
```

## Handle "no data"

- If the date has zero photos, say so plainly. Do not infer.
- If `photos-index.json` is missing, ask {{USER_FIRST_NAME}} to run `photos_update_index.py`.
- If the script warns the index is stale (>7 days), surface that warning in your response.

## Screenshots

Photos returned with `screenshot: true` are UI captures, not real-world photos. Note this in your answer so you don't imply {{USER_FIRST_NAME}} was "at" a location when the photo is a map screenshot.
