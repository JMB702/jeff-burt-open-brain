# Open Brain Updater

**Canonical entry point:**

```bash
sh scripts/run_open_brain_updater.sh
```

This wrapper runs validation first, then prints the full updater instruction bundle.

## Purpose

Deliver a briefing focused on:
1. **Trends & insights** — how entities are evolving, what's progressing, what's stalling, what connects
2. **Dormant entities** — what's gone quiet that shouldn't have

**Complete every step. Do not skip or abbreviate. If a step produces nothing, say so explicitly — do not silently omit it.**

---

## Step 1: Orient

Run `date`. Adjust tone:
- Before noon → morning briefing
- Noon–5pm → midday refresh
- After 5pm → evening update
- Weekends → lighter tone

---

## Step 2: Read Daily Notes

If `notes/raw-daily-notes/` is empty (no notes exist yet), skip to Step 5 and deliver a short message: "No daily notes found yet. Create your first note at notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md and write freely. The updater will process it on the next run."

The preflight bundle already lists notes needing processing under `--- NOTES NEEDING PROCESSING ---`. That list is the source of truth — you do not need to md5 files yourself or walk the manifest by hand. If the list is empty, skip to Step 3.

If you want the pending list in JSON form while reasoning about edits:
```bash
python3 scripts/notes_to_process.py --json
```

For each note needing processing, start with the dry-run ingestion report:
```bash
python3 scripts/process_note.py notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md
```

For historical notes, pass the historical note path instead. The report is a deterministic checklist for Claude Code: paragraph indexes, direct entity/person alias matches, likely entity appends, duplicate warnings, unmatched paragraphs, manifest status, and a preview of the `tmp/run-delta.json` shape. It is **dry-run only** and does not edit the vault. Claude Code still owns the reasoning and final writes: indirect references, new aliases/entities, wiki links, verbatim appends, people profile updates, manifest updates, summaries, Slack briefing, and commits.

If you want the report in JSON, use:
```bash
python3 scripts/process_note.py notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md --json
```

When reprocessing a modified note, read the entity files that already have entries for that date and compare against the current note content. **Think through what's new vs. what was already captured** — only append genuinely new paragraphs, don't duplicate content from a prior run. {{USER_FIRST_NAME}} often adds to a note throughout the day, so the new content is typically at the end.

After processing a note, update `notes/.manifest` with the current MD5 hash (replace the old line or add a new one). Historical notes may be organized in year subdirectories (`notes/historical-notes/YYYY/YYYY-MM-DD.md`) but the manifest stores them by basename only — same as daily notes.

### 2a. Load Entity Inventory

The preflight script prints `entities-index.md` in the updater context bundle. This file contains:
- Every entity (projects, other entities, events, medical, people) with its priority and aliases
- A flat alias lookup table: alias → entity name and type

Use this as your matching checklist. Every paragraph in every daily note must be matched against both filenames and aliases in the index. Do not rely on memory or recognition — use the map.

If the index was not printed in the preflight (e.g., running manually), regenerate it:
```bash
python3 scripts/build_entity_index.py
```
Then read `entities-index.md`.

If you create a new entity during this run, add it to your working alias map immediately — the index file will be regenerated at the next validation step (2f).

### 2b. Process Each Note Paragraph-by-Paragraph

For each note needing processing, start from the `process_note.py` report. It already uses the same direct alias matcher as `match_entities.py`, checks likely duplicate appends, and highlights unmatched paragraphs for review.

If you need the raw per-paragraph alias shortlist without the extra manifest/duplicate/run-delta context, run:
```bash
python3 scripts/match_entities.py notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md --pretty
```
Both scripts are **advisory** — the regex catches direct and alias matches only, not indirect references. Still read every paragraph.

Then work through the note **one paragraph at a time**. For each paragraph:

1. **Start from the report.** Every candidate in `candidate_entities` and `candidate_people` is a confirmed direct/alias match — those will usually become wiki links and entity appends unless Claude Code identifies a false-positive alias match or duplicate.
2. **Then reason about what the shortlist missed.** Don't skim — {{USER_FIRST_NAME}} often buries entity references in the middle or end of a paragraph. Specifically look for:
   - **Indirect references** — {{USER_FIRST_NAME}} describes working on something without naming it. The pre-matcher cannot catch these.
   - **Medical references** without the condition name (e.g., medication or equipment names → the relevant Medical file).
   - **New aliases** — if the paragraph names the entity in a new way, add that phrasing to its `aliases` frontmatter so the pre-matcher catches it next run.
3. Copy the paragraph verbatim to every matching entity file. A single paragraph can belong to multiple entities.
4. If the paragraph mentions a person, update their people profile.
5. If the paragraph doesn't match ANY existing entity or alias, flag it — see step 2c.

Pull every paragraph that mentions each entity, verbatim and complete. Do not summarize, paraphrase, or truncate {{USER_FIRST_NAME}}'s words. If two adjacent paragraphs both mention the entity, include both.

### 2c. Handle Unmatched Paragraphs

After processing all paragraphs, review any that didn't match an existing entity. **For each unmatched paragraph, reason through these questions:**

1. **Is this a situation {{USER_FIRST_NAME}} is likely to mention again?** If yes (e.g., a new hobby, a recurring life theme), create a new entity file in the appropriate folder (`projects/`, `Other Entities/`, or `events/`). Include a Priority and Aliases field.
2. **Does it belong on a person's profile?** Even if it doesn't map to a named entity, it may describe something about a person {{USER_FIRST_NAME}} knows.
3. **Could it be an indirect reference to an existing entity that the alias map didn't catch?** Re-read the paragraph and consider whether it's talking about something already tracked under a different name. If so, add the new phrasing to that entity's Aliases field.
4. **Is it genuinely a one-off?** Skip it — but this should be rare. Most paragraphs connect to something.

### 2d. Write to Entity Files

After matching:
- Add `[[wiki links]]` to the daily note for every mention of an entity or person — not just the first. When using an alias, preserve {{USER_FIRST_NAME}}'s wording as display text: `[[Entity Name|alias used]]`.
- Write verbatim paragraphs to project entities (`projects/`) and other entities (`Other Entities/`)
- Create or update event entities in `events/` when daily notes mention attending or planning to attend an event. Event entities have extended YAML frontmatter (`date`, `time`, `location`, `status`) followed by verbatim daily note paragraphs.
- Append verbatim paragraphs to medical entities in `Medical/` when daily notes mention health conditions, medications, symptoms, or medical events. Update metadata tables if new medical information is mentioned (e.g., new trigger identified, medication change).
- **Update `last_entry_date` in the entity's YAML frontmatter** every time you append a paragraph. Set it to the note's date (for daily notes) or the event date from the historical note filename (for historical notes). The field is the source of truth for the dormancy check in Step 3b.
- Update people profiles with new information
- Update `notes/.manifest` with the current hash for each processed note (add new entries or replace stale hashes). Compute with `md5 -q <filepath>` (macOS) or `md5sum <filepath>` (Linux).
- **Historical notes:** Process files in `notes/historical-notes/` the same way as daily notes, but flag entries as historical when appending to entity files. The filename date is when the event happened; the written date comes from the file's filesystem creation date (`stat -f %SB` on macOS). Use this format in entity files:
  ```
  ## YYYY-MM-DD (historical — written YYYY-MM-DD)
  > [full paragraph from historical note, verbatim]
  — [[YYYY-MM-DD]] *(historical note, written [[YYYY-MM-DD]])*
  ```
- **Summaries — regenerate incrementally, not from full history.** For each entity that received new content this run, rewrite the summary block **using only the paragraphs appended this run plus the 3 most recent prior entries** (read the tail of the entity file, not the whole thing). Do not read the previous summary. The goal is 1–3 sentences covering: current state, last activity, next step if obvious. Format:
  ```
  <!-- HUMAN SUMMARY — AI: do not read, reference, or regenerate from this section -->
  **Summary (YYYY-MM-DD):** [1-3 sentences]
  <!-- END HUMAN SUMMARY -->
  ```
- **Emit `tmp/run-delta.json`** listing everything touched this run. Step 3 reads this instead of re-opening every entity file. Format:
  ```json
  {
    "run_date": "YYYY-MM-DD",
    "entities": [
      {"name": "Entity Name", "path": "projects/Entity Name.md", "appended_dates": ["YYYY-MM-DD"], "new_paragraphs": 2}
    ],
    "people": ["slug-one", "slug-two"],
    "notes_processed": ["YYYY-MM-DD.md"]
  }
  ```
  Create `tmp/` if it doesn't exist — it's gitignored.

### 2e. Verify — No Paragraph Left Behind

After all writes are complete, do a final check. **Re-read the daily note from top to bottom one more time.** For each paragraph, confirm it either:
- Was written to at least one entity file, OR
- Was explicitly skipped as a one-off with no entity relevance

This is the safety net. The most common failure mode is a paragraph that mentions an entity in passing — a single sentence at the end, or an informal reference the alias map didn't catch. Read slowly. If any paragraph was missed, go back and process it now. Do not proceed to Step 3 until every paragraph is accounted for.

### 2f. Validate Vault Structure

After all writes in Step 2 are complete, run the validator from the vault root:

```bash
sh scripts/run_open_brain_checks.sh
```

If validation fails:
- Read every reported error carefully
- Fix the vault structure issues before continuing
- Re-run the validator until it passes cleanly

If the failures are low-risk formatting or metadata-order issues only, you may preview the automatic fixes first:

```bash
sh scripts/run_open_brain_checks.sh --check-fix
```

If that preview looks appropriate, apply them:

```bash
sh scripts/run_open_brain_checks.sh --fix
```

Do not proceed to Step 3 until validation passes.

<!-- IF PHOTOS_INTEGRATION -->
### 2g. Refresh the Photos Metadata Cache

After validation, refresh the Apple Photos metadata cache so entity/date queries from future sessions read fresh data:

```bash
python3 scripts/photos_update_index.py
```

This rewrites `Photos/photos-index.json` (gitignored). It has no effect on the briefing itself — it's infrastructure.

**Do not block the updater on failure.** If the script reports osxphotos isn't installed or Full Disk Access isn't granted, log the error output and proceed to Step 3.

**But surface it in the briefing.** The preflight emits a `!!! PHOTOS PIPELINE WARNING !!!` block at the top of the bundle when osxphotos is missing or the index is stale (>36h old). If you saw that block at the start of this run, OR if the Step 2h refresh failed, include a one-line entry in the Slack briefing under a "System health" note (e.g., "Photos pipeline: osxphotos not importable — index has not refreshed since {generated_at}. Fix with `pip3 install osxphotos --break-system-packages`."). Do not let this sit silently across runs.
<!-- END PHOTOS_INTEGRATION -->

### 2i. Reconcile Auto-Memory Against Open Brain

Claude Code maintains per-project auto-memory files under:
```
~/.claude/projects/<slugified-vault-path>/memory/
```
(The slug is the absolute vault path with `/` replaced by `-`, e.g. `-Users-name-Documents-Open-Brain`.)

These memories are point-in-time observations Claude has written about {{USER_FIRST_NAME}}, projects, and preferences. They drift — a project that's been abandoned may still be memorialized as "active," a roadmap from weeks ago may list items that are now done or pivoted away from. **Open Brain — {{USER_FIRST_NAME}}'s daily notes and entity files — is the source of truth. Auto-memory takes a back seat to it.**

Do the following:

1. **Read the index.** Open `memory/MEMORY.md` and list every memory file it points to. Also list any `.md` files in the memory directory that aren't referenced in the index (orphans).
2. **For each memory file, read it and identify the topic(s) it claims to describe** — e.g., a specific project, a person, a policy, a tool, a decision. Note any concrete claims with a date or status ("shelved," "in progress," "done," file paths, expiration dates, etc.).
3. **Check Open Brain for the latest ground truth on each topic:**
   - Use `entities-index.md` to resolve the topic to an entity file.
   - Read the entity file's tail (recent entries + summary block). If the memory's claim contradicts a more recent entry, Open Brain wins.
   - For policies / preferences / feedback-type memories, cross-check against the current `CLAUDE.md` and `OPEN BRAIN UPDATER.md`. If the policy has been codified in those files, the memory is redundant.
   - If the topic isn't tracked as an entity at all, the memory may be genuinely useful auxiliary context — leave it alone unless daily notes clearly contradict it.
4. **Take action based on confidence:**
   - **Update** a memory when Open Brain provides a clear, specific correction (e.g., "shelved" → "abandoned," status flag change, new expiration date, outdated file path).
   - **Delete** a memory when it's fully superseded by Open Brain content, duplicated by `CLAUDE.md`, or describes infrastructure/decisions that have been explicitly abandoned in daily notes.
   - **Skip and flag** when the contradiction is ambiguous — include a one-line note in the Step 5 briefing under a "Memory drift" section so {{USER_FIRST_NAME}} can decide.
   - **Add** a new memory only when daily notes reveal a durable preference, feedback, or project-state fact that belongs in auto-memory and isn't already captured. Be conservative — most content belongs in entity files, not auto-memory.
5. **Keep `MEMORY.md` in sync** with any file deletions/additions. Remove orphaned index lines; add lines for new memories. Each index line stays under ~150 characters.
6. **Do not invent.** If Open Brain doesn't say something, don't write it into memory. The no-hallucination rule applies here too.

Budget this step to a light sweep on normal runs. A full audit of every memory file against every entity is expensive — prioritize memories whose topic appears in today's (or this run's) newly-processed daily notes, plus any memory that's older than ~14 days and hasn't been checked in a while.

---

## Step 3: Trends & Insights

This is the core of the briefing. The goal is to connect things and help {{USER_FIRST_NAME}} track ideas and thoughts over time.

Start from `tmp/run-delta.json` (written in Step 2d). It lists exactly which entities received new content. For each entity in the delta, read **only the tail** of that entity file — the summary block plus the last ~5 entries is usually enough. You do not need to open entities that weren't touched this run.

For each entity, analyze:
- **Progress:** What changed since the last entry? Is {{USER_FIRST_NAME}} advancing, stalling, or pivoting?
- **Blockers:** What's stuck? What's {{USER_FIRST_NAME}} waiting on or avoiding?
- **Next step:** What did {{USER_FIRST_NAME}} say they'd do next, in their own words?
- **Connections:** Does today's activity on one entity relate to or affect another?
- **Patterns:** Are there recurring themes in when/how {{USER_FIRST_NAME}} engages with this?

Write each trend as a short insight — not a status report. Lead with the observation, support it with specific dates/quotes from the entity, and end with a concrete suggestion if one is warranted.

Aim for 3–6 insights total across all active entities. Quality over quantity — skip entities where nothing meaningful has changed.

**Do not re-read raw daily notes for trend analysis.** Entity files are the pre-indexed source. Raw notes are only read once (in Step 2, for new/unprocessed notes).

---

## Step 3b: Dormant Entity Check

The preflight bundle already includes the dormant list under `--- DORMANT ENTITIES ---` — that is the authoritative source. If you want it in JSON (e.g., to reason programmatically), rerun:
```bash
python3 scripts/list_dormant.py --json
```

The script uses each entity's `last_entry_date` frontmatter field and applies these thresholds:

| Entity Type    | active       | background   | archive |
|----------------|--------------|--------------|---------|
| Projects       | > 7 days     | > 14 days    | never   |
| Other Entities | > 14 days    | > 28 days    | never   |
| Events         | upcoming within 7d and not mentioned | same | never   |
| Medical        | never (surfaces only when mentioned) | — | —       |

For each dormant entity, read its human summary block and include entity name, days since last mention, and last known status in the briefing. Within each tier, prioritize entities that were recently active and then went silent over those that are rarely mentioned at all.

**Do not use file modification dates** — any `--fix` run or manual edit touches mtime without being a real update. `last_entry_date` is the truth.

---

## Step 4: Self-Check

Before sending, verify:
- Does every insight reference specific entity entries with dates?
- Is every next step in {{USER_FIRST_NAME}}'s own words (not AI-generated advice)?
- Are cross-entity connections surfaced where they exist?
- If the trends section feels thin or generic, go back and dig deeper into the entity files.
- Re-run `sh scripts/run_open_brain_checks.sh` if you made any file edits after Step 2f

---

## Step 5: Deliver Briefing

<!-- IF BRIEFING_METHOD = slack -->
### Slack Delivery

Channel: `#briefing` ({{SLACK_CHANNEL_ID}})

**The briefing contains answers and observations — not checklists or homework.**

Split into multiple messages if over ~3000 characters.

**Slack formatting:**
- Links: `<https://example.com|Display Text>`
- Bold: `**text**` (double asterisks) — the Slack MCP tool converts single `*text*` to italic. Use `**text**` for ALL headers, section titles, and any text that should be bold.
- Bullet lists only — no tables
- Short lines for mobile reading
- **Blank lines:** The Slack API strips empty lines. To create visual spacing, put `&#x200B;` (a zero-width space HTML entity) on its own line wherever you want a blank line. Place one before and after every section header and between each insight.

```
**Open Brain — [Day] [Date]**
———————————————————
&#x200B;
**Trends & Insights**
&#x200B;
**1. First insight title.**
Insight body text.
&#x200B;
**2. Second insight title.**
Insight body text.
&#x200B;
———————————————————
&#x200B;
**Dormant Entities**
&#x200B;
[Entities not mentioned recently, with last known status. Or "None — all entities active."]
```
<!-- END slack -->

<!-- IF BRIEFING_METHOD = imessage -->
### iMessage Delivery

Send the briefing to `{{IMESSAGE_RECIPIENT}}` via iMessage.

**The briefing contains answers and observations — not checklists or homework.**

Keep messages concise — iMessage doesn't render markdown. Use plain text with line breaks. Split into multiple messages if over ~1500 characters.

```
Open Brain — [Day] [Date]
———————————————————

TRENDS & INSIGHTS

1. First insight title.
Insight body text.

2. Second insight title.
Insight body text.

———————————————————

DORMANT ENTITIES

[Entities not mentioned recently, with last known status. Or "None — all entities active."]
```
<!-- END imessage -->

<!-- IF BRIEFING_METHOD = email -->
### Email Delivery

Send the briefing to `{{EMAIL_RECIPIENT}}` via Gmail.

**Subject:** Open Brain — [Day] [Date]

**The briefing contains answers and observations — not checklists or homework.**

Use plain text email. Format cleanly with line breaks and simple structure.

```
TRENDS & INSIGHTS

1. First insight title.
Insight body text.

2. Second insight title.
Insight body text.

———————————————————

DORMANT ENTITIES

[Entities not mentioned recently, with last known status. Or "None — all entities active."]
```
<!-- END email -->

<!-- IF BRIEFING_METHOD = file -->
### File Delivery

Write the briefing to `notes/briefings/YYYY-MM-DD.md`.

**The briefing contains answers and observations — not checklists or homework.**

Use standard markdown formatting.

```markdown
**Open Brain — [Day] [Date]**

---

## Trends & Insights

### 1. First insight title.
Insight body text.

### 2. Second insight title.
Insight body text.

---

## Dormant Entities

[Entities not mentioned recently, with last known status. Or "None — all entities active."]
```
<!-- END file -->

---

## Step 6: Commit

```bash
cd "{{VAULT_PATH}}" && git add -A && git commit -m "Updater run YYYY-MM-DD"
```
