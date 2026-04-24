from pathlib import Path as _Path
from dotenv import load_dotenv as _lde
_lde(_Path(__file__).parent / ".env")

#!/usr/bin/env python3
"""
review.py — Confidence decay scanner. Find stale wiki pages and downgrade them.

Usage:
  python .tools/review.py --vault ~/llm-wiki-vault
  python .tools/review.py --vault ~/llm-wiki-vault --dry-run
  python .tools/review.py --vault ~/llm-wiki-vault --auto   # downgrade without prompting
"""

import argparse
import re
from datetime import date, timedelta
from pathlib import Path


# Decay thresholds (days)
HIGH_TO_MEDIUM_DAYS  = 90
MEDIUM_STALE_DAYS    = 180
STUB_ABANDONED_DAYS  = 30
STUB_WORD_THRESHOLD  = 150


def main():
    parser = argparse.ArgumentParser(description="Wiki confidence decay review")
    parser.add_argument("--vault",    required=True)
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--auto",     action="store_true",
                        help="Auto-downgrade without interactive prompts")
    args = parser.parse_args()

    vault     = Path(args.vault).expanduser().resolve()
    today     = date.today()
    today_str = today.isoformat()

    print(f"\n🔍 Scanning wiki confidence levels...")

    # ── Load pages ────────────────────────────────────────────
    pages = load_all_pages(vault / "wiki")
    print(f"   Loaded {len(pages)} wiki pages")

    # ── Categorise ────────────────────────────────────────────
    downgrades = []   # high → medium
    stale      = []   # medium, very old
    stubs      = []   # low, abandoned

    for page in pages:
        confidence = page["confidence"]
        updated    = page["updated"]
        created    = page["created"]
        word_count = page["word_count"]

        if updated:
            days_since_update = (today - updated).days
        else:
            days_since_update = (today - created).days if created else 999

        if confidence == "high" and days_since_update >= HIGH_TO_MEDIUM_DAYS:
            downgrades.append({**page, "days": days_since_update})

        elif confidence == "medium" and days_since_update >= MEDIUM_STALE_DAYS:
            stale.append({**page, "days": days_since_update})

        elif confidence == "low":
            days_since_create = (today - created).days if created else 999
            if days_since_create >= STUB_ABANDONED_DAYS or word_count < STUB_WORD_THRESHOLD:
                stubs.append({**page, "days": days_since_create})

    downgrades.sort(key=lambda x: x["days"], reverse=True)
    stale.sort(key=lambda x: x["days"], reverse=True)
    stubs.sort(key=lambda x: x["days"], reverse=True)

    print(f"\n📋 Review queue:")
    print(f"   🔴 Downgrade (high→medium, {HIGH_TO_MEDIUM_DAYS}+ days): {len(downgrades)}")
    print(f"   🟡 Stale (medium, {MEDIUM_STALE_DAYS}+ days): {len(stale)}")
    print(f"   ⚪ Abandoned stubs: {len(stubs)}")

    if args.dry_run:
        print("\n[DRY RUN — no files written]\n")
        _print_queue(downgrades, stale, stubs)
        return

    # ── Apply downgrades ──────────────────────────────────────
    downgraded_count = 0
    if downgrades:
        print(f"\n🔴 Auto-downgrading {len(downgrades)} high→medium pages...")
        for page in downgrades:
            _downgrade_page(page, today_str)
            downgraded_count += 1
            print(f"   ↓ [[{page['id']}]] ({page['days']} days old)")

    # ── Interactive stale + stub review ──────────────────────
    deferred, resolved = [], []

    all_review = stale + stubs
    if all_review and not args.auto:
        print(f"\n🟡 Review queue ({len(all_review)} pages):")
        for page in all_review:
            label = "stale" if page in stale else "stub"
            print(f"\n  [{label}] [[{page['id']}]] — {page['days']} days old, "
                  f"{page['word_count']} words, confidence: {page['confidence']}")
            print(f"  Options: (k)eep  (d)elete  (s)kip/defer")
            try:
                choice = input("  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "s"

            if choice == "d":
                Path(page["path"]).unlink(missing_ok=True)
                resolved.append(page["id"] + " (deleted)")
                print(f"  ✓ Deleted")
            elif choice == "k":
                _extend_staleness(page, today_str)
                resolved.append(page["id"] + " (kept, window extended)")
                print(f"  ✓ Staleness window extended 90 days")
            else:
                deferred.append(page)
                print(f"  → Deferred")

    elif args.auto:
        # In auto mode just report, don't delete
        deferred = all_review

    # ── Write review report ───────────────────────────────────
    report = render_review(
        today_str, len(pages),
        downgrades, stale, stubs,
        downgraded_count, resolved, deferred
    )
    out_path = vault / "reports" / f"{today_str}-review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    # ── Update conflicts.md with note ────────────────────────
    _update_conflicts_placeholder(vault)

    print(f"\n🔍 Review complete → reports/{today_str}-review.md")
    print(f"   Downgraded: {downgraded_count}  Resolved: {len(resolved)}  Deferred: {len(deferred)}")


# ─────────────────────────────────────────────────────────────
# Page loader
# ─────────────────────────────────────────────────────────────

def load_all_pages(wiki_dir: Path) -> list[dict]:
    pages = []
    for sub in ["concepts", "tools"]:
        d = wiki_dir / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            if f.name.startswith(".") or f.stem == ".gitkeep":
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            fm   = _parse_frontmatter(text)
            body = _strip_frontmatter(text)

            confidence = fm.get("confidence", "medium").strip()
            word_count = len(body.split())

            updated_str = fm.get("updated", "").strip()
            created_str = fm.get("created", "").strip()

            try:
                updated = date.fromisoformat(updated_str) if updated_str else None
            except ValueError:
                updated = None
            try:
                created = date.fromisoformat(created_str) if created_str else None
            except ValueError:
                created = None

            pages.append({
                "id":         f.stem,
                "path":       str(f),
                "subfolder":  sub,
                "confidence": confidence,
                "updated":    updated,
                "created":    created,
                "word_count": word_count,
                "text":       text,
                "fm":         fm,
            })
    return pages


def _parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL).strip()


# ─────────────────────────────────────────────────────────────
# Page modifiers
# ─────────────────────────────────────────────────────────────

def _downgrade_page(page: dict, today_str: str):
    text = page["text"]

    # Update confidence in frontmatter
    text = re.sub(
        r"(confidence:\s*)high",
        r"\1medium",
        text
    )
    # Update updated date
    text = re.sub(
        r"(updated:\s*)[\d-]+",
        f"\\g<1>{today_str}",
        text
    )

    # Add warning note if not already present
    warning = (
        f"\n> [!warning] Confidence downgraded\n"
        f"> Marked high-confidence but not updated in {page['days']} days. "
        f"Re-verify claims before relying on this page. "
        f"Last reviewed: {today_str}\n"
    )
    if "[!warning] Confidence downgraded" not in text:
        # Add before ## See Also or at end
        if "## See Also" in text:
            text = text.replace("## See Also", warning + "\n## See Also")
        else:
            text = text.rstrip() + "\n" + warning

    Path(page["path"]).write_text(text, encoding="utf-8")


def _extend_staleness(page: dict, today_str: str):
    """Update the updated date so the page gets another window."""
    text = re.sub(
        r"(updated:\s*)[\d-]+",
        f"\\g<1>{today_str}",
        page["text"]
    )
    Path(page["path"]).write_text(text, encoding="utf-8")


def _update_conflicts_placeholder(vault: Path):
    """Ensure wiki/meta/conflicts.md exists."""
    conflicts_path = vault / "wiki" / "meta" / "conflicts.md"
    if not conflicts_path.exists():
        conflicts_path.write_text(
            "---\ntitle: \"Conflict Tracker\"\ntags: [meta, conflicts]\n"
            f"updated: {date.today().isoformat()}\n---\n\n"
            "# Conflict Tracker\n\nRun `conflicts` to scan for contradictions.\n\n"
            "## Active conflicts\n\n*None yet.*\n\n## Resolved conflicts\n\n*None yet.*\n",
            encoding="utf-8"
        )


# ─────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────

def _print_queue(downgrades, stale, stubs):
    if downgrades:
        print("\n🔴 Downgrade (high→medium):")
        for p in downgrades:
            print(f"  [[{p['id']}]] — {p['days']} days since update")
    if stale:
        print("\n🟡 Stale (medium):")
        for p in stale:
            print(f"  [[{p['id']}]] — {p['days']} days, {p['word_count']} words")
    if stubs:
        print("\n⚪ Abandoned stubs:")
        for p in stubs:
            print(f"  [[{p['id']}]] — {p['days']} days old, {p['word_count']} words")


def render_review(today_str, total, downgrades, stale, stubs,
                  downgraded_count, resolved, deferred) -> str:
    month_day = date.fromisoformat(today_str).strftime("%B %d")
    lines = [
        "---",
        f'title: "Wiki Review — {today_str}"',
        f"date: {today_str}",
        "type: confidence-review",
        f"pages_scanned: {total}",
        "---",
        "",
        f"# Wiki Review — {month_day}",
        "",
        "## Summary",
        "",
        f"- Pages scanned: {total}",
        f"- Downgraded (high→medium): {downgraded_count}",
        f"- Stale flagged: {len(stale)}",
        f"- Abandoned stubs: {len(stubs)}",
        f"- Resolved this session: {len(resolved)}",
        f"- Deferred: {len(deferred)}",
        "",
    ]

    if downgrades:
        lines += ["## Downgraded pages", ""]
        for p in downgrades:
            lines.append(f"- [[{p['id']}]] — was high, now medium ({p['days']} days old)")
        lines.append("")

    if resolved:
        lines += ["## Resolved this session", ""]
        for r in resolved:
            lines.append(f"- {r}")
        lines.append("")

    if deferred:
        lines += ["## Still needs attention", ""]
        for p in deferred:
            label = "stale" if p["confidence"] == "medium" else "stub"
            lines.append(
                f"- [[{p['id']}]] ({label}, {p['days']} days, "
                f"{p['word_count']} words)"
            )
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
