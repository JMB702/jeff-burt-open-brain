# Jeff Burt's Open Brain

A personal knowledge vault for your daily notes, with an AI updater that reads them nightly and builds a structured map of the people, projects, events, and ideas running through your life.

Tackling the same problem as [**Nate Jones's Open Brain (OB1)**](https://github.com/NateBJones-Projects/OB1) — this is my own take on it. Opinionated, Obsidian-native, and maintained by an AI agent you point at the vault.

---

## Is This The Right Open Brain For You?

Both projects exist to solve the same core problem — **your AI tools forget you, and your knowledge is fragmented across silos** — but they solve it in very different ways. Read this section before setting either one up.

### Side-by-Side

| | **Jeff's Open Brain** (this repo) | **Nate's OB1** ([link](https://github.com/NateBJones-Projects/OB1)) |
|---|---|---|
| **Where data lives** | Local markdown files in an Obsidian vault | Cloud Postgres + pgvector (Supabase or self-hosted) |
| **Capture surface** | Long-form daily notes written in Obsidian (phone + desktop) | Quick messages to Slack or Discord |
| **How AI reads it** | AI agent reads/writes markdown files directly | Any AI queries via MCP + semantic vector search |
| **Cross-AI sharing** | Whichever agent you point at the vault — one agent at a time | Built for it — Claude, ChatGPT, Cursor all share one memory |
| **What you get out** | Daily briefings, chronological entity logs, dormancy alerts, trend analysis | AI-queryable recall of anything you've captured |
| **Running cost** | Free (you already pay for your AI subscription) | ~$0.10–0.30/month (Supabase free tier) |
| **Human readability** | Every file is plain markdown you can read in any editor — forever | Data sits in a database; you query it, you don't browse it |
| **Setup time** | ~30 min (install Obsidian, run the setup agent, write your first note) | ~30–45 min (deploy Supabase, wire up chat capture, install MCP) |

### Pick Jeff's if you want…

- **Long-form journaling.** You write full paragraphs about your day, your projects, your people. You want the AI to organize that chronologically, not just store facts.
- **Human-readable forever.** Plain markdown files you can open in any editor, sync with Obsidian Sync / iCloud / Dropbox, and still read in 20 years whether or not the AI industry exists.
- **A morning briefing habit.** You want the AI to proactively tell you what's trending in your life, what's gone quiet, and what connects across domains — not just answer queries.
- **Deep per-entity history.** You want to open a file for a person, project, or idea and see every paragraph you've ever written about it, in order, with no database lookup required.
- **One agent, deep context.** You're fine pointing a single AI agent (Claude Code, Cursor, etc.) at the vault and having it know everything.

### Pick Nate's OB1 if you want…

- **Every AI remembers everything.** Claude, ChatGPT, Cursor, and your phone app all pulling from one shared memory via MCP. This is the core OB1 pitch.
- **Quick-capture, not journaling.** You'd rather ping a Slack message than write a paragraph. Small, atomic facts you'll query later.
- **Semantic search.** You want "find everything about X" to surface conceptually related items, not just keyword matches.
- **Infrastructure that scales.** You're building on top of it — family coordination, household automation, cross-person shared brains — and you want a real database.

### Use both?

They're not mutually exclusive. You can journal in Jeff's vault for long-form thinking and pipe quick captures into Nate's OB1 for cross-AI recall. Different tools for different moments.

---

## What You Get

- **Daily notes** you write freely in Obsidian. Organized as `notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md`. Never edited by the AI.
- **Entity files** the AI extracts and maintains — people, projects, events, medical, places, other. Each one is an append-only chronological log of your own words.
- **Morning briefings** delivered via Slack, iMessage, email, or a local file. Trends, insights, and "what's gone quiet that shouldn't have."
- **Per-person profiles** with contact info, relationship context, and one-line snippets per daily note mention.
- **Transcripts** as a first-class source artifact — paste in Zoom transcripts, link them to events/projects, get them indexed alongside your notes.
- **An extraction skill** (`/open-brain-extract`) to pull every paragraph you've ever written about any topic, chronologically.

## Design Philosophy

- **You write. The AI reads.** Daily notes are sacred. The AI only adds wiki links; it never rewrites your words.
- **Model-agnostic.** The value lives in the data and structure, not any one AI's capabilities. Swap Claude for GPT or a local model without breaking anything.
- **One source of truth.** Information lives in one place and is linked from others. No duplication.
- **Auto-generated memory is unreliable.** Treat anything the AI produces as regenerable. Your handwritten notes are the only ground truth.

---

## Setup Prompts — Paste Into Your AI

Both prompts below work with any agent that has shell access and can clone GitHub repos (Claude Code, Cursor, Aider, Cline, etc.). Copy the fenced block for your scenario and paste it into a fresh session.

### Fresh Install

Use this if you don't have a vault yet:

```
I want to set up Jeff Burt's Open Brain — an AI-readable personal knowledge vault for daily notes plus automatic entity extraction.

The setup system lives at: https://github.com/JMB702/jeff-burt-open-brain

Please do the following:

1. Clone that repo into a scratch directory:
   git clone https://github.com/JMB702/jeff-burt-open-brain.git /tmp/jb-open-brain-setup
   cd /tmp/jb-open-brain-setup

2. Read SETUP-INSTRUCTIONS.md from top to bottom. It is written to be read by an AI agent — follow it step by step, do not skip steps, and do not abbreviate.

3. Ask me the configuration questions it requires:
   - My full name and preferred first name
   - Where I want the vault to live on disk
   - My timezone
   - How I want morning briefings delivered (Slack, iMessage, Gmail, or a local file)
   - Any workspace / channel / email details for the briefing destination
   Do not guess. Ask one question at a time if that's easier.

4. Execute every step of the installation: directory creation, template substitution, script copying, Claude skill setup, git init of the new vault.

5. Run the validator at the end: sh scripts/run_open_brain_checks.sh --fresh-install
   Confirm it passes cleanly before handing off.

6. Tell me what my first-day actions are — creating my first daily note at the right path, connecting external services, scheduling the updater, opening the vault in Obsidian.

Start by asking me where I want the vault to live on my filesystem.
```

### Upgrade an Existing Vault

Use this if you already have a vault installed and want the latest scripts, skills, and template fixes:

```
I already have Jeff Burt's Open Brain installed and I want to pull in the latest updates.

The setup system lives at: https://github.com/JMB702/jeff-burt-open-brain

Please do the following:

1. Clone the latest setup repo into a scratch directory:
   git clone https://github.com/JMB702/jeff-burt-open-brain.git /tmp/jb-open-brain-setup
   cd /tmp/jb-open-brain-setup

2. Ask me for the absolute path to my existing Open Brain vault.

3. Safety first: check for uncommitted changes in my vault. If there are any, ask me to commit or stash them before you touch anything.

4. Run the automated upgrade from inside the cloned setup repo:
   sh setup.sh --upgrade <my-vault-path>
   This updates regenerable things automatically: scripts/, .githooks/, the open-brain-extract skill, and the scheduled-task SKILL.md. It does NOT overwrite my CLAUDE.md, OPEN BRAIN UPDATER.md, .claude/settings.local.json, or any vault content — those have my customizations.

5. Read SETUP-INSTRUCTIONS.md sections U3 and U4. Diff my vault's CLAUDE.md and OPEN BRAIN UPDATER.md against the upstream templates in templates/vault/. Surface every meaningful change — new sections, changed instructions, new conventions — and ask me before applying any of them. Respect my template substitutions (my name, vault path, timezone, briefing method) when comparing.

6. Read section U5. Compare templates/claude/settings.local.json against my .claude/settings.local.json. If any new permission UUIDs were added upstream, tell me which ones and ask before adding them.

7. Read section U6. Check if the global ~/.claude/CLAUDE.md section has changed upstream. If so, surface the diff and ask before applying.

8. Run the validator from my vault root: sh scripts/run_open_brain_checks.sh
   Fix any new errors that surface from the updated validator.

9. Summarize: what was auto-updated, what I need to review manually, whether the scheduled task needs reloading, and whether I need to re-authenticate any external services (Slack, Gmail, iMessage).

Hard rules — do not touch any of these under any circumstance:
- notes/raw-daily-notes/
- notes/historical-notes/
- notes/transcripts/
- projects/, "Other Entities/", events/, Medical/, people/, places/, research/
- entities-index.json, entities-index.md (regenerated automatically)
- notes/.manifest
- .obsidian/workspace.json, .obsidian/plugins/, .obsidian/themes/
- Anything I've written by hand in the Background sections of people profiles

Start by asking for my vault's absolute path and confirming you have permission to run shell commands and edit files there.
```

---

## Manual Setup

Clone this repo and open [`SETUP-INSTRUCTIONS.md`](./SETUP-INSTRUCTIONS.md). It's written to be read by an AI agent, but humans can follow it too — you'll just do the template substitutions by hand.

```bash
git clone https://github.com/JMB702/jeff-burt-open-brain.git
cd jeff-burt-open-brain
# read SETUP-INSTRUCTIONS.md
```

---

## Requirements

- [Obsidian](https://obsidian.md) (free) for writing and browsing the vault
- An AI agent with shell and filesystem access — [Claude Code](https://claude.ai/code), Cursor, Aider, Cline, etc.
- Optional: Slack, Gmail, or iMessage MCP connections for briefing delivery
- Python 3.9+ (for the updater scripts)

---

## What's In This Repo

| Path | Purpose |
|------|---------|
| `SETUP-INSTRUCTIONS.md` | Step-by-step install, written for an AI agent |
| `setup.sh` | Shell bootstrapper invoked during setup |
| `templates/vault/` | Starter vault files (`CLAUDE.md`, `OPEN-BRAIN-UPDATER.md`, etc.) |
| `templates/scripts/` | Python/shell scripts the vault needs (validator, entity index builder, updater, etc.) |
| `templates/claude/` | Claude Code skills and `settings.local.json` scaffolding |
| `templates/githooks/` | Pre-commit validator hook |
| `templates/scheduled-task/` | Scheduled-task skill for automated daily briefings |
| `examples/` | Sample entity files showing the expected format |

---

## What This Isn't

- **Not a SaaS.** You host your own vault on your own machine. No servers, no accounts, no lock-in.
- **Not cloud-synced by default.** Pair with Obsidian Sync, iCloud, Dropbox, or a private git remote if you want multi-device.
- **Not the only approach.** [Nate Jones's OB1](https://github.com/NateBJones-Projects/OB1) is another take on the same idea with a very different architecture — see the comparison section above.

---

## License

MIT. See [`LICENSE`](./LICENSE).

---

Built by [Jeff Burt](https://github.com/JMB702) · [Eos Automations](https://eosautomations.com).
