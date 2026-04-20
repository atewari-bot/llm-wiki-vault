#!/usr/bin/env bash
# run-weekly.sh — Generate weekly review
# Usage: bash tools/run-weekly.sh

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/tools/.venv/bin/activate"
python "$VAULT/tools/weekly.py" --vault "$VAULT" "$@"
