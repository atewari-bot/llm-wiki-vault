#!/usr/bin/env bash
# build-graph.sh — Build knowledge graph from raw/ → write directly to wiki/
# Usage:
#   bash .tools/build-graph.sh                    # all of raw/
#   bash .tools/build-graph.sh --inbox-only       # inbox only
#   bash .tools/build-graph.sh --dry-run          # preview only
#   bash .tools/build-graph.sh --drawio file.xml  # include diagram

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/.tools/.venv/bin/activate"

python "$VAULT/.tools/knowledge_graph_builder.py" \
  --vault "$VAULT" \
  "$@"
