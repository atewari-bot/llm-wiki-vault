#!/usr/bin/env bash
# run-daily.sh — Generate today's daily briefing
# Usage:
#   bash tools/run-daily.sh              # with calendar
#   bash tools/run-daily.sh --no-calendar  # offline

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/tools/.venv/bin/activate"
python "$VAULT/tools/daily.py" --vault "$VAULT" "$@"
# Flags: --no-calendar (offline), --no-slack (skip Slack fetch), --date YYYY-MM-DD
