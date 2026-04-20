#!/usr/bin/env bash
# run-slack-channels.sh — Manage monitored Slack channels
# Usage:
#   bash tools/run-slack-channels.sh list
#   bash tools/run-slack-channels.sh add CXXXXXXXXXX
#   bash tools/run-slack-channels.sh add general
#   bash tools/run-slack-channels.sh remove CXXXXXXXXXX
#   bash tools/run-slack-channels.sh search engineering

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/tools/.venv/bin/activate"
python "$VAULT/tools/slack_channels.py" "$@"
