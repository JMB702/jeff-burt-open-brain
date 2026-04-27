#!/bin/sh
# Compare every file in the setup bundle (`Open brain set up/templates/`) to its
# counterpart in the live vault / home config. Print drift so the vault owner
# can see what changes haven't been synced to the public setup bundle yet.
#
# Mappings:
#   templates/vault/OPEN-BRAIN-UPDATER.md  -> <VAULT>/OPEN BRAIN UPDATER.md  (hyphen -> space)
#   templates/vault/<rest>                 -> <VAULT>/<rest>
#   templates/scripts/<X>                  -> <VAULT>/scripts/<X>
#   templates/githooks/<X>                 -> <VAULT>/.githooks/<X>
#   templates/claude/settings.local.json   -> <VAULT>/.claude/settings.local.json
#   templates/claude/skills/<X>            -> <VAULT>/.claude/skills/<X>
#   templates/claude/global-claude-md-section.md -> snippet of $HOME/.claude/CLAUDE.md  (skipped — snippet, not file)
#   templates/scheduled-task/<X>           -> $HOME/.claude/scheduled-tasks/open-brain-updater/<X>
#
# Note: setup.sh substitutes placeholders like $VAULT_PATH when installing, so
# some diffs in settings/skills files are expected artifacts, not real drift.
# Eyeball the diff — real changes are obvious.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES="$VAULT_ROOT/Open brain set up/templates"

if [ ! -d "$TEMPLATES" ]; then
    echo "error: no setup templates at $TEMPLATES" >&2
    exit 1
fi

resolve_live_path() {
    rel="$1"
    case "$rel" in
        vault/OPEN-BRAIN-UPDATER.md)
            printf '%s/%s' "$VAULT_ROOT" "OPEN BRAIN UPDATER.md" ;;
        vault/*)
            printf '%s/%s' "$VAULT_ROOT" "${rel#vault/}" ;;
        scripts/*)
            printf '%s/%s' "$VAULT_ROOT" "$rel" ;;
        githooks/*)
            printf '%s/.githooks/%s' "$VAULT_ROOT" "${rel#githooks/}" ;;
        claude/global-claude-md-section.md)
            ;; # snippet, not a 1:1 file — skip
        claude/settings.local.json)
            printf '%s/.claude/settings.local.json' "$VAULT_ROOT" ;;
        claude/skills/*)
            printf '%s/.claude/%s' "$VAULT_ROOT" "${rel#claude/}" ;;
        scheduled-task/*)
            printf '%s/.claude/scheduled-tasks/open-brain-updater/%s' "$HOME" "${rel#scheduled-task/}" ;;
    esac
}

# Stash running counts in a tmp file — the while-read subshell can't update
# parent-shell variables on all POSIX shells.
TMPCOUNT="$(mktemp -t ob_diff_counts.XXXXXX)"
trap 'rm -f "$TMPCOUNT"' EXIT
printf '0 0 0 0\n' >"$TMPCOUNT"

# Pass 1: every template file -> live counterpart.
find "$TEMPLATES" -type f ! -name '.DS_Store' ! -path '*/__pycache__/*' | sort | while IFS= read -r tmpl; do
    rel="${tmpl#$TEMPLATES/}"
    live="$(resolve_live_path "$rel" || true)"
    read -r d m o s <"$TMPCOUNT"

    if [ -z "$live" ]; then
        s=$((s + 1))
        printf '%d %d %d %d\n' "$d" "$m" "$o" "$s" >"$TMPCOUNT"
        continue
    fi

    if [ ! -f "$live" ]; then
        printf '=== MISSING IN LIVE VAULT ===\n  template: %s\n  expected: %s\n\n' "$rel" "$live"
        m=$((m + 1))
        printf '%d %d %d %d\n' "$d" "$m" "$o" "$s" >"$TMPCOUNT"
        continue
    fi

    if ! diff -q "$live" "$tmpl" >/dev/null 2>&1; then
        printf '=== DRIFT: %s ===\n' "$rel"
        printf '  live:   %s\n' "$live"
        printf '  bundle: %s\n' "$tmpl"
        diff -u "$tmpl" "$live" | head -80
        printf '\n'
        d=$((d + 1))
        printf '%d %d %d %d\n' "$d" "$m" "$o" "$s" >"$TMPCOUNT"
    fi
done

# Pass 2: files that exist in live but not in the bundle (potential additions).
find "$VAULT_ROOT/scripts" -maxdepth 1 -type f \( -name '*.py' -o -name '*.sh' \) | sort | while IFS= read -r live_script; do
    name="$(basename "$live_script")"
    if [ ! -f "$TEMPLATES/scripts/$name" ]; then
        printf '=== ONLY IN LIVE (scripts/) ===\n  %s\n\n' "$name"
        read -r d m o s <"$TMPCOUNT"
        o=$((o + 1))
        printf '%d %d %d %d\n' "$d" "$m" "$o" "$s" >"$TMPCOUNT"
    fi
done

if [ -d "$VAULT_ROOT/.claude/skills" ]; then
    find "$VAULT_ROOT/.claude/skills" -maxdepth 1 -mindepth 1 -type d | sort | while IFS= read -r live_skill_dir; do
        name="$(basename "$live_skill_dir")"
        if [ ! -f "$TEMPLATES/claude/skills/$name/SKILL.md" ]; then
            printf '=== ONLY IN LIVE (.claude/skills/) ===\n  %s\n\n' "$name"
            read -r d m o s <"$TMPCOUNT"
            o=$((o + 1))
            printf '%d %d %d %d\n' "$d" "$m" "$o" "$s" >"$TMPCOUNT"
        fi
    done
fi

read -r drift_count missing_count only_in_live_count skipped_count <"$TMPCOUNT"

printf '===============================\n'
printf 'Summary: %d drifted, %d missing in live, %d only in live\n' \
    "$drift_count" "$missing_count" "$only_in_live_count"
if [ "$skipped_count" -gt 0 ]; then
    printf '(%d template files skipped — snippet-based or unmapped)\n' "$skipped_count"
fi

if [ "$drift_count" -eq 0 ] && [ "$missing_count" -eq 0 ] && [ "$only_in_live_count" -eq 0 ]; then
    printf 'Clean — setup bundle matches live vault.\n'
fi
