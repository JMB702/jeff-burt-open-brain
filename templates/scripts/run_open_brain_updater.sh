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

# Photos pipeline health check — surface stale index or missing osxphotos early.
# A silent failure here (e.g. Homebrew Python upgrade wiping osxphotos) means
# the daily index refresh in Step 2h is quietly not happening. We warn loudly
# so the session can flag it in the briefing instead of letting it sit for weeks.
PHOTOS_WARN=""
if ! python3 -c "import osxphotos" >/dev/null 2>&1; then
  PHOTOS_WARN="osxphotos is not importable by the current python3 ($(python3 --version 2>&1)). Step 2h will skip the index refresh silently. Fix: pip3 install osxphotos --break-system-packages (see Photos/README.md)."
elif [ -f "Photos/photos-index.json" ]; then
  AGE_HOURS=$(python3 -c "
import json
from datetime import datetime
try:
    d = json.load(open('Photos/photos-index.json'))
    gen = datetime.fromisoformat(d['generated_at'])
    age = (datetime.now(gen.tzinfo) - gen).total_seconds() / 3600
    print(int(age))
except Exception:
    print(-1)
" 2>/dev/null)
  if [ "$AGE_HOURS" -gt 36 ] 2>/dev/null; then
    PHOTOS_WARN="Photos index is ${AGE_HOURS} hours old — Step 2h should refresh it every ~24h but hasn't. Investigate: run 'python3 scripts/photos_update_index.py --verbose' and check for errors."
  fi
fi

if [ -n "$PHOTOS_WARN" ]; then
  echo "!!! PHOTOS PIPELINE WARNING !!!"
  echo "$PHOTOS_WARN"
  echo "Include this warning in the Slack briefing so {{USER_FIRST_NAME}} sees it."
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  echo
fi

# Ensure today's blank daily note exists (idempotent).
# The model doesn't need to remember this — the preflight handles it.
TODAY=$(date +%Y-%m-%d)
YEAR_DIR=$(date +%Y)
MONTH_DIR="$(date +%m)-$(date +%B)"
NOTE_REL="notes/raw-daily-notes/${YEAR_DIR}/${MONTH_DIR}/${TODAY}.md"
EMPTY_MD5="d41d8cd98f00b204e9800998ecf8427e"
MANIFEST="notes/.manifest"

if [ ! -f "$NOTE_REL" ]; then
  mkdir -p "$(dirname "$NOTE_REL")"
  touch "$NOTE_REL"
  NOTE_STATUS="created"
else
  NOTE_STATUS="exists"
fi

# If the note is empty, make sure the manifest has an entry so a future edit
# registers as "modified". If the note already has content, let notes_to_process
# surface it through the normal flow.
MANIFEST_STATUS="—"
if [ ! -s "$NOTE_REL" ] && ! grep -q "^${TODAY}.md|" "$MANIFEST" 2>/dev/null; then
  echo "${TODAY}.md|${EMPTY_MD5}" >> "$MANIFEST"
  MANIFEST_STATUS="added empty-hash entry"
fi

echo "--- TODAY'S NOTE ---"
echo "path: $NOTE_REL"
echo "status: $NOTE_STATUS"
echo "manifest: $MANIFEST_STATUS"
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
