#!/usr/bin/env bash
# run-slack-ingest.sh — Fetch Slack messages into raw/slack/ sidecars
# Usage:
#   bash tools/run-slack-ingest.sh                    # last 24h
#   bash tools/run-slack-ingest.sh --hours 48         # last 48h
#   bash tools/run-slack-ingest.sh --since 2026-04-14 # from a date
#   bash tools/run-slack-ingest.sh --dry-run          # preview only
#
# Requires: SLACK_BOT_TOKEN in tools/.env
# Without bot token: use Cowork/Claude to fetch Slack via MCP instead

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/tools/.venv/bin/activate"
python "$VAULT/tools/slack_ingest.py" --vault "$VAULT" "$@"
