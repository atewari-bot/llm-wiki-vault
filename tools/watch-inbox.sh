#!/usr/bin/env bash
# watch-inbox.sh — Watch raw/inbox/ and auto-ingest new files into wiki/
#
# Usage:
#   bash tools/watch-inbox.sh            # watch and build on new files
#   bash tools/watch-inbox.sh --dry-run  # watch but preview only

set -e
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
INBOX="$VAULT/raw/inbox"
VENV="$VAULT/tools/.venv/bin/python"
BUILDER="$VAULT/tools/knowledge_graph_builder.py"
LOG="$VAULT/tools/watch.log"
DRY_RUN=""

for arg in "$@"; do
  [[ $arg == "--dry-run" ]] && DRY_RUN="--dry-run"
done

if [ ! -d "$INBOX" ]; then echo "❌ raw/inbox/ not found"; exit 1; fi
if [ ! -f "$VENV" ];  then echo "❌ Run: bash tools/setup.sh first"; exit 1; fi
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$DRY_RUN" ]; then
  echo "❌ ANTHROPIC_API_KEY not set"; exit 1
fi

run_ingest() {
  local file="$1"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📥 $(date '+%H:%M:%S')  New: $(basename "$file")"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  sleep 3
  [ -f "$file" ] || return
  "$VENV" "$BUILDER" \
    --vault "$VAULT" \
    --inbox-only \
    --mark-processed \
    $DRY_RUN \
    2>&1 | tee -a "$LOG"
  echo "⏳ Watching raw/inbox/..."
}

echo "👁  Watching: $INBOX"
echo "📋 Log: $LOG"
echo "🛑 Ctrl+C to stop"
echo "⏳ Watching raw/inbox/..."

if command -v fswatch &>/dev/null; then
  fswatch -0 --event Created --event MovedTo \
    --include '\.md$' --extended "$INBOX" | \
  while IFS= read -r -d "" file; do
    run_ingest "$file"
  done
else
  "$VENV" -c "
import sys, time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

vault = '$VAULT'
inbox = '$INBOX'
builder = '$BUILDER'
venv_py = '$VENV'
dry = '$DRY_RUN'

class Handler(FileSystemEventHandler):
    def _handle(self, path):
        if path.endswith('.md') and not Path(path).name.startswith('.'):
            time.sleep(3)
            if not Path(path).exists(): return
            cmd = [venv_py, builder, '--vault', vault,
                   '--inbox-only', '--mark-processed']
            if dry: cmd.append('--dry-run')
            subprocess.run(cmd)
            print('⏳ Watching raw/inbox/...')
    def on_created(self, e):
        if not e.is_directory: self._handle(e.src_path)
    def on_moved(self, e):
        if not e.is_directory: self._handle(e.dest_path)

obs = Observer()
obs.schedule(Handler(), inbox, recursive=False)
obs.start()
try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    obs.stop()
obs.join()
"
fi
