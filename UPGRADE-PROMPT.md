# Upgrade Prompt — Jeff Burt's Open Brain

Paste the fenced block below into a fresh AI agent session (Claude Code, Cursor, Aider, Cline, or anything else with shell access and the ability to clone GitHub repos). The agent will audit your current vault, compare it against upstream, and walk you through each upgrade decision one at a time.

If you don't have a vault yet and want to install from scratch, use [`INSTALL-PROMPT.md`](./INSTALL-PROMPT.md) instead.

**Heads up — this prompt is intentionally long.** Upgrading is a negotiation, not a script. People customize their vaults in ways big and small, and a good upgrade respects those customizations. The prompt has five phases (audit, report, questions, apply, validate) and enforces that you see every change before it lands.

---

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
