#!/usr/bin/env python3
"""
daily.py — Generate daily briefing from Calendar + Slack + vault state.

Usage:
  python tools/daily.py --vault ~/llm-wiki-vault
  python tools/daily.py --vault ~/llm-wiki-vault --no-calendar
  python tools/daily.py --vault ~/llm-wiki-vault --no-slack
  python tools/daily.py --vault ~/llm-wiki-vault --date 2026-04-21
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


def main():
    parser = argparse.ArgumentParser(description="Generate daily briefing")
    parser.add_argument("--vault",       required=True)
    parser.add_argument("--date",        default=None)
    parser.add_argument("--no-calendar", action="store_true")
    parser.add_argument("--no-slack",    action="store_true")
    args = parser.parse_args()

    vault     = Path(args.vault).expanduser().resolve()
    today_str = args.date or date.today().isoformat()
    today     = date.fromisoformat(today_str)
    weekday   = today.strftime("%A")

    print(f"\nGenerating daily briefing for {weekday} {today_str}...")

    # 1. Refresh Slack (if bot token available and not skipped)
    slack_todos = []
    if not args.no_slack:
        slack_todos = _maybe_refresh_slack(vault, today_str)

    # 2. Calendar
    events = []
    if not args.no_calendar:
        events = fetch_calendar(today_str)
        print(f"   Calendar: {len(events)} events")

    # 3. Inbox state
    inbox_count = count_unprocessed(vault / "raw" / "inbox")
    notes_count = count_unprocessed(vault / "raw" / "notes")

    # 4. Gaps
    gaps = read_gaps(vault / "wiki" / "meta" / "graph-report.md")

    # 5. Carry-forward
    carried = read_carry_forward(vault / "reports" / "daily", today_str)

    # 6. Manual todos
    manual_todos = read_manual_todos(vault, today_str)
    if manual_todos:
        print(f"   Manual todos: {len(manual_todos)} planned tasks")

    # 7. Wiki pulse
    pulse = wiki_pulse(vault / "wiki", today)

    # 8. Enrich events
    enriched_events = enrich_events(events, vault / "wiki")

    # 9. Build todos
    todos = build_todos(
        events=enriched_events,
        inbox_count=inbox_count,
        notes_count=notes_count,
        gaps=gaps,
        carried=carried,
        slack_todos=slack_todos,
        manual_todos=manual_todos,
    )

    # 10. Write
    briefing = render_briefing(today, weekday, enriched_events, todos, carried,
                               pulse, gaps, slack_todos, manual_todos=manual_todos)

    out_path = vault / "reports" / "daily" / f"{today_str}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(briefing, encoding="utf-8")

    must   = sum(1 for t in todos if t["tier"] == "must" and t.get("source") != "manual")
    should = sum(1 for t in todos if t["tier"] == "should")
    ift    = sum(1 for t in todos if t["tier"] == "if-time")

    print(f"\nDaily briefing -> reports/daily/{today_str}.md")
    print(f"   Meetings: {len(events)}  Slack items: {len(slack_todos)}")
    if manual_todos:
        print(f"   Planned: {len(manual_todos)} manual tasks")
    print(f"   Todos: {must} must  {should} should  {ift} if-time")
    print(f"   Carry-forward: {len(carried)}")


def _maybe_refresh_slack(vault: Path, date_str: str) -> list:
    """Attempt Slack refresh via slack_ingest.py if bot token set, else read sidecars."""
    from slack_ingest import fetch_slack_todos

    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if token:
        print("   Refreshing Slack...")
        try:
            subprocess.run(
                [sys.executable, str(vault / "tools" / "slack_ingest.py"),
                 "--vault", str(vault)],
                check=True, timeout=60
            )
        except Exception as e:
            print(f"   Slack refresh failed: {e} — using cached sidecars")

    todos = fetch_slack_todos(vault, date_str)
    if todos:
        print(f"   Slack: {len(todos)} action items")
    else:
        print("   Slack: no action items (run 'refresh slack' via Cowork if needed)")
    return todos


def fetch_calendar(date_str: str) -> list:
    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            mcp_servers=[{
                "type": "url",
                "url":  "https://calendarmcp.googleapis.com/mcp/v1",
                "name": "google-calendar"
            }],
            messages=[{"role": "user", "content": (
                f"List all events for {date_str} from my Google Calendar. "
                f"Return ONLY a JSON array: "
                f'[{{"time":"09:00","end":"09:45","title":"...","description":""}}]. '
                f"No markdown. Empty array [] if no events."
            )}]
        )
        raw = "".join(b.text for b in response.content if hasattr(b, "text")).strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw) if raw.startswith("[") else []
    except Exception as e:
        print(f"   Calendar unavailable: {e}")
        return []


def count_unprocessed(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(
        1 for f in folder.rglob("*.md")
        if not f.name.startswith(".") and "processed:" not in f.read_text(errors="ignore")
    )


def read_gaps(report_path: Path) -> list:
    if not report_path.exists():
        return []
    gaps, in_gaps = [], False
    for line in report_path.read_text(errors="ignore").splitlines():
        if "## Gaps" in line:
            in_gaps = True
            continue
        if in_gaps and line.startswith("##"):
            break
        if in_gaps and line.startswith("### "):
            gaps.append(line.lstrip("# ").strip())
    return gaps[:5]


def read_carry_forward(daily_dir: Path, today_str: str) -> list:
    today   = date.fromisoformat(today_str)
    carried = []
    for days_ago in range(1, 8):
        path = daily_dir / f"{(today - timedelta(days=days_ago)).isoformat()}.md"
        if not path.exists():
            continue
        for line in path.read_text(errors="ignore").splitlines():
            m = re.match(r"^-\s\[\s\]\s+(.+)$", line)
            if m:
                task = m.group(1).strip()
                if "carry-forward" not in task.lower() and "carried" not in task.lower():
                    carried.append({"text": task, "days_ago": days_ago})
    seen, dedup = set(), []
    for item in carried:
        if item["text"] not in seen:
            seen.add(item["text"])
            dedup.append(item)
    return dedup


def enrich_events(events: list, wiki_dir: Path) -> list:
    all_pages = []
    for sub in ["concepts", "people", "tools"]:
        d = wiki_dir / sub
        if d.exists():
            all_pages.extend(f.stem for f in d.glob("*.md"))
    enriched = []
    for event in events:
        keywords = set(re.sub(r"[^a-zA-Z0-9 ]", "", event.get("title", "")).lower().split())
        relevant = [p for p in all_pages if keywords & set(p.lower().replace("-", " ").split())]
        enriched.append({**event, "wiki_pages": relevant[:3]})
    return enriched


def wiki_pulse(wiki_dir: Path, today: date) -> list:
    week_start = today - timedelta(days=today.weekday())
    recent = []
    for sub in ["concepts", "people", "tools"]:
        d = wiki_dir / sub
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            m = re.search(r"updated:\s*(\d{4}-\d{2}-\d{2})", f.read_text(errors="ignore"))
            if m:
                try:
                    if date.fromisoformat(m.group(1)) >= week_start:
                        recent.append(f"[[{f.stem}]] — updated {m.group(1)}")
                except ValueError:
                    pass
    return recent[:7]


def read_manual_todos(vault: Path, today_str: str) -> list:
    todo_path = vault / "raw" / "todos" / f"{today_str}.md"
    if not todo_path.exists():
        return []
    todos = []
    for line in todo_path.read_text(errors="ignore").splitlines():
        m = re.match(r"^-\s\[\s\]\s+(.+)$", line)
        if m:
            text = re.sub(r"\s*<!--.*?-->", "", m.group(1)).strip()
            if text:
                todos.append({"text": text, "source": "manual"})
    return todos


def build_todos(events, inbox_count, notes_count, gaps, carried, slack_todos=None, manual_todos=None) -> list:
    todos = []

    for item in (manual_todos or []):
        todos.append({"text": item["text"], "rationale": "planned",
                      "score": 3, "tier": "must", "source": "manual"})

    if inbox_count > 0:
        todos.append({"text": f"Process inbox ({inbox_count} unprocessed files)",
                      "rationale": "clear before new content arrives",
                      "score": 3 + (1 if inbox_count > 5 else 0), "tier": "must"})

    if notes_count > 0:
        todos.append({"text": f"Process notes ({notes_count} unprocessed files)",
                      "rationale": "wikify before context is lost",
                      "score": 2, "tier": "should"})

    for event in events:
        if event.get("wiki_pages"):
            pages = ", ".join(f"[[{p}]]" for p in event["wiki_pages"])
            todos.append({"text": f"Prep for {event['title']} — review {pages}",
                          "rationale": f"meeting at {event.get('time','')}",
                          "score": 4, "tier": "must"})

    for item in (slack_todos or []):
        score  = item.get("score", 2)
        boost  = 2 if score >= 3 else 1
        todos.append({"text": f"#{item.get('channel','slack')} — {item['text'][:80]}",
                      "rationale": f"via {item.get('sender','Slack')}",
                      "score": boost, "tier": "should", "source": "slack"})

    for gap in gaps[:2]:
        todos.append({"text": f"Research: {gap}", "rationale": "open knowledge gap",
                      "score": 1, "tier": "if-time"})

    for item in carried:
        days  = item["days_ago"]
        score = 2 + min(days, 3)
        todos.append({"text": item["text"], "rationale": f"carried {days} day{'s' if days>1 else ''}",
                      "score": score, "tier": "should", "carried": True, "days": days})

    todos.sort(key=lambda t: t["score"], reverse=True)
    for i, t in enumerate(todos):
        t["tier"] = "must" if i < 3 else ("should" if i < 6 else "if-time")
    return todos


def render_briefing(today, weekday, events, todos, carried, pulse, gaps, slack_todos=None, manual_todos=None) -> str:
    date_str  = today.isoformat()
    month_day = today.strftime("%B %d")
    manual_t = [t for t in todos if t.get("source") == "manual"]
    must_t   = [t for t in todos if t["tier"] == "must" and t.get("source") != "manual"]
    should_t = [t for t in todos if t["tier"] == "should"]
    ift_t    = [t for t in todos if t["tier"] == "if-time"]

    lines = [
        "---",
        f'title: "Daily Briefing — {weekday} {month_day}"',
        f"date: {date_str}",
        "type: daily-briefing",
        "---",
        "",
        f"# Daily Briefing — {weekday} {month_day}",
        "",
    ]

    parts = []
    if manual_todos:
        n = len(manual_todos)
        parts.append(f"{n} planned task{'s' if n > 1 else ''} for today")
    if events:      parts.append(f"{len(events)} meeting{'s' if len(events)>1 else ''}")
    if slack_todos: parts.append(f"{len(slack_todos)} Slack item{'s' if len(slack_todos)>1 else ''}")
    if must_t:      parts.append(f"{len(must_t)} must-do{'s' if len(must_t)>1 else ''}")
    if carried:     parts.append(f"{len(carried)} carried")
    lines += [f"> {'  ·  '.join(parts) if parts else 'Clear day'}", ""]

    if events:
        lines += ["## Calendar", ""]
        for e in events:
            t = f"**{e.get('time','')}**" if e.get("time") else ""
            lines.append(f"- {t} — {e.get('title','Untitled')}")
            if e.get("wiki_pages"):
                lines.append(f"  → Wiki: {'  ·  '.join(f'[[{p}]]' for p in e['wiki_pages'])}")
            if e.get("description"):
                lines.append(f"  → {e['description'][:120]}")
        lines.append("")

    lines += ["## Todo", ""]
    if manual_t:
        lines += ["### Planned", ""]
        for t in manual_t:
            lines.append(f"- [ ] {t['text']} `Manual`")
        lines.append("")
    if must_t:
        lines += ["### Must do", ""]
        for t in must_t:
            rat = f" — *{t['rationale']}*" if t.get("rationale") else ""
            lines.append(f"- [ ] {t['text']}{rat}")
        lines.append("")
    if should_t:
        lines += ["### Should do", ""]
        for t in should_t:
            rat = f" — *{t['rationale']}*" if t.get("rationale") else ""
            lines.append(f"- [ ] {t['text']}{rat}")
        lines.append("")
    if ift_t:
        lines += ["### If time", ""]
        for t in ift_t:
            lines.append(f"- [ ] {t['text']}")
        lines.append("")

    old_carried = [t for t in todos if t.get("carried") and t.get("days", 0) >= 3]
    if old_carried:
        lines += ["### Carry-forward", ""]
        for t in old_carried:
            flag = " — consider dropping" if t["days"] >= 5 else ""
            lines.append(f"- [ ] {t['text']} *(carried {t['days']} days{flag})*")
        lines.append("")

    if slack_todos:
        lines += ["## From Slack", ""]
        for item in slack_todos[:10]:
            lines.append(f"- [ ] #{item.get('channel','slack')} — {item['text'][:100]} "
                         f"*(via {item.get('sender','Unknown')})*")
        lines.append("")

    if pulse:
        lines += ["## Knowledge pulse", ""]
        for p in pulse[:5]:
            lines.append(f"- {p}")
        lines.append("")

    if gaps:
        lines += ["## Open knowledge gaps", ""]
        for g in gaps[:3]:
            lines.append(f"- {g} → `ingest <url>` to fill")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
