#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/.tools/.venv/bin/activate"
echo "[run-weekly] Vault: $VAULT"
python "$VAULT/.tools/weekly.py" --vault "$VAULT" "$@"
