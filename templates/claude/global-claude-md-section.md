
## Open Brain — {{USER_FIRST_NAME}}'s knowledge system

**`{{VAULT_PATH}}/`** is {{USER_FIRST_NAME}}'s personal knowledge base. **Treat it as an extension of this file.** Consult it by default for any non-trivial question about {{USER_FIRST_NAME}}, their people, projects, preferences, or history. Skip it only for pure technical tasks with no personal context.

### Default triggers — consult Open Brain when you see any of these

- **Proper nouns** that might be a person, project, place, or event → check `entities-index.md` for aliases and the right file path.
- **Phrases like** "mentioned before," "wrote about," "last time," "my X," "what do I think about Y," "the X project" → Open Brain.
- **Personal context** — schedule, preferences, budget, goals, relationships, opinions, past decisions → Open Brain.
- **Location, date, photo, or OCR questions** ("where was I," "find the receipt," "photos from X") → Photos integration (below) before pixel vision.
- **Project work** needing personal context not present in the project directory → Open Brain.

If none of those apply, proceed normally.

### Lookup order — stop when you have enough

1. **Meta-questions about Open Brain itself** ("what is Open Brain," "what can it do," architecture/components) → read `{{VAULT_PATH}}/CLAUDE.md` and `{{VAULT_PATH}}/AGENTS.md` **first**. The tracker at `projects/Open Brain.md` narrates evolution; CLAUDE.md describes current architecture.
2. **Entity index** → `entities-index.md`. Flat list of every entity with aliases. Resolves names and gives you the right file path.
3. **Entity file** → `projects/<Name>.md`, `events/<Name>.md`, `Medical/<Name>.md`, `Other Entities/<Name>.md`. Verbatim daily-note paragraphs, chronological.
4. **Today's raw note** → `notes/raw-daily-notes/YYYY/MM-Month/YYYY-MM-DD.md`. Check this if the topic seems recent — the morning updater runs on a schedule, so anything written since hasn't been processed into entities yet.
5. **People — for communication context** → `~/.claude/people/<slug>.md` (richer profile with tech level, communication style, topics to avoid). Use this before messaging or advising about someone.
6. **People — for chronological mentions** → `{{VAULT_PATH}}/people/<slug>.md` (verbatim daily-note paragraphs, like other entities).
7. **Historical notes** → `notes/historical-notes/` — biographical context {{USER_FIRST_NAME}} wrote from memory. Flagged as less reliable than daily notes.
8. **Raw daily notes archive** → `notes/raw-daily-notes/YYYY/MM-Month/`. Only grep as a last resort when the entity file is missing or {{USER_FIRST_NAME}} explicitly asks.

### Photos integration

Apple Photos metadata (GPS, timestamps, face clusters, albums, OCR text) is cached locally and queryable via scripts in `{{VAULT_PATH}}/scripts/`:

- `photos_query.py <date>` — by date/range
- `photos_for_entity.py <entity-file>` — correlate photos to an entity
- `photos_candidates.py <date>` — ranked shortlist with filters (`--person`, `--location`, `--text`, `--labels`)
- `photos_export.py <uuid>` — materialize a photo for vision

Metadata first, pixel vision sparingly. User skills: `/what-did-i-see`, `/photos-for-event`. Full rules: `{{VAULT_PATH}}/Photos/README.md`.

### Hard rules

- **Never edit raw daily notes.** Wiki-link additions only (`[[Entity Name]]`).
- **Never invent facts.** If Open Brain doesn't say it, say you don't know.
- **Daily notes are source of truth** for how {{USER_FIRST_NAME}} thinks — not source code, not old CLAUDE.md files, not auto-generated memory.
- **Project's own CLAUDE.md** is authoritative for project content; Open Brain summarizes and connects.
- Skills: `/open-brain` (read + create), `/open-brain-edit` (modify existing), `/open-brain-extract` (chronological extraction on a topic), `/daily-note` (log a session).
