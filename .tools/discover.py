from pathlib import Path as _Path
from dotenv import load_dotenv as _lde
_lde(_Path(__file__).parent / ".env")

#!/usr/bin/env python3
"""
discover.py — Serendipity engine. Find non-obvious connections across the wiki.

Usage:
  python .tools/discover.py --vault ~/llm-wiki-vault
  python .tools/discover.py --vault ~/llm-wiki-vault --dry-run
"""

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "scripts"))


def main():
    parser = argparse.ArgumentParser(description="Find non-obvious wiki connections")
    parser.add_argument("--vault",    required=True)
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--max-bridges", type=int, default=3)
    args = parser.parse_args()

    vault     = Path(args.vault).expanduser().resolve()
    today_str = date.today().isoformat()

    print(f"\n🔍 Scanning wiki for hidden connections...")

    # ── Load all wiki pages ───────────────────────────────────
    pages = load_wiki_pages(vault / "wiki")
    print(f"   Loaded {len(pages)} wiki pages")

    if len(pages) < 3:
        print("   ⚠️  Need at least 3 wiki pages to find connections. Ingest more content first.")
        return

    # ── Find connections ──────────────────────────────────────
    bridges   = find_bridge_connections(pages, max_results=args.max_bridges)
    sequences = find_implicit_sequences(pages, max_results=2)
    anomaly   = find_anomaly(pages)

    print(f"   Bridges: {len(bridges)}  Sequences: {len(sequences)}")

    if args.dry_run:
        print("\n[DRY RUN — no files written]\n")
        print("Bridge connections:")
        for b in bridges:
            print(f"  {b['page_a']} ↔ {b['page_b']}: {b['reason']}")
        return

    # ── Write report ──────────────────────────────────────────
    report = render_discoveries(today_str, pages, bridges, sequences, anomaly)
    out_path = vault / "reports" / f"{today_str}-discoveries.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    print(f"\n🔍 Discoveries → reports/{today_str}-discoveries.md")
    print(f"   Bridges: {len(bridges)}  Sequences: {len(sequences)}")


# ─────────────────────────────────────────────────────────────
# Wiki loader
# ─────────────────────────────────────────────────────────────

def load_wiki_pages(wiki_dir: Path) -> list[dict]:
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
            links = _extract_wikilinks(text)
            tags  = _extract_tags(text, fm)
            words = set(re.sub(r"[^a-zA-Z]", " ", body.lower()).split())

            pages.append({
                "id":         f.stem,
                "path":       str(f),
                "type":       sub.rstrip("s"),  # concepts→concept etc
                "title":      fm.get("title", f.stem).strip('"'),
                "cluster":    fm.get("cluster", "").strip('"'),
                "confidence": fm.get("confidence", "medium"),
                "tags":       tags,
                "links":      links,
                "words":      words,
                "body":       body[:1500],
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


def _extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|#]+)", text)


def _extract_tags(text: str, fm: dict) -> list[str]:
    inline  = re.findall(r"#([a-zA-Z][\w/-]*)", text)
    fm_tags = re.findall(r"[\w/-]+", fm.get("tags", ""))
    return list(set(inline + fm_tags))


# ─────────────────────────────────────────────────────────────
# Bridge connections
# ─────────────────────────────────────────────────────────────

def find_bridge_connections(pages: list[dict], max_results: int = 3) -> list[dict]:
    """
    Find pairs of pages that share structure but have no direct wikilink.
    Uses three signals:
    1. Shared tags (but no link between them)
    2. Both linked FROM same third page (co-citation)
    3. High word overlap in body text
    """
    page_map   = {p["id"]: p for p in pages}
    all_links  = {p["id"]: set(p["links"]) for p in pages}
    bridges    = []
    seen_pairs = set()

    for i, pa in enumerate(pages):
        for pb in pages[i+1:]:
            pair_key = tuple(sorted([pa["id"], pb["id"]]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Skip if already linked
            if pb["id"] in all_links.get(pa["id"], set()) or \
               pa["id"] in all_links.get(pb["id"], set()):
                continue

            # Skip if same page
            if pa["id"] == pb["id"]:
                continue

            score  = 0
            reason = []

            # Signal 1: shared tags
            shared_tags = set(pa["tags"]) & set(pb["tags"])
            skip_tags   = {"knowledge-graph", "concept", "tool", "moc"}
            meaningful_tags = shared_tags - skip_tags
            if meaningful_tags:
                score  += len(meaningful_tags) * 2
                reason.append(f"share tags: {', '.join(list(meaningful_tags)[:3])}")

            # Signal 2: co-citation (both linked from same page)
            co_citations = []
            for pc in pages:
                if pc["id"] in (pa["id"], pb["id"]):
                    continue
                if pa["id"] in all_links.get(pc["id"], set()) and \
                   pb["id"] in all_links.get(pc["id"], set()):
                    co_citations.append(pc["id"])
            if co_citations:
                score  += len(co_citations) * 3
                reason.append(f"both cited by [[{co_citations[0]}]]")

            # Signal 3: word overlap
            common_words = pa["words"] & pb["words"]
            stop_words   = {"the", "a", "an", "is", "are", "was", "were",
                            "and", "or", "to", "of", "in", "that", "it",
                            "this", "for", "on", "with", "as", "at", "by"}
            meaningful_words = common_words - stop_words - \
                               {w for w in common_words if len(w) < 4}
            if len(meaningful_words) >= 8:
                score  += 1
                reason.append(f"high vocabulary overlap ({len(meaningful_words)} words)")

            # Same cluster bonus
            if pa["cluster"] and pb["cluster"] and pa["cluster"] == pb["cluster"]:
                score += 2

            if score >= 4:
                # Guess relationship type
                rel = _guess_relationship(pa, pb)
                bridges.append({
                    "page_a": pa["id"],
                    "page_b": pb["id"],
                    "score":  score,
                    "reason": "; ".join(reason),
                    "rel":    rel,
                })

    bridges.sort(key=lambda x: x["score"], reverse=True)
    return bridges[:max_results]


def _guess_relationship(pa: dict, pb: dict) -> str:
    """Heuristic: guess likely relationship type from page content."""
    a_body = pa["body"].lower()
    b_body = pb["body"].lower()

    if any(w in a_body for w in ["unlike", "contrast", "different", "instead"]):
        return "contrasts_with"
    if any(w in a_body for w in ["requires", "depends", "needs", "built on"]):
        return "depends_on"
    if any(w in a_body for w in ["leads to", "results in", "causes", "enables"]):
        return "leads_to"
    if any(w in a_body for w in ["part of", "component", "subset", "type of"]):
        return "part_of"
    return "relates_to"


# ─────────────────────────────────────────────────────────────
# Implicit sequences
# ─────────────────────────────────────────────────────────────

def find_implicit_sequences(pages: list[dict], max_results: int = 2) -> list[dict]:
    """
    Find A → B → C chains where A doesn't link to C directly.
    """
    page_map  = {p["id"]: p for p in pages}
    all_links = {p["id"]: set(p["links"]) for p in pages}
    sequences = []

    for pa in pages:
        a_links = all_links.get(pa["id"], set())
        for b_id in a_links:
            pb = page_map.get(b_id)
            if not pb:
                continue
            b_links = all_links.get(b_id, set())
            for c_id in b_links:
                if c_id == pa["id"]:
                    continue
                if c_id in a_links:
                    continue  # A already links to C
                pc = page_map.get(c_id)
                if not pc:
                    continue

                sequences.append({
                    "a":     pa["id"],
                    "b":     b_id,
                    "c":     c_id,
                    "chain": f"[[{pa['id']}]] → [[{b_id}]] → [[{c_id}]]",
                })

    return sequences[:max_results]


# ─────────────────────────────────────────────────────────────
# Anomaly detection
# ─────────────────────────────────────────────────────────────

def find_anomaly(pages: list[dict]) -> str:
    """Find one interesting pattern or anomaly in the wiki."""
    if not pages:
        return ""

    # Most linked-to page (hub)
    link_counts = defaultdict(int)
    for p in pages:
        for link in p["links"]:
            link_counts[link] += 1

    if link_counts:
        top = max(link_counts, key=link_counts.get)
        count = link_counts[top]
        if count >= 3:
            return (
                f"[[{top}]] is your most-referenced page ({count} incoming links) "
                f"but may be undersized relative to its importance — "
                f"consider expanding it or splitting into sub-concepts."
            )

    # Cluster with no inter-cluster links
    clusters = defaultdict(list)
    for p in pages:
        if p["cluster"]:
            clusters[p["cluster"]].append(p["id"])

    page_map = {p["id"]: p for p in pages}
    for cluster, members in clusters.items():
        if len(members) < 2:
            continue
        external_links = 0
        for mid in members:
            page = page_map.get(mid)
            if page:
                for link in page["links"]:
                    if link not in members:
                        external_links += 1
        if external_links == 0:
            return (
                f"The '{cluster}' cluster has {len(members)} pages "
                f"but zero links to other clusters — it's an island. "
                f"Consider connecting it to the broader wiki."
            )

    # High confidence pages with no incoming links
    orphan_high = [
        p["id"] for p in pages
        if p["confidence"] == "high"
        and link_counts.get(p["id"], 0) == 0
    ]
    if orphan_high:
        return (
            f"[[{orphan_high[0]}]] is marked high-confidence but has no "
            f"incoming wikilinks — it's authoritative but isolated. "
            f"Link it from related pages to activate it."
        )

    return ""


# ─────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────

def render_discoveries(today_str, pages, bridges, sequences, anomaly) -> str:
    month_day = date.fromisoformat(today_str).strftime("%B %d")
    lines = [
        "---",
        f'title: "Discoveries — {today_str}"',
        f"date: {today_str}",
        "type: discoveries",
        f"wiki_pages_scanned: {len(pages)}",
        "---",
        "",
        f"# Discoveries — {month_day}",
        f"*{len(pages)} wiki pages scanned*",
        "",
    ]

    if bridges:
        lines += ["## Bridge connections", ""]
        for i, b in enumerate(bridges, 1):
            lines += [
                f"### {i}. [[{b['page_a']}]] ↔ [[{b['page_b']}]]",
                f"**Why this matters:** {b['reason']}",
                f"**Suggested link type:** `{b['rel']}`",
                f"**Action:** Add to [[{b['page_a']}]]: "
                f"`- **{b['rel']}** → [[{b['page_b']}]]`",
                "",
            ]

    if sequences:
        lines += ["## Implicit sequences", ""]
        for i, s in enumerate(sequences, 1):
            lines += [
                f"### {i}. {s['chain']}",
                f"[[{s['a']}]] links to [[{s['b']}]], which links to [[{s['c']}]], "
                f"but [[{s['a']}]] doesn't link to [[{s['c']}]] directly.",
                f"**Action:** Add to [[{s['a']}]]: `- **leads_to** → [[{s['c']}]]`",
                "",
            ]

    if anomaly:
        lines += ["## One surprising observation", "", anomaly, ""]

    if not any([bridges, sequences, anomaly]):
        lines += [
            "_No significant new connections found._",
            "",
            "Your wiki is well-connected for its current size.",
            "Ingest more content and run discover again.",
            "",
        ]

    return "\n".join(lines)


if __name__ == "__main__":
    main()
