#!/usr/bin/env python3
"""gcal.py — Headless Google Calendar reader. Used by daily.py."""
import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
TOKEN_FILE = TOOLS_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def is_configured() -> bool:
    return TOKEN_FILE.exists()


def fetch_events(date_str: str, calendar_id: str = "primary") -> list:
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError("Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    if not TOKEN_FILE.exists():
        raise RuntimeError(f"No OAuth token at {TOKEN_FILE}. Run: python .tools/gcal_auth.py")
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        else:
            raise RuntimeError("Token expired. Run: python .tools/gcal_auth.py")
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    date_dt = datetime.strptime(date_str, "%Y-%m-%d")
    time_min = (date_dt - timedelta(hours=12)).replace(tzinfo=timezone.utc)
    time_max = (date_dt + timedelta(hours=36)).replace(tzinfo=timezone.utc)
    result = service.events().list(
        calendarId=calendar_id, timeMin=time_min.isoformat(), timeMax=time_max.isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute()
    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})
        start_raw = start.get("dateTime", start.get("date", ""))
        end_raw = end.get("dateTime", end.get("date", ""))
        try:
            start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            time_fmt = start_dt.astimezone().strftime("%H:%M")
            if start_dt.astimezone().strftime("%Y-%m-%d") != date_str:
                continue
        except (ValueError, AttributeError):
            time_fmt = "All day"
        try:
            end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
            end_fmt = end_dt.astimezone().strftime("%H:%M")
        except (ValueError, AttributeError):
            end_fmt = ""
        events.append({"time": time_fmt, "end": end_fmt, "title": item.get("summary", "Untitled"),
                       "description": item.get("description", "")})
    events.sort(key=lambda e: e["time"])
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    from datetime import date
    date_str = args.date or date.today().isoformat()
    if not is_configured():
        print("❌ Not configured. Run: python .tools/gcal_auth.py")
        sys.exit(1)
    try:
        events = fetch_events(date_str)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    if args.json:
        print(json.dumps(events, indent=2))
    else:
        print(f"📅 Events for {date_str} ({len(events)} found):")
        for ev in events:
            time_range = f"{ev['time']}–{ev['end']}" if ev["end"] else ev["time"]
            print(f"  {time_range}  {ev['title']}")


if __name__ == "__main__":
    main()
