# Open Brain Setup Instructions

You are setting up **Open Brain**, a personal knowledge system built on Obsidian and Claude Code. This file contains every step you need to follow. Read it completely before starting.

## Prerequisites

- **Obsidian** installed (https://obsidian.md — free)
- **Claude Code** (or another AI coding agent) installed
- **Git** installed
- **Python 3** installed (for validation and entity index scripts)
- macOS or Linux (Windows support untested)

---

## Automated Setup (Recommended)

The fastest path is to use `setup.sh`. It handles directory creation, file copying, template substitution, conditional block stripping, validation, and git init in one command.

### Fresh Install

1. Gather the user's preferences (see Step 1 below for the questions).
2. Write a config file (any path, e.g., `/tmp/ob-config`). Quote all values:
   ```
   USER_FULL_NAME="Jane Smith"
   USER_FIRST_NAME="Jane"
   VAULT_PATH="~/Documents/Open Brain"
   TIMEZONE="America/New_York"
   BRIEFING_METHOD="slack"
   SLACK_WORKSPACE="mycompany.slack.com"
   SLACK_CHANNEL_ID="C01EXAMPLE1"
   ```
3. Run: `sh setup.sh --install /tmp/ob-config`

### Upgrade

Run: `sh setup.sh --upgrade "~/Documents/Open Brain"`

This copies the latest scripts/hooks, validates, and builds the entity index. It does NOT overwrite CLAUDE.md or the updater — it prints what to review manually.

### Manual Setup (Fallback)

If the script doesn't fit your environment, follow the manual steps below.

## Fresh Install vs. Upgrade (Manual Path)

Before starting, determine which path to follow:

1. Ask the user where the vault should live (or already lives). Store as `{{VAULT_PATH}}`.
2. Check if an Open Brain vault already exists at that path:
   ```bash
   test -f "{{VAULT_PATH}}/CLAUDE.md" && test -d "{{VAULT_PATH}}/notes/raw-daily-notes" && echo "EXISTING" || echo "NEW"
   ```
3. If **EXISTING**: follow the **Upgrade** section below, then skip to Step 8.
4. If **NEW**: continue with Step 1 (Fresh Install).

---

## Upgrade an Existing Vault

Use this when an Open Brain vault already exists but needs to be brought up to date with the latest template changes.

### U1. Back Up

```bash
cp "{{VAULT_PATH}}/CLAUDE.md" "{{VAULT_PATH}}/CLAUDE.md.bak.$(date +%s)"
cp "{{VAULT_PATH}}/OPEN BRAIN UPDATER.md" "{{VAULT_PATH}}/OPEN BRAIN UPDATER.md.bak.$(date +%s)"
```

### U2. Copy Scripts and Hooks

These are not templatized — they work as-is in any vault:

```bash
mkdir -p "{{VAULT_PATH}}/scripts"
mkdir -p "{{VAULT_PATH}}/.githooks"
cp templates/scripts/* "{{VAULT_PATH}}/scripts/"
cp templates/githooks/* "{{VAULT_PATH}}/.githooks/"
chmod +x "{{VAULT_PATH}}/.githooks/pre-commit"
chmod +x "{{VAULT_PATH}}/scripts/"*.sh
```

### U3. Review and Apply CLAUDE.md Changes

Do NOT overwrite the existing `CLAUDE.md` — it may have user customizations.

Instead, compare the template against the existing file section by section. The key sections that may need to be added or updated:

1. **Entity Index section** (after File Locations table) — if missing, add it
2. **Validation section** (after Manifest section) — if missing, add it
3. **File Locations table** — ensure it includes `entities-index.json` and `entities-index.md` rows
4. **Updater Entry Point** — ensure it references `sh scripts/run_open_brain_updater.sh`

Read the template `CLAUDE.md` to see the canonical versions of these sections, then add any missing sections to the existing file. Preserve all user-specific content (names, paths, Slack config, etc.).

### U4. Review and Apply Updater Changes

Compare the template `OPEN-BRAIN-UPDATER.md` against the existing file. Key changes:

1. **Step 2a** — should reference `entities-index.md` instead of manual `ls`/`head` scanning
2. **Step 2f** — validate vault structure step (add if missing, after 2e)
3. **Step 4** — should include re-running validation after edits
4. **Canonical entry point** block at top — add if missing

### U5. Update Permissions

Check `{{VAULT_PATH}}/.claude/settings.local.json` and ensure it includes:
- `"Bash(python3 *)"` — for validation and index scripts
- `"Bash(sh scripts/*)"` — for shell script wrappers

### U6. Update Global CLAUDE.md

Check `~/.claude/CLAUDE.md` for the "Deep Context — Open Brain" section. The search order should be:
1. Entity index (`entities-index.md`) — start here
2. Entity files (`projects/`, `Other Entities/`, etc.)
3. People profiles (`people/`)
4. Daily notes (`notes/raw-daily-notes/`) — last resort
5. Historical notes (`notes/historical-notes/`) — biographical context

If the section references a stale path like `daily-notes/Other/`, update it. Daily notes are now at `notes/raw-daily-notes/`.

### U7. Validate and Build Index

```bash
cd "{{VAULT_PATH}}" && sh scripts/run_open_brain_checks.sh
```

This validates the vault structure and generates `entities-index.json` + `entities-index.md`.

### U8. Configure Git Hooks

```bash
cd "{{VAULT_PATH}}" && git config core.hooksPath .githooks
```

### U9. Commit

```bash
cd "{{VAULT_PATH}}" && git add -A && git commit -m "Upgrade: add scripts, validation, entity index"
```

After upgrading, skip to **Step 8: Report and Next Steps**.

---

## Step 1: Gather Preferences

Ask the user the following questions using your Q&A system. Store all answers — you'll use them to fill `{{VARIABLE}}` placeholders throughout the template files.

### Required

1. **What's your full name?** → Store as `{{USER_FULL_NAME}}`
2. **What's your first name?** (used throughout the system in place of the owner's name) → Store as `{{USER_FIRST_NAME}}`
3. **Where should the vault live?** Suggest `~/Documents/Open Brain` → Store as `{{VAULT_PATH}}`
4. **What's your timezone?** Suggest `America/New_York` → Store as `{{TIMEZONE}}`

### Briefing Delivery

5. **How would you like to receive your daily briefing?**
   - **Slack** — Posts to a Slack channel (requires Slack MCP connection)
   - **iMessage** — Sends to your phone number (requires iMessage MCP)
   - **Email** — Sends via Gmail (requires Gmail MCP connection)
   - **File only** — Saves to `notes/briefings/` in the vault (no integration needed)

   Store the choice as `{{BRIEFING_METHOD}}` (`slack`, `imessage`, `email`, or `file`).

   **If Slack:**
   - Ask: What's your Slack workspace URL? (e.g., `mycompany.slack.com`) → `{{SLACK_WORKSPACE}}`
   - Ask: What's the channel ID for briefings? (e.g., `C01EXAMPLE1` — find this in Slack channel details) → `{{SLACK_CHANNEL_ID}}`

   **If iMessage:**
   - Ask: What phone number should briefings be sent to? → `{{IMESSAGE_RECIPIENT}}`

   **If Email:**
   - Ask: What email address should briefings be sent to? → `{{EMAIL_RECIPIENT}}`

### Optional

6. **Do you want calendar integration?** (for scheduling awareness in briefings) → `{{CALENDAR_ENABLED}}` (`true`/`false`)

---

## Step 2: Create Vault Directory Structure

Create the following directories at `{{VAULT_PATH}}`:

```
{{VAULT_PATH}}/
├── notes/
│   ├── raw-daily-notes/   # organized as YYYY/MM-MonthName/YYYY-MM-DD.md
│   ├── historical-notes/
│   ├── transcripts/
│   └── briefings/
├── projects/
├── Other Entities/
├── events/
├── Medical/
├── people/
├── places/
├── research/
├── scripts/
├── .githooks/
├── .claude/
│   └── skills/
│       └── open-brain-extract/
└── .obsidian/
```

```bash
mkdir -p "{{VAULT_PATH}}/notes/raw-daily-notes"
mkdir -p "{{VAULT_PATH}}/notes/historical-notes"
mkdir -p "{{VAULT_PATH}}/notes/briefings"
mkdir -p "{{VAULT_PATH}}/projects"
mkdir -p "{{VAULT_PATH}}/Other Entities"
mkdir -p "{{VAULT_PATH}}/events"
mkdir -p "{{VAULT_PATH}}/Medical"
mkdir -p "{{VAULT_PATH}}/people"
mkdir -p "{{VAULT_PATH}}/places"
mkdir -p "{{VAULT_PATH}}/research"
mkdir -p "{{VAULT_PATH}}/scripts"
mkdir -p "{{VAULT_PATH}}/.githooks"
mkdir -p "{{VAULT_PATH}}/.claude/skills/open-brain-extract"
mkdir -p "{{VAULT_PATH}}/.obsidian"
```

---

## Step 3: Copy and Templatize Files

For each template file listed below, copy it to the specified destination inside the vault. Replace ALL `{{VARIABLE}}` placeholders with the values gathered in Step 1.

**Important:** After copying each file, verify that no `{{` placeholders remain. If `{{BRIEFING_METHOD}}` is `file`, remove the Slack/iMessage/Email sections from the updater and CLAUDE.md rather than leaving unfilled placeholders.

| Template Source (relative to this folder) | Destination |
|---|---|
| `templates/vault/CLAUDE.md` | `{{VAULT_PATH}}/CLAUDE.md` |
| `templates/vault/OPEN-BRAIN-UPDATER.md` | `{{VAULT_PATH}}/OPEN BRAIN UPDATER.md` |
| `templates/vault/.obsidian/app.json` | `{{VAULT_PATH}}/.obsidian/app.json` |
| `templates/vault/.obsidian/appearance.json` | `{{VAULT_PATH}}/.obsidian/appearance.json` |
| `templates/vault/.obsidian/core-plugins.json` | `{{VAULT_PATH}}/.obsidian/core-plugins.json` |
| `templates/vault/.obsidian/graph.json` | `{{VAULT_PATH}}/.obsidian/graph.json` |
| `templates/vault/Medical/Medical Info.md` | `{{VAULT_PATH}}/Medical/Medical Info.md` |
| `templates/claude/settings.local.json` | `{{VAULT_PATH}}/.claude/settings.local.json` |
| `templates/claude/skills/open-brain-extract/SKILL.md` | `{{VAULT_PATH}}/.claude/skills/open-brain-extract/SKILL.md` |
| `templates/scripts/validate_open_brain.py` | `{{VAULT_PATH}}/scripts/validate_open_brain.py` |
| `templates/scripts/build_entity_index.py` | `{{VAULT_PATH}}/scripts/build_entity_index.py` |
| `templates/scripts/run_open_brain_checks.sh` | `{{VAULT_PATH}}/scripts/run_open_brain_checks.sh` |
| `templates/scripts/run_open_brain_updater.sh` | `{{VAULT_PATH}}/scripts/run_open_brain_updater.sh` |
| `templates/scripts/generate_agents_md.py` | `{{VAULT_PATH}}/scripts/generate_agents_md.py` |
| `templates/scripts/notes_to_process.py` | `{{VAULT_PATH}}/scripts/notes_to_process.py` |
| `templates/scripts/match_entities.py` | `{{VAULT_PATH}}/scripts/match_entities.py` |
| `templates/scripts/list_dormant.py` | `{{VAULT_PATH}}/scripts/list_dormant.py` |
| `templates/scripts/backfill_last_entry_date.py` | `{{VAULT_PATH}}/scripts/backfill_last_entry_date.py` |
| `templates/scripts/clean_zoom_transcript.py` | `{{VAULT_PATH}}/scripts/clean_zoom_transcript.py` |
| `templates/scripts/README.md` | `{{VAULT_PATH}}/scripts/README.md` |
| `templates/githooks/pre-commit` | `{{VAULT_PATH}}/.githooks/pre-commit` |
| `dotgitignore` | `{{VAULT_PATH}}/.gitignore` |

**Note:** Scripts and githooks are NOT templatized — copy them as-is. After copying, make all scripts executable and generate `AGENTS.md` from the substituted `CLAUDE.md`:

```bash
chmod +x "{{VAULT_PATH}}/scripts/"*.sh "{{VAULT_PATH}}/scripts/"*.py "{{VAULT_PATH}}/.githooks/pre-commit"
( cd "{{VAULT_PATH}}" && python3 scripts/generate_agents_md.py )
```

### Entity File Format Reference

The `examples/` directory contains sample entity files showing the correct format:
- `examples/project-entity.md` — project entity with priority, aliases, summary, and verbatim entries
- `examples/other-entity.md` — same format for ideas/concepts
- `examples/event-entity.md` — event entity with structured metadata header
- `examples/people-profile.md` — person profile with YAML frontmatter

The user can reference these when creating entities manually, or let the updater create them automatically from daily notes.

### Conditional: Updater Step 5 (Briefing Delivery)

The updater template (`OPEN-BRAIN-UPDATER.md`) contains all four delivery variants in Step 5, wrapped in comments like:

```
<!-- IF BRIEFING_METHOD = slack -->
...
<!-- END slack -->
```

**Keep only the section matching `{{BRIEFING_METHOD}}`** and delete the other three. Remove the comment markers from the kept section.

### Conditional: CLAUDE.md Slack Section

The vault `CLAUDE.md` template has a Slack section wrapped in:

```
<!-- IF SLACK -->
...
<!-- END SLACK -->
```

If `{{BRIEFING_METHOD}}` is `slack`, keep this section and remove the comment markers. Otherwise, delete the entire block.

---

## Step 4: Set Up .claude/ Inside the Vault

The `settings.local.json` file pre-authorizes permissions so the scheduled updater doesn't hang on prompts. After copying and templatizing it:

1. Verify all `{{VAULT_PATH}}` values were replaced
2. If the user chose a briefing method that uses MCP (Slack, Gmail, iMessage), add a comment in the file noting which MCP permission needs to be added once connected:

```json
// TODO: After connecting [Slack/Gmail/iMessage] MCP, add:
// "mcp__<UUID>__[tool_name]"
// Find the UUID from the MCP tool names in your Claude Code session
```

The MCP server UUIDs are installation-specific and cannot be predicted. The user will need to:
1. Connect their MCP integration in Claude Code
2. Find the UUID from any tool name (format: `mcp__<UUID>__tool_name`)
3. Add the permission line to `settings.local.json`

**Permissions to add per briefing method:**
- **Slack:** `mcp__<UUID>__slack_send_message`
- **Gmail:** `mcp__<UUID>__gmail_create_draft`
- **iMessage:** `mcp__<UUID>__send_imessage`
- **File:** No MCP permission needed

---

## Step 5: Append to Global ~/.claude/CLAUDE.md

This step adds the "Deep Context — Open Brain" section to the user's global Claude configuration so all Claude sessions know about the vault.

1. Check if `~/.claude/` directory exists. If not, create it: `mkdir -p ~/.claude`
2. Check if `~/.claude/CLAUDE.md` exists.
   - If it exists, back it up: `cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak.$(date +%s)`
   - Check if it already contains `## Deep Context — Open Brain`. If so, **skip this step** (don't duplicate).
3. Read `templates/claude/global-claude-md-section.md`, replace all `{{VARIABLE}}` placeholders.
4. Append the result to `~/.claude/CLAUDE.md` (or create it if it doesn't exist).

**Note:** This only adds the Open Brain pointer section. It does NOT add personal information. The user can add their own "About" section to `~/.claude/CLAUDE.md` separately if they want Claude to have personal context.

---

## Step 6: Set Up Scheduled Task

Create the updater scheduled task so Open Brain runs automatically each morning.

1. **Check first:** if `~/.claude/scheduled-tasks/open-brain-updater/SKILL.md` already exists AND points at a different vault path, STOP. The automated `setup.sh` flow refuses to clobber an existing task for exactly this reason. Either point this install at the same vault as the existing task, or have the user remove the existing `SKILL.md` before continuing.
2. Create directory: `mkdir -p ~/.claude/scheduled-tasks/open-brain-updater`
3. Copy `templates/scheduled-task/SKILL.md` to `~/.claude/scheduled-tasks/open-brain-updater/SKILL.md`
4. Replace `{{VAULT_PATH}}` in the file with the actual (absolute) vault path — not a relative or `~`-prefixed path.

The scheduled task will run when configured via the Claude Code scheduled tasks system. The user can set the cron schedule (e.g., daily at 6 AM) through their Claude Code interface.

### Why the scheduled task gets stuck on permissions

The scheduled-task agent runs headless — it cannot answer permission prompts. Any Bash command or file write that isn't in `.claude/settings.local.json` causes the task to hang or abort silently. The template `settings.local.json` already authorizes everything the shipped updater needs. If you add new scripts, new Bash commands, or new file-write paths, **also add them to the allow-list**, or the scheduled task will break the next morning.

Particularly easy to miss when extending the updater:
- `Bash(mkdir *)` for creating the `tmp/` directory (required for `run-delta.json`)
- `Bash(stat *)` for reading historical-note filesystem timestamps
- `Bash(find *)` as a safety net for historical-note discovery
- `Write(/tmp/**)` if you add scratch files outside the entity folders

---

## Step 7: Initialize Manifest, Validate, and Set Up Git

```bash
touch "{{VAULT_PATH}}/notes/.manifest"
cd "{{VAULT_PATH}}" && sh scripts/run_open_brain_checks.sh
```

This validates the vault structure and generates the entity index (`entities-index.json` + `entities-index.md`). Fix any errors before proceeding.

Then initialize Git:

```bash
cd "{{VAULT_PATH}}" && git init && git config core.hooksPath .githooks && git add -A && git commit -m "Initial Open Brain setup"
```

The pre-commit hook will run the validator automatically on every future commit.

---

## Step 8: Report and Next Steps

Tell the user:

1. **Setup complete.** Open Brain vault created at `{{VAULT_PATH}}`.
2. **Open in Obsidian:** Launch Obsidian → "Open folder as vault" → select the vault path.
3. **Import existing notes:** If you have existing daily notes, copy them into `notes/raw-daily-notes/YYYY/MM-MonthName/` using the `YYYY-MM-DD.md` filename format (e.g., `2026/04-April/2026-04-05.md`). Then run the updater manually the first time — the initial processing of many notes may take longer than a typical scheduled run. The system will automatically detect and process all unprocessed notes.
4. **Connect integrations:** If you chose Slack/Gmail/iMessage for briefings, connect the MCP integration in Claude Code and add the permission to `.claude/settings.local.json` (see Step 4 for details).
5. **Schedule the updater:** Configure the `open-brain-updater` scheduled task to run daily at your preferred time (e.g., 6 AM).
6. **Start writing:** Create your first daily note at `notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md` (e.g., `notes/raw-daily-notes/2026/04-April/2026-04-05.md`). Write freely — the updater will process it on its next run.

---

## How It Works (For the User)

- **You write daily notes** under `notes/raw-daily-notes/YYYY/MM-MonthName/`. Just write. The AI handles everything else.
- **The updater runs automatically** (or manually). It reads your new notes, extracts mentions of people/projects/events/concepts, and files them into the right entity.
- **Entity files** (`projects/`, `people/`, `events/`, `Other Entities/`, `Medical/`) accumulate verbatim excerpts from your notes over time, giving you a chronological history of each topic.
- **The briefing** summarizes trends, surfaces dormant entities, and connects dots across your life.
- **The extraction skill** (`/open-brain-extract`) lets you pull together everything you've written about any topic on demand.
