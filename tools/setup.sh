#!/usr/bin/env bash
# setup.sh — One-command setup for LLM Wiki Vault on Mac or Linux

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_DIR="$VAULT/tools"
VENV_DIR="$TOOLS_DIR/.venv"

echo ""
echo "LLM Wiki Vault — Setup"
echo "======================"
echo "Vault: $VAULT"
echo ""

# Python check
if ! command -v python3 &>/dev/null; then
  echo "ERR Python 3 not found. Install from https://python.org"
  exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "OK  Python $PY_VER"

# Claude Code check
if command -v claude &>/dev/null; then
  echo "OK  Claude Code found"
else
  echo "WARN Claude Code not found. Install: npm install -g @anthropic-ai/claude-code"
fi

# Virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$TOOLS_DIR/requirements.txt"
echo "OK  Packages installed (anthropic, networkx, watchdog, python-dotenv, slack-sdk)"

# .env check
echo ""
if [ ! -f "$TOOLS_DIR/.env" ]; then
  echo "WARN tools/.env not found — template already included, edit it now"
else
  echo "OK  tools/.env found"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "WARN ANTHROPIC_API_KEY not set in environment."
  echo "     Add it to tools/.env (ANTHROPIC_API_KEY=sk-ant-...)"
  echo "     Note: Do NOT export it in the same shell as 'claude' to avoid auth conflicts"
else
  echo "OK  ANTHROPIC_API_KEY found in environment"
fi

# Done
echo ""
echo "Setup complete!"
echo ""
echo "Commands:"
echo "  cd '$VAULT' && claude              # start Claude Code"
echo "  bash tools/build-graph.sh         # build knowledge graph"
echo "  bash tools/run-daily.sh           # generate daily briefing"
echo "  bash tools/run-daily.sh --no-slack  # skip Slack fetch"
echo "  bash tools/watch-inbox.sh         # auto-watch inbox"
echo "  bash tools/run-slack-ingest.sh    # fetch Slack (requires SLACK_BOT_TOKEN)"
echo "  bash tools/run-slack-channels.sh list  # manage channels"
echo "  bash tools/schedule.sh install    # periodic auto-builds"
echo ""
echo "Auth note:"
echo "  Claude Code uses your claude.ai login — no API key export needed."
echo "  Python tools use ANTHROPIC_API_KEY from tools/.env — NOT from shell env."
echo "  Do not export ANTHROPIC_API_KEY in the same terminal you run 'claude'."
echo ""
