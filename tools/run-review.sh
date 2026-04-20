#!/usr/bin/env bash
# run-review.sh — Confidence decay review
# Usage:
#   bash tools/run-review.sh              # interactive
#   bash tools/run-review.sh --auto       # auto-downgrade, no prompts
#   bash tools/run-review.sh --dry-run    # preview only

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/tools/.venv/bin/activate"
python "$VAULT/tools/review.py" --vault "$VAULT" "$@"
