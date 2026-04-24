#!/usr/bin/env bash
# run-discover.sh — Find non-obvious connections across the wiki
# Usage:
#   bash .tools/run-discover.sh
#   bash .tools/run-discover.sh --dry-run

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/.tools/.venv/bin/activate"
python "$VAULT/.tools/discover.py" --vault "$VAULT" "$@"
