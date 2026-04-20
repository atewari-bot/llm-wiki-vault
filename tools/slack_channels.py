#!/usr/bin/env python3
"""
slack_channels.py — Manage monitored Slack channels in tools/.env

Usage:
  python tools/slack_channels.py list
  python tools/slack_channels.py add CXXXXXXXXXX
  python tools/slack_channels.py add general
  python tools/slack_channels.py remove CXXXXXXXXXX
  python tools/slack_channels.py search engineering
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)


# ─────────────────────────────────────────────────────────────
# .env helpers
# ─────────────────────────────────────────────────────────────

def _read_env_lines() -> list:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    return []


def _get_channel_ids() -> list:
    raw = os.environ.get("SLACK_CHANNEL_IDS", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def _set_channel_ids(ids: list):
    """Rewrite SLACK_CHANNEL_IDS in tools/.env, preserving all other lines."""
    lines  = _read_env_lines()
    new_val = ",".join(ids)
    found  = False
    new_lines = []

    for line in lines:
        if line.startswith("SLACK_CHANNEL_IDS="):
            new_lines.append(f"SLACK_CHANNEL_IDS={new_val}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"SLACK_CHANNEL_IDS={new_val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ["SLACK_CHANNEL_IDS"] = new_val


# ─────────────────────────────────────────────────────────────
# Slack client (optional)
# ─────────────────────────────────────────────────────────────

def _get_client():
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        return None
    try:
        from slack_sdk import WebClient
        return WebClient(token=token)
    except ImportError:
        return None


def _resolve_channel(client, id_or_name: str):
    """Resolve name or ID to (id, name). Returns (None, None) if not found."""
    if not client:
        # Without bot token, trust the ID as-is if it looks like one
        if re.match(r"^C[A-Z0-9]{8,}$", id_or_name):
            return id_or_name, id_or_name
        return None, None

    # Looks like an ID — verify it
    if re.match(r"^[A-Z][A-Z0-9]{8,}$", id_or_name):
        try:
            resp = client.conversations_info(channel=id_or_name)
            ch   = resp["channel"]
            return ch["id"], ch.get("name", id_or_name)
        except Exception:
            return None, None

    # Search by name
    try:
        cursor = None
        while True:
            kwargs = {"types": "public_channel,private_channel", "limit": 200}
            if cursor:
                kwargs["cursor"] = cursor
            resp   = client.conversations_list(**kwargs)
            for ch in resp.get("channels", []):
                if ch.get("name", "").lower() == id_or_name.lower():
                    return ch["id"], ch["name"]
            meta   = resp.get("response_metadata", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break
    except Exception:
        pass

    return None, None


def _search_channels(client, query: str, limit: int = 15) -> list:
    if not client:
        return []
    results = []
    cursor  = None
    try:
        while len(results) < limit:
            kwargs = {"types": "public_channel,private_channel", "limit": 200}
            if cursor:
                kwargs["cursor"] = cursor
            resp = client.conversations_list(**kwargs)
            for ch in resp.get("channels", []):
                name    = ch.get("name", "")
                topic   = ch.get("topic", {}).get("value", "")
                purpose = ch.get("purpose", {}).get("value", "")
                if query.lower() in (name + topic + purpose).lower():
                    results.append({
                        "id":      ch["id"],
                        "name":    name,
                        "members": ch.get("num_members", 0),
                        "topic":   topic[:60] or purpose[:60],
                    })
            meta   = resp.get("response_metadata", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break
    except Exception as e:
        print(f"Search error: {e}")
    return results[:limit]


# ─────────────────────────────────────────────────────────────
# Subcommands
# ─────────────────────────────────────────────────────────────

def cmd_list(args):
    ids    = _get_channel_ids()
    client = _get_client()

    print(f"\nMonitored Slack channels ({len(ids)}):")
    print(f"Config: {ENV_PATH}")
    print()

    if not ids:
        print("  (none configured)")
        print("\nAdd a channel: python tools/slack_channels.py add <channel-id>")
        return

    for ch_id in ids:
        if client:
            try:
                resp = client.conversations_info(channel=ch_id)
                name = resp["channel"].get("name", ch_id)
                print(f"  #{name} ({ch_id})")
            except Exception:
                print(f"  {ch_id} (could not resolve name)")
        else:
            print(f"  {ch_id}")

    if not client:
        print("\nNote: Add SLACK_BOT_TOKEN to tools/.env to resolve channel names.")


def cmd_add(args):
    id_or_name = args.channel
    current    = _get_channel_ids()
    client     = _get_client()

    ch_id, ch_name = _resolve_channel(client, id_or_name)

    if not ch_id:
        if not client:
            # No bot token — require ID format
            if re.match(r"^C[A-Z0-9]{8,}$", id_or_name):
                ch_id, ch_name = id_or_name, id_or_name
            else:
                print(f"Error: '{id_or_name}' doesn't look like a channel ID.")
                print("Without SLACK_BOT_TOKEN, you must provide a channel ID (e.g. CXXXXXXXXXX).")
                print("Find it in Slack: right-click channel → View channel details → copy Channel ID")
                sys.exit(1)
        else:
            print(f"Channel '{id_or_name}' not found in your workspace.")
            sys.exit(1)

    if ch_id in current:
        label = f"#{ch_name}" if ch_name != ch_id else ch_id
        print(f"{label} is already monitored.")
        return

    current.append(ch_id)
    _set_channel_ids(current)

    label = f"#{ch_name} ({ch_id})" if ch_name != ch_id else ch_id
    print(f"Added: {label}")
    print(f"Now monitoring {len(current)} channel(s).")
    print("\nRun `refresh slack` or `daily` to pull messages from this channel.")


def cmd_remove(args):
    id_or_name = args.channel
    current    = _get_channel_ids()
    client     = _get_client()

    # Try to resolve to ID
    ch_id, ch_name = _resolve_channel(client, id_or_name)
    if not ch_id:
        # Try matching directly
        ch_id = id_or_name if id_or_name in current else None

    if not ch_id or ch_id not in current:
        print(f"'{id_or_name}' is not in the monitored channels list.")
        print("Current channels:", ", ".join(current) or "(none)")
        sys.exit(1)

    current.remove(ch_id)
    _set_channel_ids(current)

    label = f"#{ch_name} ({ch_id})" if ch_name and ch_name != ch_id else ch_id
    print(f"Removed: {label}")
    print(f"Now monitoring {len(current)} channel(s).")


def cmd_search(args):
    client = _get_client()

    if not client:
        print("Search requires SLACK_BOT_TOKEN in tools/.env.")
        print("Without it, find channel IDs in Slack:")
        print("  Right-click channel → View channel details → Channel ID at the bottom")
        sys.exit(1)

    query   = args.query
    results = _search_channels(client, query)
    current = _get_channel_ids()

    if not results:
        print(f"No channels found matching '{query}'")
        return

    print(f"\nChannels matching '{query}':\n")
    print(f"{'ID':<14} {'Name':<25} {'Members':>8}  {'Topic'}")
    print("-" * 70)
    for ch in results:
        monitored = " [monitored]" if ch["id"] in current else ""
        print(f"{ch['id']:<14} {ch['name']:<25} {ch['members']:>8}  {ch['topic']}{monitored}")

    print()
    print("To start monitoring: python tools/slack_channels.py add <ID>")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage monitored Slack channels")
    sub    = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="Show monitored channels")

    add_p = sub.add_parser("add", help="Add a channel to monitor")
    add_p.add_argument("channel", help="Channel ID (C...) or name")

    rm_p = sub.add_parser("remove", help="Remove a channel")
    rm_p.add_argument("channel", help="Channel ID or name")

    search_p = sub.add_parser("search", help="Search workspace channels (requires bot token)")
    search_p.add_argument("query", help="Search query")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "list":   cmd_list,
        "add":    cmd_add,
        "remove": cmd_remove,
        "search": cmd_search,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
