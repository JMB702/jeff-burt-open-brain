#!/usr/bin/env python3
"""Generate AGENTS.md from CLAUDE.md.

AGENTS.md is a convention some agent tools (Codex, others) read instead of
CLAUDE.md. Keeping a hand-written copy drifts; this script writes AGENTS.md
with the same content as CLAUDE.md plus a generated-file header.

Usage:
    python3 scripts/generate_agents_md.py           # write AGENTS.md
    python3 scripts/generate_agents_md.py --check   # exit 1 if AGENTS.md is stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = VAULT_ROOT / "CLAUDE.md"
TARGET = VAULT_ROOT / "AGENTS.md"

HEADER = (
    "<!-- Auto-generated from CLAUDE.md by scripts/generate_agents_md.py — do not edit directly. -->\n"
    "<!-- To update, edit CLAUDE.md and run `python3 scripts/generate_agents_md.py`. -->\n\n"
)


def render() -> str:
    return HEADER + SOURCE.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if AGENTS.md is out of date.")
    args = parser.parse_args()

    expected = render()

    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != expected:
            sys.stderr.write(
                "AGENTS.md is out of date. Run: python3 scripts/generate_agents_md.py\n"
            )
            return 1
        return 0

    TARGET.write_text(expected, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(VAULT_ROOT)} ({len(expected)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
