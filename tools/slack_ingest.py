#!/usr/bin/env python3
"""
slack_ingest.py — Ingest Slack messages into raw/slack/ sidecars.

Usage:
  python tools/slack_ingest.py --vault ~/llm-wiki-vault
  python tools/slack_ingest.py --vault ~/llm-wiki-vault --hours 48
  python tools/slack_ingest.py --vault ~/llm-wiki-vault --since 2026-04-14
  python tools/slack_ingest.py --vault ~/llm-wiki-vault --dry-run

Requires SLACK_BOT_TOKEN in tools/.env.
Without a bot token: use Cowork/Claude MCP to fetch Slack and write the same
sidecars manually — daily.py and weekly.py read from sidecars regardless.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


# ─────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────

ACTION_PATTERNS = [
    r"\bplease\b", r"\bfollow.?up\b", r"\baction item\b",
    r"\btodo\b", r"\bdeadline\b", r"\bneed to\b",
    r"\bwe should\b", r"\bcan you\b", r"\bcould you\b",
    r"\bby eod\b", r"\bby tomorrow\b", r"\bby end of day\b",
]


def _score_message(text: str, my_user_id: str = "") -> int:
    score = 0
    lower = text.lower()

    # Action patterns
    for pat in ACTION_PATTERNS:
        if re.search(pat, lower):
            score += 2
            break  # only count once for action patterns

    # @mention of self
    if my_user_id and f"<@{my_user_id}>" in text:
        score += 2
    # @mention of anyone
    elif re.search(r"<@U[A-Z0-9]+>", text):
        score += 1

    # Ends with question
    stripped = text.strip().rstrip("*_~`")
    if stripped.endswith("?"):
        score += 1

    # Too short
    words = len(text.split())
    if words < 4:
        score -= 1

    return score


def _clean_slack_text(text: str) -> str:
    """Strip Slack markup: <@U...>, <#C...>, <url|text>, :emoji:"""
    text = re.sub(r"<@U[A-Z0-9]+>", "@user", text)
    text = re.sub(r"<#C[A-Z0-9]+\|([^>]+)>", r"#\1", text)
    text = re.sub(r"<([^|>]+)\|([^>]+)>", r"\2", text)
    text = re.sub(r"<([^>]+)>", r"\1", text)
    text = re.sub(r":[a-z_]+:", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─────────────────────────────────────────────────────────────
# Slack client
# ─────────────────────────────────────────────────────────────

def _get_client():
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "SLACK_BOT_TOKEN not set in tools/.env\n"
            "Without a bot token, use Cowork or Claude to fetch Slack via MCP.\n"
            "Required scopes: channels:history, channels:read, users:read, groups:history"
        )
    try:
        from slack_sdk import WebClient
        return WebClient(token=token)
    except ImportError:
        raise RuntimeError("slack-sdk not installed. Run: pip install slack-sdk")


def _get_channel_name(client, channel_id: str) -> str:
    try:
        resp = client.conversations_info(channel=channel_id)
        return resp["channel"].get("name", channel_id)
    except Exception:
        return channel_id


def _fetch_user_name(client, user_id: str, cache: dict) -> str:
    if user_id in cache:
        return cache[user_id]
    try:
        resp = client.users_info(user=user_id)
        name = (
            resp["user"].get("profile", {}).get("display_name")
            or resp["user"].get("real_name")
            or user_id
        )
        cache[user_id] = name
        return name
    except Exception:
        cache[user_id] = user_id
        return user_id


def _fetch_messages(client, channel_id: str, oldest_ts: float, latest_ts: float) -> list:
    messages = []
    cursor = None
    while True:
        kwargs = {
            "channel": channel_id,
            "oldest": str(oldest_ts),
            "latest": str(latest_ts),
            "limit": 200,
        }
        if cursor:
            kwargs["cursor"] = cursor
        try:
            resp = client.conversations_history(**kwargs)
        except Exception as e:
            print(f"   Error fetching messages: {e}")
            break
        messages.extend(resp.get("messages", []))
        meta = resp.get("response_metadata", {})
        cursor = meta.get("next_cursor")
        if not cursor:
            break
        time.sleep(0.5)
    return messages


# ─────────────────────────────────────────────────────────────
# Ingestion
# ─────────────────────────────────────────────────────────────

def ingest_channel(client, channel_id: str, oldest_ts: float, latest_ts: float,
                   my_user_id: str, dry_run: bool = False) -> dict:
    channel_name = _get_channel_name(client, channel_id)
    raw_msgs     = _fetch_messages(client, channel_id, oldest_ts, latest_ts)
    user_cache   = {}

    action_items = []
    raw_messages = []

    for msg in raw_msgs:
        if msg.get("subtype"):  # skip join/leave/etc
            continue
        text = _clean_slack_text(msg.get("text", ""))
        if not text:
            continue

        user_id   = msg.get("user", "")
        sender    = _fetch_user_name(client, user_id, user_cache) if user_id else "Unknown"
        ts        = float(msg.get("ts", 0))
        ts_human  = datetime.utcfromtimestamp(ts).strftime("%H:%M UTC")
        score     = _score_message(text, my_user_id)

        raw_messages.append({"text": text, "sender": sender, "ts_human": ts_human})

        if score >= 2:
            action_items.append({
                "text":     text,
                "sender":   sender,
                "ts_human": ts_human,
                "score":    score,
                "channel":  channel_name,
            })

    return {
        "channel_id":    channel_id,
        "channel_name":  channel_name,
        "message_count": len(raw_messages),
        "action_items":  sorted(action_items, key=lambda x: x["score"], reverse=True),
        "raw_messages":  raw_messages,
    }


def save_results(results: list, vault: Path, date_str: str, dry_run: bool = False) -> list:
    saved = []
    for r in results:
        ch_name  = r["channel_name"]
        out_dir  = vault / "raw" / "slack" / date_str / ch_name
        md_path  = out_dir / "digest.md"
        json_path = out_dir / "data.json"

        if dry_run:
            print(f"   [DRY RUN] Would write: {md_path}")
            print(f"   [DRY RUN] Would write: {json_path}")
            continue

        out_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON sidecar
        json_path.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")

        # Write markdown digest
        lines = [
            "---",
            f'title: "Slack Digest — #{ch_name} — {date_str}"',
            f"date: {date_str}",
            f"channel: {ch_name}",
            f"channel_id: {r['channel_id']}",
            "type: slack-digest",
            "processed: false",
            "---",
            "",
            f"# #{ch_name} — {date_str}",
            f"*{r['message_count']} messages scanned · {len(r['action_items'])} action items*",
            "",
        ]

        if r["action_items"]:
            lines += ["## Action items", ""]
            for item in r["action_items"]:
                lines.append(f"- [ ] {item['text']} *(via {item['sender']}, score: {item['score']})*")
            lines.append("")

        if r["raw_messages"]:
            lines += ["## Message log", ""]
            for msg in r["raw_messages"][:50]:  # cap at 50 for readability
                lines.append(f"- **{msg['sender']}** ({msg['ts_human']}): {msg['text'][:200]}")
            lines.append("")

        md_path.write_text("\n".join(lines), encoding="utf-8")
        saved.append(md_path)

    return saved


# ─────────────────────────────────────────────────────────────
# Public API for daily.py / weekly.py
# ─────────────────────────────────────────────────────────────

def fetch_slack_todos(vault: Path, date_str: str) -> list:
    """Read today's JSON sidecars and return all action items."""
    slack_dir = vault / "raw" / "slack" / date_str
    if not slack_dir.exists():
        return []

    items = []
    for json_path in slack_dir.rglob("data.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            items.extend(data.get("action_items", []))
        except Exception:
            pass

    return items


def fetch_slack_weekly_stats(vault: Path, monday_str: str, today_str: str) -> dict:
    """Aggregate week's Slack stats from all sidecars."""
    monday = date.fromisoformat(monday_str)
    today  = date.fromisoformat(today_str)

    stats = {
        "channels":     set(),
        "messages":     0,
        "action_items": 0,
        "unresolved":   0,
    }

    current = monday
    while current <= today:
        slack_dir = vault / "raw" / "slack" / current.isoformat()
        if slack_dir.exists():
            for json_path in slack_dir.rglob("data.json"):
                try:
                    data = json.loads(json_path.read_text(encoding="utf-8"))
                    stats["channels"].add(data.get("channel_name", "unknown"))
                    stats["messages"]     += data.get("message_count", 0)
                    stats["action_items"] += len(data.get("action_items", []))
                except Exception:
                    pass
        current += timedelta(days=1)

    stats["channels"] = list(stats["channels"])
    return stats


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest Slack messages into vault")
    parser.add_argument("--vault",    required=True)
    parser.add_argument("--hours",    type=int, default=None)
    parser.add_argument("--since",    default=None, help="YYYY-MM-DD")
    parser.add_argument("--channels", default=None, help="Comma-separated channel IDs")
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()

    vault      = Path(args.vault).expanduser().resolve()
    today_str  = date.today().isoformat()
    now_ts     = time.time()

    # Determine lookback
    lookback_hours = args.hours or int(os.environ.get("SLACK_LOOKBACK_HOURS", "24"))
    if args.since:
        since_dt  = datetime.fromisoformat(args.since)
        oldest_ts = since_dt.timestamp()
    else:
        oldest_ts = now_ts - (lookback_hours * 3600)

    # Determine channels
    channel_ids_raw = args.channels or os.environ.get("SLACK_CHANNEL_IDS", "")
    channel_ids     = [c.strip() for c in channel_ids_raw.split(",") if c.strip()]

    if not channel_ids:
        print("No channels configured. Add SLACK_CHANNEL_IDS to tools/.env")
        sys.exit(1)

    my_user_id = os.environ.get("SLACK_MY_USER_ID", "").strip()

    print(f"\nSlack ingest — {len(channel_ids)} channel(s), last {lookback_hours}h")

    try:
        client = _get_client()
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    results = []
    for ch_id in channel_ids:
        print(f"  Fetching #{ch_id}...")
        result = ingest_channel(client, ch_id, oldest_ts, now_ts, my_user_id, args.dry_run)
        results.append(result)
        print(f"  #{result['channel_name']} — {result['message_count']} messages, "
              f"{len(result['action_items'])} action items")

    saved = save_results(results, vault, today_str, args.dry_run)

    if not args.dry_run:
        print(f"\nSaved {len(saved)} files to raw/slack/{today_str}/")
        print("Say `daily` to include in today's briefing.")


if __name__ == "__main__":
    main()
