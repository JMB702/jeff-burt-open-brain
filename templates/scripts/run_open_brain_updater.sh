#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
VAULT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$VAULT_ROOT"

echo "Open Brain updater preflight..."
sh scripts/run_open_brain_checks.sh
echo
echo "Preflight passed."
echo
echo "Use the following instruction bundle for the updater run:"
echo
echo "=== BEGIN OPEN BRAIN UPDATER CONTEXT ==="
echo
echo "--- FILE: CLAUDE.md ---"
cat "CLAUDE.md"
echo
echo "--- FILE: OPEN BRAIN UPDATER.md ---"
cat "OPEN BRAIN UPDATER.md"
echo
echo "--- FILE: entities-index.md ---"
cat "entities-index.md"
echo
echo "--- NOTES NEEDING PROCESSING ---"
echo "(filename|status|current_md5|stored_md5 — empty if none)"
python3 scripts/notes_to_process.py
echo
echo "--- DORMANT ENTITIES ---"
python3 scripts/list_dormant.py
echo
echo "Tip: per-paragraph alias shortlists are available via:"
echo "  python3 scripts/match_entities.py <note-path> --pretty"
echo
echo "=== END OPEN BRAIN UPDATER CONTEXT ==="
