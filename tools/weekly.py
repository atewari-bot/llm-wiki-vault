#!/usr/bin/env python3
"""
weekly.py — Generate weekly review including Slack activity stats.

Usage:
  python tools/weekly.py --vault ~/llm-wiki-vault
  python tools/weekly.py --vault ~/llm-wiki-vault --week 2026-W16
  python tools/weekly.py --vault ~/llm-wiki-vault --no-slack
"""

import argparse
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


def main():
    parser = argparse.ArgumentParser(description="Generate weekly review")
    parser.add_argument("--vault",    required=True)
    parser.add_argument("--week",     default=None, help="YYYY-WNN")
    parser.add_argument("--no-slack", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    today = date.today()

    if args.week:
        year, wn  = args.week.split("-W")
        week_start = date.fromisocalendar(int(year), int(wn), 1)
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end  = week_start + timedelta(days=6)
    week_num  = week_start.isocalendar()[1]
    year      = week_start.year
    week_id   = f"{year}-W{week_num:02d}"

    print(f"\nGenerating weekly review for {week_id} ({week_start} to {week_end})...")

    # Daily reports
    daily_dir     = vault / "reports" / "daily"
    daily_reports = []
    for d in range(7):
        day  = week_start + timedelta(days=d)
        path = daily_dir / f"{day.isoformat()}.md"
        if path.exists():
            daily_reports.append((day, path))
    print(f"   Daily reports: {len(daily_reports)}")

    # Todo completion
    total, completed, incomplete = 0, 0, []
    for day, path in daily_reports:
        for line in path.read_text(errors="ignore").splitlines():
            if re.match(r"^-\s\[x\]", line):
                total += 1; completed += 1
            elif re.match(r"^-\s\[\s\]", line):
                total += 1
                task = re.sub(r"^-\s\[\s\]\s+", "", line).strip()
                if task and "carry-forward" not in task.lower():
                    incomplete.append({"text": task, "date": day.isoformat()})

    seen, dedup = set(), []
    for item in incomplete:
        if item["text"] not in seen:
            seen.add(item["text"])
            dedup.append(item)

    task_counts = Counter(i["text"] for i in incomplete)
    blockers    = [t for t, c in task_counts.items() if c >= 2]
    pct         = round((completed / total * 100) if total > 0 else 0)

    # Wiki activity
    wiki_new, wiki_updated = [], []
    for sub in ["concepts", "people", "tools"]:
        d = vault / "wiki" / sub
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            text    = f.read_text(errors="ignore")
            created = re.search(r"created:\s*(\d{4}-\d{2}-\d{2})", text)
            updated = re.search(r"updated:\s*(\d{4}-\d{2}-\d{2})", text)
            try:
                if created and week_start <= date.fromisoformat(created.group(1)) <= week_end:
                    wiki_new.append(f.stem)
                elif updated and week_start <= date.fromisoformat(updated.group(1)) <= week_end:
                    wiki_updated.append(f.stem)
            except ValueError:
                pass

    art_count   = _count_new_files(vault / "raw" / "articles", week_start, week_end)
    notes_count = _count_new_files(vault / "raw" / "notes",    week_start, week_end)

    # Gaps
    open_gaps = _read_gaps(vault / "wiki" / "meta" / "graph-report.md")
    filled    = [g for g in open_gaps if any(g.lower() in p.lower() for p in wiki_new)]
    still_open = [g for g in open_gaps if g not in filled]

    # Slack stats
    slack_stats = None
    if not args.no_slack:
        try:
            sys.path.insert(0, str(vault / "tools"))
            from slack_ingest import fetch_slack_weekly_stats
            slack_stats = fetch_slack_weekly_stats(
                vault, week_start.isoformat(), min(today, week_end).isoformat()
            )
            print(f"   Slack: {slack_stats['messages']} messages, "
                  f"{slack_stats['action_items']} action items")
        except Exception as e:
            print(f"   Slack stats unavailable: {e}")

    # Render
    bar_fill  = round(pct / 10)
    bar       = "■" * bar_fill + "░" * (10 - bar_fill)
    month_rng = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}"

    lines = [
        "---",
        f'title: "Weekly Review — {week_id}"',
        f"week: {week_id}",
        f"date_range: {month_rng}",
        "type: weekly-review",
        "---",
        "",
        f"# Week {week_num} — {month_rng}",
        "",
        "## Todo summary",
        "",
        f"- Completed: {completed} / {total} total",
        f"- Completion rate: {bar} {pct}%",
    ]
    if blockers:
        lines += ["- Persistent blockers (2+ days):"]
        for b in blockers[:3]:
            lines.append(f"  - {b[:80]}")
    lines.append("")

    lines += ["## Knowledge activity", ""]
    lines += [
        f"- Articles ingested: {art_count}",
        f"- Notes captured: {notes_count}",
        f"- Wiki pages created: {len(wiki_new)}",
        f"- Wiki pages updated: {len(wiki_updated)}",
    ]
    if wiki_new:
        lines.append(f"- New: {', '.join(f'[[{p}]]' for p in wiki_new[:5])}")
    lines.append("")

    if slack_stats:
        lines += ["## Slack activity", ""]
        lines += [
            f"- Channels monitored: {len(slack_stats['channels'])} "
            f"({', '.join(f'#{c}' for c in slack_stats['channels'][:5])})",
            f"- Messages scanned: {slack_stats['messages']}",
            f"- Action items surfaced: {slack_stats['action_items']}",
        ]
        lines.append("")

    if open_gaps:
        lines += ["## Gaps", ""]
        if filled:
            lines.append(f"- Filled: {', '.join(f'[[{g}]]' for g in filled)}")
        if still_open:
            lines.append(f"- Still open: {', '.join(still_open[:3])}")
        lines.append("")

    lines += ["## Next week focus", ""]
    suggestions = []
    if still_open:   suggestions.append(f"Research: {still_open[0]}")
    if blockers:     suggestions.append(f"Resolve: {blockers[0][:60]}")
    suggestions.append("Run `discover` to surface new connections")
    for s in suggestions[:3]:
        lines.append(f"- [ ] {s}")
    lines.append("")

    if dedup:
        lines += ["## Carrying into next week", ""]
        for item in dedup[:10]:
            lines.append(f"- [ ] {item['text']}")
        lines.append("")

    out_path = vault / "reports" / "weekly" / f"{week_id}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWeekly review -> reports/weekly/{week_id}.md")
    print(f"   Completion: {pct}%  Wiki: +{len(wiki_new)} pages")


def _count_new_files(folder: Path, start: date, end: date) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*.md")
               if not f.name.startswith(".")
               and start <= date.fromtimestamp(f.stat().st_mtime) <= end)


def _read_gaps(path: Path) -> list:
    if not path.exists():
        return []
    gaps, in_gaps = [], False
    for line in path.read_text(errors="ignore").splitlines():
        if "## Gaps" in line:
            in_gaps = True
            continue
        if in_gaps and line.startswith("##"):
            break
        if in_gaps and line.startswith("### "):
            gaps.append(line.lstrip("# ").strip())
    return gaps[:5]


if __name__ == "__main__":
    main()
