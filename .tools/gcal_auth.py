#!/usr/bin/env python3
"""
gcal_auth.py — One-time Google Calendar OAuth setup.
Creates .tools/token.json for headless daily briefings.
Usage: python .tools/gcal_auth.py
"""
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
CLIENT_SECRET = TOOLS_DIR / "client_secret.json"
TOKEN_FILE = TOOLS_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("❌ Run: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)
    if not CLIENT_SECRET.exists():
        print(f"❌ {CLIENT_SECRET} not found. Download OAuth credentials from Google Cloud Console.")
        sys.exit(1)
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None
    if creds and creds.valid:
        print(f"✅ Token already valid — {TOKEN_FILE}")
        return
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
            print("✅ Token refreshed")
            return
        except Exception as e:
            print(f"[gcal_auth] Refresh failed ({e}) — re-authorising...")
            creds = None
    print("Opening browser for Google Calendar authorization...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())
    print(f"✅ Token saved → {TOKEN_FILE}")
    print("Run: bash .tools/run-daily.sh")


if __name__ == "__main__":
    main()
