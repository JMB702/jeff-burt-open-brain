---
name: open-brain-extract
description: "Extract all mentions of a specific idea, concept, project, or person from daily notes chronologically. Use when the user asks to pull together everything they've written about a topic, or when the main session needs full context on a specific subject before performing higher-level work. Triggers on phrases like 'extract everything about X', 'pull my notes on X', 'what have I written about X', 'gather context on X'."
user-invocable: true
---

# /open-brain-extract — Extract Topic Context from Daily Notes

You are extracting every mention of a specific topic from {{USER_FIRST_NAME}}'s notes in `notes/raw-daily-notes/` and `notes/historical-notes/`, assembling a chronological timeline that gives the main session complete context on that topic without the noise of everything else.

## Arguments

The user provides:
- **Topic** (required): The idea, concept, project, or person to extract. Examples: "Garden", "My Project", "Book", "first-last"
- **--since DATE** (optional): Only search notes from this date forward. Format: `YYYY-MM-DD`
- **--last Nd** (optional): Only search the last N days of notes. Example: `--last 30d`

If no date filter is provided, search ALL daily notes.

## Step 1: Build Search Terms

The user will refer to topics casually. Build a list of search variants before scanning notes.

For the given topic, generate aliases:
- The exact term as given
- Wiki link forms: `[[Topic]]`, `[[topic-slug|Topic]]`, `[[topic-slug]]`
- Common shorthand (e.g., "My Project" -> "the project", "project site")
- For people: both display name and slug (e.g., "Alex", "alex-kim", "Alex Kim", "[[alex-kim|Alex]]")

Present the search terms to the user briefly: "Searching for: [list]. Any other terms I should include?"

If the user says "no" or doesn't add any, proceed. If they add terms, incorporate them.

## Step 2: Fast Scan — Identify Relevant Files

Use grep to find which daily note files contain ANY of the search terms. This avoids reading every file in full.

```bash
grep -ril "term1\|term2\|term3" "notes/raw-daily-notes/" "notes/historical-notes/"
```

Sort results chronologically (filenames are date-based). Apply date filters if provided.

If no files match, report that and stop.

## Step 3: Check Existing Entity Files (Fast Path)

Before reading all raw notes, check if an entity file already exists for this topic:
- `projects/` — for project entities
- `Other Entities/` — for concept/topic entities
- `people/` — for person profiles

If an entity file exists, read it. It may already contain curated excerpts. Note any dates already covered — you can skip re-extracting those from raw notes unless the user wants a complete re-extraction.

Ask: "An entity file for [topic] already exists with entries through [latest date]. Want me to extract only newer mentions, or do a full re-extraction?"

If no entity file exists, proceed with full extraction.

## Step 4: Extract Mentions Chronologically

Process each matching daily note file **from oldest to newest**.

For each file:
1. Read the full file content
2. Find every paragraph/block that mentions the topic (using the search terms from Step 1)
3. Extract the **full paragraph** containing the mention — do not truncate or summarize
4. If two adjacent paragraphs both mention the topic, extract them as one block
5. If a paragraph mentions the topic intertwined with another subject, extract the whole paragraph anyway — do not try to surgically remove unrelated content
6. If the file contains no matches (false positive from grep), skip it

## Step 5: Assemble the Timeline

Format the output as a chronological timeline:

```markdown
# [Topic] — Extracted from Daily Notes

**Search terms used:** [list]
**Date range:** [earliest] to [latest]
**Notes scanned:** [count matching] of [total notes]

---

## YYYY-MM-DD
> [exact extracted paragraph(s)]

## YYYY-MM-DD
> [exact extracted paragraph(s)]

## YYYY-MM-DD
> [exact extracted paragraph(s)]
```

## Step 6: Deliver to Main Session

Present the assembled timeline to the user/main session. This is now the **working context** for whatever higher-level task follows.

After presenting, ask: "Here's everything you've written about [topic]. What would you like to do with this?"

## Rules

1. **Verbatim extraction only.** Copy {{USER_FIRST_NAME}}'s exact words. Never summarize, rephrase, or add AI commentary within the extracted blocks.
2. **Preserve wiki links.** Keep all `[[wiki links]]` as they appear in the source.
3. **Don't edit notes.** This skill is read-only on `notes/raw-daily-notes/` and `notes/historical-notes/`. Historical notes are retrospective — the filename date is when the event happened, not when it was written.
4. **Paragraph-level granularity.** Extract whole paragraphs, not sentences. A paragraph is text between blank lines.
5. **Skip empty matches.** If grep matched on a wiki link target but the surrounding paragraph isn't really about the topic, skip it. Use judgment.
6. **Report gaps.** If there's a long gap between mentions (e.g., 2 weeks+), note it: `*[No mentions from YYYY-MM-DD to YYYY-MM-DD]*`
7. **Context over precision.** When in doubt, include a paragraph rather than exclude it. The main session can filter; it can't recover what you didn't extract.
