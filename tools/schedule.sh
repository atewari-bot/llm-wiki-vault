#!/usr/bin/env bash
# schedule.sh — Set up periodic knowledge graph builds
#
# Creates either:
#   (a) a cron job  — runs at set intervals silently in background
#   (b) a launchd plist (Mac) — more reliable, survives reboots
#
# Usage:
#   bash tools/schedule.sh install    # install schedule
#   bash tools/schedule.sh remove     # remove schedule
#   bash tools/schedule.sh status     # check if running
#   bash tools/schedule.sh run-now    # trigger manually

set -e

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$VAULT/tools/.venv/bin/python"
BUILDER="$VAULT/tools/knowledge_graph_builder.py"
LOG="$VAULT/tools/schedule.log"
PLIST_NAME="com.llmwiki.build-graph"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

COMMAND="$VENV $BUILDER --vault $VAULT --output $VAULT/tools/output --mark-processed"
MERGE="echo done"

ACTION="${1:-help}"

# ── Install ───────────────────────────────────────────────────
install_schedule() {
  echo ""
  echo "How often should the knowledge graph build?"
  echo "  1) Every 30 minutes"
  echo "  2) Every hour"
  echo "  3) Every 6 hours"
  echo "  4) Daily at 9am"
  echo "  5) Daily at midnight"
  read -p "Choose [1-5]: " choice

  case $choice in
    1) INTERVAL=1800;  LABEL="every 30 min" ;;
    2) INTERVAL=3600;  LABEL="every hour" ;;
    3) INTERVAL=21600; LABEL="every 6 hours" ;;
    4) INTERVAL=86400; LABEL="daily at 9am"; HOUR=9 ;;
    5) INTERVAL=86400; LABEL="daily at midnight"; HOUR=0 ;;
    *) echo "Invalid choice"; exit 1 ;;
  esac

  if [[ "$OSTYPE" == "darwin"* ]]; then
    install_launchd
  else
    install_cron
  fi

  echo ""
  echo "✅ Schedule installed: $LABEL"
  echo "📋 Log file: $LOG"
  echo ""
  echo "Commands:"
  echo "  bash tools/schedule.sh status    # check status"
  echo "  bash tools/schedule.sh run-now   # trigger now"
  echo "  bash tools/schedule.sh remove    # uninstall"
}

install_launchd() {
  # Generate plist
  if [ -n "$HOUR" ]; then
    START_INTERVAL=""
    START_CAL="
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>$HOUR</integer>
        <key>Minute</key><integer>0</integer>
    </dict>"
  else
    START_INTERVAL="<key>StartInterval</key><integer>$INTERVAL</integer>"
    START_CAL=""
  fi

  cat > "$PLIST_PATH" << XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>$COMMAND &amp;&amp; $MERGE</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>$ANTHROPIC_API_KEY</string>
    </dict>
    $START_INTERVAL
    $START_CAL
    <key>StandardOutPath</key>
    <string>$LOG</string>
    <key>StandardErrorPath</key>
    <string>$LOG</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
XML

  launchctl unload "$PLIST_PATH" 2>/dev/null || true
  launchctl load "$PLIST_PATH"
  echo "📌 launchd agent installed: $PLIST_NAME"
}

install_cron() {
  if [ -n "$HOUR" ]; then
    CRON_EXPR="0 $HOUR * * *"
  else
    MINS=$((INTERVAL / 60))
    CRON_EXPR="*/$MINS * * * *"
  fi

  CRON_LINE="$CRON_EXPR $COMMAND >> $LOG 2>&1 && $MERGE"
  (crontab -l 2>/dev/null | grep -v "$BUILDER"; echo "$CRON_LINE") | crontab -
  echo "📌 Cron job installed: $CRON_EXPR"
}

# ── Remove ────────────────────────────────────────────────────
remove_schedule() {
  if [[ "$OSTYPE" == "darwin"* ]] && [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm "$PLIST_PATH"
    echo "✅ launchd agent removed"
  fi

  # Remove cron entries too
  crontab -l 2>/dev/null | grep -v "$BUILDER" | crontab - 2>/dev/null && \
    echo "✅ Cron entries removed" || true

  echo "Schedule removed."
}

# ── Status ────────────────────────────────────────────────────
show_status() {
  echo ""
  echo "📋 Schedule Status"
  echo "─────────────────"

  if [[ "$OSTYPE" == "darwin"* ]] && [ -f "$PLIST_PATH" ]; then
    echo "launchd: ✅ installed"
    launchctl list | grep "$PLIST_NAME" || echo "  (not currently loaded)"
  else
    echo "launchd: not installed"
  fi

  CRON=$(crontab -l 2>/dev/null | grep "$BUILDER" || true)
  if [ -n "$CRON" ]; then
    echo "cron:    ✅ $CRON"
  else
    echo "cron:    not installed"
  fi

  echo ""
  if [ -f "$LOG" ]; then
    echo "📄 Last 10 log lines ($LOG):"
    tail -10 "$LOG"
  else
    echo "No log file yet."
  fi
}

# ── Run now ───────────────────────────────────────────────────
run_now() {
  echo "🔄 Running knowledge graph build now..."
  eval "$COMMAND" && eval "$MERGE"
  echo "✅ Done. Check tools/output/ for results."
}

# ── Dispatch ──────────────────────────────────────────────────
case $ACTION in
  install)  install_schedule ;;
  remove)   remove_schedule ;;
  status)   show_status ;;
  run-now)  run_now ;;
  *)
    echo "Usage: bash tools/schedule.sh [install|remove|status|run-now]"
    echo ""
    echo "  install   Set up periodic automatic graph builds"
    echo "  remove    Remove the schedule"
    echo "  status    Show current schedule and recent log"
    echo "  run-now   Trigger a build immediately"
    ;;
esac