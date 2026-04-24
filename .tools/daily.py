#!/usr/bin/env python3
"""
daily.py — Daily briefing generator for LLM Wiki Vault.
Usage: python .tools/daily.py --vault PATH [--date YYYY-MM-DD] [--no-calendar]
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))


def fetch_calendar(date_str: str) -> list:
    try:
        tools_dir = Path(__file__).parent
        sys.path.insert(0, str(tools_dir))
        from gcal import fetch_events, is_configured
        if is_configured():
            events = fetch_events(date_str)
            print(f"[daily] Calendar: {len(events)} event(s) via OAuth token")
            return events
        else:
            print("[daily] Calendar: no token.json — run 'python .tools/gcal_auth.py' to enable headless access")
    except Exception as e:
        print(f"[daily] Calendar: OAuth attempt failed ({e})")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        mcp_servers = [{"type": "url", "url": "https://calendarmcp.googleapis.com/mcp/v1", "name": "google-calendar"}]
        prompt = (
            f"Fetch all calendar events for {date_str}. "
            "Return a JSON array only, no explanation, no markdown fences. "
            'Format: [{"time": "09:00", "end": "09:45", "title": "...", "description": "..."}]'
        )
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1000,
            mcp_servers=mcp_servers,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        events = json.loads(raw.strip())
        print(f"[daily] Calendar: {len(events)} event(s) via Cowork MCP")
        return events if isinstance(events, list) else []
    except Exception as e:
        print(f"[daily] Warning: all calendar methods failed — {e}")
        return []


def read_manual_todos(vault: Path, date_str: str) -> list:
    todo_file = vault / "raw" / "todos" / f"{date_str}.md"
    if not todo_file.exists():
        return []
    try:
        text = todo_file.read_text(encoding="utf-8")
    except Exception:
        return []
    items = re.findall(r"^- \[ \] (.+)$", text, re.MULTILINE)
    return [item.strip() for item in items if item.strip()]


def count_unprocessed(folder: Path) -> int:
    if not folder.exists():
        return 0
    count = 0
    for md in folder.rglob("*.md"):
        if md.name.startswith("."):
            continue
        try:
            text = md.read_text(encoding="utf-8")
            if "processed:" not in text:
                count += 1
        except Exception:
            pass
    return count


def read_gaps(report_path: Path) -> list:
    if not report_path.exists():
        return []
    text = report_path.read_text(encoding="utf-8")
    m = re.search(r"## Gaps.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not m:
        return []
    section = m.group(1)
    gaps = re.findall(r"###\s+\d+\.\s+(.+)", section)
    return gaps[:5]


def read_carry_forward(reports_dir: Path, today_str: str) -> list:
    today = datetime.strptime(today_str, "%Y-%m-%d").date()
    seen: dict = {}
    for days_ago in range(1, 8):
        check_date = today - timedelta(days=days_ago)
        report_file = reports_dir / "daily" / f"{check_date.isoformat()}.md"
        if not report_file.exists():
            continue
        try:
            text = report_file.read_text(encoding="utf-8")
        except Exception:
            continue
        unchecked = re.findall(r"^- \[ \] (.+)$", text, re.MULTILINE)
        for item_text in unchecked:
            item_text = item_text.strip()
            clean = re.sub(r"\s*\(carried \d+ days.*?\)", "", item_text).strip()
            if clean not in seen:
                seen[clean] = {"text": clean, "days_ago": days_ago, "from_date": check_date.isoformat()}
    return list(seen.values())


def enrich_events(events: list, wiki_dir: Path) -> list:
    wiki_pages = []
    for md in wiki_dir.rglob("*.md"):
        if md.name.startswith(".") or "(MOC)" in md.name:
            continue
        wiki_pages.append(md.stem.replace("-", " ").replace("_", " ").lower())
    enriched = []
    for event in events:
        title_words = set(re.findall(r"\b\w{4,}\b", event.get("title", "").lower()))
        matches = []
        for page_name in wiki_pages:
            page_words = set(re.findall(r"\b\w{4,}\b", page_name))
            if title_words & page_words:
                matches.append(page_name.title())
            if len(matches) >= 3:
                break
        event["wiki_pages"] = matches
        enriched.append(event)
    return enriched


def wiki_pulse(wiki_dir: Path, today: str) -> list:
    today_dt = datetime.strptime(today, "%Y-%m-%d").date()
    week_start = today_dt - timedelta(days=today_dt.weekday())
    results = []
    for md in wiki_dir.rglob("*.md"):
        if md.name.startswith("."):
            continue
        try:
            text = md.read_text(encoding="utf-8")
            m = re.search(r"^updated:\s*(.+)$", text, re.MULTILINE)
            if m:
                updated_str = m.group(1).strip()
                try:
                    updated_dt = datetime.strptime(updated_str, "%Y-%m-%d").date()
                    if updated_dt >= week_start:
                        page_name = md.stem.replace("-", " ").replace("_", " ").title()
                        results.append(f"[[{page_name}]] — updated {updated_str}")
                except ValueError:
                    pass
        except Exception:
            pass
    return results


def build_todos(events: list, notes_count: int, gaps: list, carried: list,
                manual_todos: list | None = None) -> list:
    todos = []
    for text in (manual_todos or []):
        todos.append({"text": text, "rationale": "manually planned", "score": 3, "tier": "must",
                      "carried": False, "days": 0, "source": "manual"})
    for event in events:
        pages = event.get("wiki_pages", [])
        if pages:
            todos.append({"text": f"Prepare for: {event.get('title', 'Meeting')} ({event.get('time', '')})",
                          "rationale": f"Meeting today — relevant wiki: {', '.join(pages[:2])}",
                          "score": 3, "tier": "must", "carried": False, "days": 0})
    if notes_count > 5:
        todos.append({"text": f"Process notes ({notes_count} unprocessed files)",
                      "rationale": "Notes backlog > 5 files", "score": 1 + (1 if notes_count > 10 else 0),
                      "tier": "should", "carried": False, "days": 0})
    for gap in gaps[:3]:
        todos.append({"text": f"Research: {gap}", "rationale": "Fills knowledge gap in graph",
                      "score": 1, "tier": "if-time", "carried": False, "days": 0})
    gap_names = [g.lower() for g in gaps]
    for item in carried:
        text = item["text"]
        days = item["days_ago"]
        score = 2 if days >= 3 else 0
        if any(g in text.lower() for g in gap_names):
            score += 1
        tier = "must" if score >= 3 else ("should" if score >= 2 else "if-time")
        todos.append({"text": text, "rationale": f"Carried {days} day(s)", "score": score,
                      "tier": tier, "carried": True, "days": days})
    todos.sort(key=lambda t: t["score"], reverse=True)
    for todo in todos:
        if todo["score"] >= 3:
            todo["tier"] = "must"
        elif todo["score"] >= 1:
            todo["tier"] = "should"
        else:
            todo["tier"] = "if-time"
    return todos


def render_briefing(today_str: str, events: list, todos: list, pulse: list, gaps: list,
                    notes_count: int, manual_todos: list | None = None) -> str:
    today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
    weekday = today_dt.strftime("%A")
    month_day = today_dt.strftime("%B %-d")
    title = f"Daily Briefing — {weekday} {month_day}"
    manual_count = len(manual_todos) if manual_todos else 0
    if manual_count > 0:
        focus = f"{manual_count} planned task{'s' if manual_count != 1 else ''} for today."
    elif notes_count > 0:
        focus = f"{notes_count} unprocessed notes await — prioritise knowledge capture today."
    elif events:
        focus = f"{len(events)} meeting(s) scheduled — review prep materials below."
    else:
        focus = "Clear day — good time for deep work and wiki enrichment."
    lines = ["---", f'title: "{title}"', f"date: {today_str}", "type: daily-briefing", "---", "",
             f"# {title}", "", f"> {focus}", "", "## Calendar", ""]
    if events:
        for event in events:
            time = event.get("time", "??:??")
            end = event.get("end", "")
            title_ev = event.get("title", "Untitled")
            duration = f"{time}–{end}" if end else time
            pages = event.get("wiki_pages", [])
            wiki_str = ", ".join(f"[[{p}]]" for p in pages) if pages else "—"
            lines.append(f"- {duration} — {title_ev} → Wiki: {wiki_str} → Prep: review linked pages")
    else:
        lines.append("- *(No calendar events found)*")
    lines += ["", "## Todo", ""]
    manual = [t for t in todos if t.get("source") == "manual"]
    must = [t for t in todos if t["tier"] == "must" and not t["carried"] and t.get("source") != "manual"]
    should = [t for t in todos if t["tier"] == "should" and not t["carried"] and t.get("source") != "manual"]
    if_time = [t for t in todos if t["tier"] == "if-time" and not t["carried"] and t.get("source") != "manual"]
    carry = [t for t in todos if t["carried"]]

    def render_todo_list(items, header):
        out = [f"### {header}", ""]
        if not items:
            out.append("*(none)*")
        for item in items:
            days = item.get("days", 0)
            text = item["text"]
            rationale = item.get("rationale", "")
            if item.get("carried") and days:
                flag = " — *consider dropping*" if days >= 5 else ""
                out.append(f"- [ ] {text} *(carried {days} day{'s' if days != 1 else ''}){flag}*")
            elif item.get("source") == "manual":
                out.append(f"- [ ] {text}")
            else:
                out.append(f"- [ ] {text} — *{rationale}*")
        out.append("")
        return out

    if manual:
        lines += render_todo_list(manual, "Planned")
    lines += render_todo_list(must, "Must do")
    lines += render_todo_list(should, "Should do")
    lines += render_todo_list(if_time, "If time")
    if carry:
        lines += render_todo_list(carry, "Carry-forward")
    lines += ["## Knowledge pulse", ""]
    if pulse:
        for p in pulse[:7]:
            lines.append(f"- {p}")
    else:
        lines.append("- *(No wiki pages updated this week yet)*")
    lines += ["", "## Open knowledge gaps", ""]
    if gaps:
        for gap in gaps[:3]:
            lines.append(f"- {gap} → ingest <url> to fill")
    else:
        lines.append("- *(No gaps detected — run `build graph` to analyse)*")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="LLM Wiki Vault — Daily Briefing Generator")
    parser.add_argument("--vault", metavar="PATH", required=True)
    parser.add_argument("--date", metavar="YYYY-MM-DD", default=date.today().isoformat())
    parser.add_argument("--no-calendar", action="store_true")
    args = parser.parse_args()
    vault = Path(args.vault).resolve()
    today_str = args.date
    print(f"[daily] Generating briefing for {today_str}...")
    events = [] if args.no_calendar else fetch_calendar(today_str)
    wiki_dir = vault / "wiki"
    events = enrich_events(events, wiki_dir)
    notes_count = count_unprocessed(vault / "raw" / "notes")
    gaps = read_gaps(vault / "wiki" / "meta" / "graph-report.md")
    manual_todos = read_manual_todos(vault, today_str)
    carried = read_carry_forward(vault / "reports", today_str)
    todos = build_todos(events, notes_count, gaps, carried, manual_todos)
    pulse = wiki_pulse(wiki_dir, today_str)
    briefing = render_briefing(today_str, events, todos, pulse, gaps, notes_count, manual_todos)
    out_path = vault / "reports" / "daily" / f"{today_str}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(briefing, encoding="utf-8")
    print(f"[daily] Saved → {out_path}")


if __name__ == "__main__":
    main()
