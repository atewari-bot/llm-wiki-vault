#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/.tools/.venv/bin/activate"
echo "[run-eod] Vault: $VAULT"
python "$VAULT/.tools/eod.py" --vault "$VAULT" "$@"
