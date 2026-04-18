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

## Setup — Paste One Of These Into Your AI

Pick based on whether you already have a vault. Works with any AI agent that has shell access and can clone GitHub repos (Claude Code, Cursor, Aider, Cline, etc.).

**Fresh install** (you don't have a vault yet):

```
Help me set up Jeff Burt's Open Brain from https://github.com/JMB702/jeff-burt-open-brain. Clone the repo, read the README, then follow INSTALL-PROMPT.md step by step.
```

**Upgrade an existing vault** (review-first, you approve each change):

```
Help me upgrade my existing Jeff Burt's Open Brain from https://github.com/JMB702/jeff-burt-open-brain. Clone the repo, read the README, then follow UPGRADE-PROMPT.md step by step.
```

That's it. The agent clones the repo, reads the detailed playbook for your scenario, and drives the rest. If you're curious what the agent will actually do, the playbooks are right here in the repo: [`INSTALL-PROMPT.md`](./INSTALL-PROMPT.md) and [`UPGRADE-PROMPT.md`](./UPGRADE-PROMPT.md).

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
| `INSTALL-PROMPT.md` | Copy-paste prompt for a fresh install |
| `UPGRADE-PROMPT.md` | Copy-paste prompt for upgrading an existing vault (review-first flow) |
| `SETUP-INSTRUCTIONS.md` | Detailed step-by-step install/upgrade reference, written for an AI agent |
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
