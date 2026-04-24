#!/usr/bin/env python3
"""
eod.py — Headless end-of-day capture for LLM Wiki Vault.
Usage: python .tools/eod.py --vault PATH [--date YYYY-MM-DD] [--dry-run]
"""
import argparse
import re
from datetime import date, datetime
from pathlib import Path


def count_unprocessed(directory: Path) -> int:
    if not directory.exists():
        return 0
    count = 0
    for md in directory.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
            if "processed:" not in text[:300]:
                count += 1
        except Exception:
            pass
    return count


def parse_daily_report(report_path: Path) -> dict:
    if not report_path.exists():
        return {"completed": [], "pending": [], "carry_forward": []}
    text = report_path.read_text(encoding="utf-8")
    completed = []
    pending = []
    carry_forward = []
    in_carry = False
    for line in text.splitlines():
        if re.match(r"^### Carry.forward", line, re.IGNORECASE):
            in_carry = True
            continue
        if re.match(r"^###", line) and in_carry:
            in_carry = False
        m_done = re.match(r"^- \[x\] (.+)", line, re.IGNORECASE)
        if m_done:
            completed.append(m_done.group(1).strip())
            continue
        m_open = re.match(r"^- \[ \] (.+)", line)
        if m_open:
            text_item = m_open.group(1).strip()
            if in_carry:
                carry_forward.append(text_item)
            else:
                pending.append(text_item)
    return {"completed": completed, "pending": pending, "carry_forward": carry_forward}


def write_eod(vault: Path, today_str: str, dry_run: bool = False) -> Path | None:
    today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
    weekday = today_dt.strftime("%A")
    month_day = today_dt.strftime("%B %-d")
    month_bucket = today_dt.strftime("%Y-%m")
    report_path = vault / "reports" / "daily" / f"{today_str}.md"
    parsed = parse_daily_report(report_path)
    completed = parsed["completed"]
    pending = parsed["pending"]
    carry_forward = parsed["carry_forward"]
    notes_count = count_unprocessed(vault / "raw" / "notes")
    notes_state = f"{notes_count} unprocessed" if notes_count > 0 else "clear"
    total_items = len(completed) + len(pending)
    pct = round(100 * len(completed) / total_items) if total_items > 0 else 0
    print(f"[eod] Completed: {len(completed)} / {total_items} ({pct}%)")
    if dry_run:
        print(f"[eod] DRY RUN — would save to raw/notes/{month_bucket}/{today_str}-eod.md")
        return None
    lines = ["---", f'title: "EOD Note — {today_str}"', f"date: {today_str}", "type: eod",
             "source: auto", "processed: false", "---", "", f"# EOD — {weekday} {month_day}", "",
             f"> {len(completed)}/{total_items} items completed ({pct}%)", "", "## Completed today", ""]
    if completed:
        for item in completed:
            lines.append(f"- [x] {item}")
    else:
        lines.append("- *(nothing checked off today)*")
    lines += ["", "## Carry forward", ""]
    all_pending = pending + carry_forward
    if all_pending:
        for item in all_pending:
            lines.append(f"- [ ] {item}")
    else:
        lines.append("- *(all clear — nothing pending)*")
    lines += ["", "## Notes state", "", f"- raw/notes/: {notes_state}", ""]
    content = "\n".join(lines)
    out_dir = vault / "raw" / "notes" / month_bucket
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today_str}-eod.md"
    if out_path.exists():
        print(f"[eod] EOD already exists — skipping")
        return out_path
    out_path.write_text(content, encoding="utf-8")
    print(f"[eod] Saved → {out_path.relative_to(vault)}")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", metavar="PATH", required=True)
    parser.add_argument("--date", metavar="YYYY-MM-DD", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    vault = Path(args.vault).resolve()
    out = write_eod(vault, args.date, dry_run=args.dry_run)
    if out and not args.dry_run:
        print(f"\n✅ EOD saved → {out.relative_to(vault)}")


if __name__ == "__main__":
    main()
