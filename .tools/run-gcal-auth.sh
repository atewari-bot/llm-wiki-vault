#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$VAULT/.tools/.venv/bin/activate"
python -c "import googleapiclient" 2>/dev/null || pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client -q
python "$VAULT/.tools/gcal_auth.py"
