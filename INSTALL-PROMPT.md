# Install Prompt — Jeff Burt's Open Brain

Paste the fenced block below into a fresh AI agent session (Claude Code, Cursor, Aider, Cline, or anything else with shell access and the ability to clone GitHub repos). The agent will clone this repo, ask you the configuration questions, and build out your vault.

If you already have a vault and want to pull in updates instead, use [`UPGRADE-PROMPT.md`](./UPGRADE-PROMPT.md).

---

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
