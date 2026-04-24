#!/usr/bin/env bash
# schedule-discover.sh — Manages daily 6:00 AM discover run
# Usage: bash .tools/schedule-discover.sh install|remove|status|run-now
set -e
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS="$VAULT/.tools"
PLIST_ID="com.llm-wiki-vault.discover"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_ID.plist"
LOG="$TOOLS/discover.log"
RUNNER="$TOOLS/run-discover.sh"
OS=$(uname -s)
case "${1:-}" in
install)
    if [ "$OS" = "Darwin" ]; then
        mkdir -p "$HOME/Library/LaunchAgents"
        cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$PLIST_ID</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$RUNNER</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  <key>EnvironmentVariables</key>
  <dict><key>ANTHROPIC_API_KEY</key><string>$ANTHROPIC_API_KEY</string></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLIST
        launchctl load "$PLIST_PATH" 2>/dev/null || launchctl bootstrap gui/$(id -u) "$PLIST_PATH" 2>/dev/null || true
        echo "OK  discover installed — fires daily at 6:00 AM"
    else
        (crontab -l 2>/dev/null; echo "0 6 * * * /bin/bash $RUNNER >> $LOG 2>&1") | crontab -
        echo "OK  Crontab entry added"
    fi ;;
remove)
    if [ "$OS" = "Darwin" ] && [ -f "$PLIST_PATH" ]; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true; rm -f "$PLIST_PATH"
        echo "OK  discover job removed"
    else
        crontab -l 2>/dev/null | grep -v "$RUNNER" | crontab - 2>/dev/null || true
    fi ;;
status)
    echo "=== discover Schedule Status ==="
    [ -f "$PLIST_PATH" ] && launchctl list "$PLIST_ID" 2>/dev/null || echo "Not installed"
    echo ""; echo "=== Last 10 lines of $LOG ==="
    [ -f "$LOG" ] && tail -n 10 "$LOG" || echo "(no log yet)" ;;
run-now) bash "$RUNNER" ;;
*) echo "Usage: bash .tools/schedule-discover.sh install|remove|status|run-now"; exit 1 ;;
esac
