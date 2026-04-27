## Open Brain Scripts

### Validator

Run the structural validator from the vault root:

```bash
sh scripts/run_open_brain_checks.sh
```

Apply low-risk structural fixes first, then validate:

```bash
sh scripts/run_open_brain_checks.sh --fix
```

Preview which files `--fix` would change, without writing anything:

```bash
sh scripts/run_open_brain_checks.sh --check-fix
```

The validator currently checks:
- broken wiki links
- missing required metadata on entity files
- duplicate aliases
- malformed verbatim entity entry blocks
- malformed human summary blocks
- manifest file sanity against `notes/raw-daily-notes/`
- allowed `Priority` values
- required event metadata shape before the `---` separator

The `--fix` mode is intentionally conservative. It currently normalizes:
- `Priority` casing to `active`, `background`, or `archive`
- `Priority` and `Aliases` ordering at the top of entity files
- blank-line spacing in the top metadata/header section

It does not rewrite daily note content or entity entry text.

### Updater Entry Point

Use the canonical updater entry point:

```bash
sh scripts/run_open_brain_updater.sh
```

This command:
- runs the Open Brain structural checks first
- stops immediately if validation fails
- prints the exact `CLAUDE.md` and `OPEN BRAIN UPDATER.md` instruction bundle for the updater run

This is useful for scheduled tasks and for any agent session that should start from the same preflighted updater context.

### Note Processing Dry Run

Before Claude Code edits the vault for a pending daily or historical note, generate a deterministic ingestion report:

```bash
python3 scripts/process_note.py notes/raw-daily-notes/YYYY/MM-MonthName/YYYY-MM-DD.md
```

Machine-readable output:

```bash
python3 scripts/process_note.py <note-path> --json
```

Write the JSON report to a file without editing vault content:

```bash
python3 scripts/process_note.py <note-path> --output tmp/process-note-report.json
```

The report includes paragraph indexes, direct entity/person alias matches, likely entity appends, duplicate warnings, unmatched paragraphs, manifest status, and a preview of the `tmp/run-delta.json` shape. It is dry-run only. Claude Code still owns indirect reasoning and final writes.

### Operator Workflow

The standard operator flow is:

1. Preview low-risk structural cleanup if needed:

```bash
sh scripts/run_open_brain_checks.sh --check-fix
```

2. Apply low-risk structural cleanup if appropriate:

```bash
sh scripts/run_open_brain_checks.sh --fix
```

3. Start the updater from the canonical entry point:

```bash
sh scripts/run_open_brain_updater.sh
```

If you only want a clean validation pass with no fixes, run:

```bash
sh scripts/run_open_brain_checks.sh
```

It exits with code `1` when validation fails, which makes it safe to use in Git hooks and automation.

### Pre-commit Hook

This repo includes a tracked pre-commit hook in `.githooks/pre-commit` that runs the validator before each commit.

If the hook path is not already configured for this repo, enable it with:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

After that, every `git commit` in this repo will run the validator automatically.
