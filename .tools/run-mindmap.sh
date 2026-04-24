#!/usr/bin/env bash
# run-mindmap.sh — Placeholder runner for scheduled mindmap generation.
# The `mindmap <topic>` trigger is handled in-conversation by Claude via CLAUDE.md.
# This script exists so schedule-mindmap.sh has something to call if the user wires
# a specific topic into the scheduled job.
set -e
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
echo "[run-mindmap] Vault: $VAULT"
echo "[run-mindmap] The mindmap trigger is interactive — run 'mindmap <topic>' inside Claude Code."
echo "[run-mindmap] To wire a recurring topic, edit this script to pass --topic to discover.py or call Claude headlessly."
