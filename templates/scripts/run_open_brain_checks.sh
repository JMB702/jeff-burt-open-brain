#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
VAULT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$VAULT_ROOT"
python3 scripts/validate_open_brain.py "$@"

# Regenerate AGENTS.md from CLAUDE.md (fails if drift would occur; --fix regenerates)
case " $* " in
    *" --fix "*) python3 scripts/generate_agents_md.py ;;
    *)           python3 scripts/generate_agents_md.py --check ;;
esac

# Regenerate entity index after successful validation
python3 scripts/build_entity_index.py
