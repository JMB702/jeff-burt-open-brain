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

Use this if you already have a vault installed and want to pull in the latest scripts, skills, and template improvements. **This prompt is longer than the fresh-install one on purpose** — upgrading is a negotiation, not a script. People customize their vaults in ways big and small, and a good upgrade respects those customizations:

```
I already have Jeff Burt's Open Brain installed and I want to pull in the latest updates.

The setup system lives at: https://github.com/JMB702/jeff-burt-open-brain

This upgrade is a negotiation, not a mechanical script. I've probably customized parts of my vault — my CLAUDE.md, the updater, my settings, maybe my scripts. You need to understand my current state, compare it to upstream, surface the differences with explanations, and let me decide case by case what to take and what to keep. Read this entire prompt before doing anything.

===== PHASE 0 — SETUP (read-only) =====

1. Clone the latest setup repo into a scratch directory:
   git clone https://github.com/JMB702/jeff-burt-open-brain.git /tmp/jb-open-brain-setup
   cd /tmp/jb-open-brain-setup

2. Ask me for the absolute path to my existing vault. Verify it exists and contains a CLAUDE.md file.

3. Safety check: in my vault, run `git status`. If there are uncommitted changes, stop and ask me to commit or stash them before you touch anything. Never overwrite uncommitted work.

===== PHASE 1 — STATE AUDIT (read-only) =====

Do not modify any file in my vault during this phase. You are only reading and reporting.

4. Map my vault's current structure. List:
   - Every subdirectory under my vault root (depth 2 is enough for discovery)
   - Every file in scripts/, .githooks/, .claude/skills/, templates/, and the vault root
   - Whether I have a .obsidian/ config, a notes/.manifest, a CLAUDE.md, an OPEN BRAIN UPDATER.md, a .claude/settings.local.json
   - Any non-standard folders I've added (e.g., Books/, Dreams/, custom entity categories)

5. Check my vault's git log: `git log --oneline -50`. This tells you what I've done since installing — commits labeled "Upgrade" vs. content commits vs. structural changes. Flag anything that looks like a self-made customization (e.g., "Add Books folder", "Custom migraine tracking").

6. For each file that exists in BOTH my vault AND the upstream templates/, run a diff. You care about these pairs specifically:
   - my-vault/CLAUDE.md           vs. /tmp/jb-open-brain-setup/templates/vault/CLAUDE.md
   - my-vault/OPEN BRAIN UPDATER.md  vs. /tmp/jb-open-brain-setup/templates/vault/OPEN-BRAIN-UPDATER.md
   - every file in my-vault/scripts/  vs. /tmp/jb-open-brain-setup/templates/scripts/
   - every file in my-vault/.githooks/ vs. /tmp/jb-open-brain-setup/templates/githooks/
   - every file in my-vault/.claude/skills/ vs. /tmp/jb-open-brain-setup/templates/claude/skills/
   - my-vault/.claude/settings.local.json vs. /tmp/jb-open-brain-setup/templates/claude/settings.local.json
   - ~/.claude/CLAUDE.md (my global) — look for the "Deep Context — Open Brain" / similar section and compare against /tmp/jb-open-brain-setup/templates/claude/global-claude-md-section.md

   When diffing CLAUDE.md and the UPDATER, IGNORE template substitutions (my name, first-name slug, vault path, timezone, briefing method, Slack workspace, channel ID, etc.) — those are my personal values, not customizations. Focus on structural/content differences.

7. Build a classification for every delta you find. Use these categories:
   - [UPSTREAM-NEW]   File or section exists upstream, not in my vault. Candidate to add.
   - [UPSTREAM-CHANGED-USER-UNCHANGED]  Upstream evolved, I never touched it. Usually safe to apply.
   - [USER-CUSTOMIZED-UPSTREAM-UNCHANGED]  I changed it, upstream didn't. Leave alone.
   - [BOTH-CHANGED]  Conflict. Needs a 3-way discussion.
   - [USER-ADDED]    I have it, upstream doesn't. Definitely leave alone.
   - [UPSTREAM-REMOVED]  Upstream used to ship this, no longer does. I should be asked whether I still want it.

===== PHASE 2 — WRITTEN STATE REPORT =====

Before asking any questions, produce a single written report for me in this shape:

    ## Upgrade review for <vault path>
    
    **Your vault, in brief:**
    - <N> daily notes spanning <date range>
    - <N> entity files across <folders>
    - <N> people profiles
    - Git log shows <M> commits since you installed; last commit <date>
    
    **Scripts (<folder>/scripts/):**
    - X files identical to upstream
    - Y files where upstream has changes you don't have — list each with a one-line description of what changed and why it matters
    - Z files you've customized — list each, I will not touch these without asking
    - W files upstream adds that you don't have — list each with what it does
    
    **CLAUDE.md:**
    - Sections you have but upstream no longer ships: ...
    - Sections upstream now has that you don't: ... (with WHY each matters)
    - Sections where we both have differences: ... (needs 3-way review)
    
    **OPEN BRAIN UPDATER.md:**
    - (same structure as CLAUDE.md)
    
    **Skills and settings:**
    - New permission UUIDs in upstream: ...
    - New or changed skill files: ... (with what they enable)
    
    **Global ~/.claude/CLAUDE.md Open Brain section:**
    - Differences and why
    
    **Non-standard folders I found in your vault:**
    - e.g., Books/, Music/ — I'll leave these alone
    
    **What I will NOT touch (hard rules):**
    - All raw-daily-notes, historical-notes, transcripts
    - All entity folders (projects/, Other Entities/, events/, Medical/, people/, places/, research/)
    - entities-index.*, notes/.manifest
    - .obsidian/workspace.json, .obsidian/plugins/, .obsidian/themes/
    - Background sections of people profiles
    
    **My recommendation:**
    - Strong yeses: <additive improvements with no downside>
    - Needs your call: <things that conflict with your customizations>
    - Skip unless you want it: <stylistic or opt-in features>

Deliver this report. Do not take any action yet.

===== PHASE 3 — CLARIFYING QUESTIONS =====

Once I've read the report, ask me about each non-obvious upgrade one at a time. Format:

    [UPGRADE NAME]
    What it is: <one sentence>
    Why it's better: <one or two sentences — what problem it solves, what it enables. Reason from the code change itself. Do not invent benefits.>
    What changes if you take it: <concrete list>
    What you lose: <anything — honestly>
    Apply? (yes / no / modify)

For conflicts, frame as a three-way:

    [CONFLICT]
    Upstream version does: <X>
    Your version does: <Y>
    What you might have been going for: <best-effort read of my intent>
    Options:
      (a) Keep yours
      (b) Take upstream's
      (c) Merge — I'll propose a merged version for your review
    Choose:

Ask one question at a time unless I tell you to batch.

===== PHASE 4 — APPLY (only what I approved) =====

For each approved change:
- Back up the file being modified: cp <file> <file>.bak.$(date +%s)
- Apply the change
- Show me the resulting diff so I can see exactly what landed
- Wait for my "good" before moving to the next file

For bulk-safe changes (e.g., script updates where I confirmed I hadn't customized them), you may apply all at once and show me the summary diff.

When updating CLAUDE.md or the updater, never blind-overwrite. Always use surgical edits that preserve every line of mine you didn't explicitly get approval to change.

===== PHASE 5 — VALIDATE AND REPORT =====

After all approved changes are applied:

1. Run: sh scripts/run_open_brain_checks.sh (from my vault root)
   Fix any errors that surface from the newer validator. If a new validator rule flags existing content, tell me the rule, show me the flagged files, and ask before auto-fixing.

2. If the updater scheduled task exists, remind me it may need to be reloaded in Claude Code for any new SKILL.md content to take effect.

3. Final summary in this shape:
    ## Upgrade complete
    **Applied:** <list with one-liner for each>
    **Skipped at your request:** <list>
    **Needs your manual follow-up:** <e.g., reconnect Slack if permission UUID changed, reload scheduled task, edit Background sections by hand>
    **Backups created:** <list of .bak files, so I can delete them once I've verified>

===== HARD RULES =====

Never touch under any circumstance, regardless of what upstream changed:
- notes/raw-daily-notes/
- notes/historical-notes/
- notes/transcripts/
- projects/, "Other Entities/", events/, Medical/, people/, places/, research/
- entities-index.json, entities-index.md (regenerate via the validator, don't copy)
- notes/.manifest
- .obsidian/workspace.json, .obsidian/plugins/, .obsidian/themes/, .obsidian/workspace-mobile.json
- The ## Background sections of people profiles (human-curated)
- Any file or folder you can't explain the purpose of — ask first

Never run setup.sh --upgrade <path> as a shortcut to skip this review. The point of this upgrade is that I see every change before it lands.

Start now with Phase 0, Step 1.
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
