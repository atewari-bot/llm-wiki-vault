from pathlib import Path as _Path
from dotenv import load_dotenv as _lde
_lde(_Path(__file__).parent / ".env")

#!/usr/bin/env python3
"""
knowledge_graph_builder.py
Build an AI-enriched knowledge graph from raw/ notes.
Writes entity pages directly into wiki/ — no staging directory.

Usage:
  python knowledge_graph_builder.py --vault ~/llm-wiki-vault
  python knowledge_graph_builder.py --vault ~/llm-wiki-vault --inbox-only
  python knowledge_graph_builder.py --vault ~/llm-wiki-vault --drawio diagram.xml
  python knowledge_graph_builder.py --vault ~/llm-wiki-vault --dry-run
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from parsers import parse_raw, parse_miro, parse_drawio, is_drawio
from enricher import enrich
from graph_builder import build_graph, graph_to_json, save_graph_json
from exporters import export_to_vault, export_miro_xml


def main():
    parser = argparse.ArgumentParser(
        description="Build knowledge graph from raw/ notes → write directly to wiki/"
    )
    parser.add_argument("--vault", metavar="PATH", required=False,
                        help="Path to llm-wiki-vault (reads raw/, writes to wiki/)")
    parser.add_argument("--miro",   metavar="XML")
    parser.add_argument("--drawio", metavar="XML")
    parser.add_argument("--xml",    metavar="XML", help="Auto-detect Miro or draw.io")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — no files written")
    parser.add_argument("--no-miro-export", action="store_true")
    parser.add_argument("--mark-processed", action="store_true",
                        help="Tag note files as processed after ingestion")

    args = parser.parse_args()

    if not any([args.vault, args.miro, args.drawio, args.xml]):
        parser.print_help()
        sys.exit(1)

    notes, nodes, edges = [], [], []
    vault_path = None

    # ── Parse raw/ ────────────────────────────────────────────
    if args.vault:
        vault_path = Path(args.vault).expanduser().resolve()
        print(f"📂 Reading raw/  ({vault_path})")
        notes = parse_raw(str(vault_path))

        by_folder = {}
        for n in notes:
            by_folder.setdefault(n["subfolder"], 0)
            by_folder[n["subfolder"]] += 1
        for folder, count in sorted(by_folder.items()):
            print(f"   raw/{folder}/: {count} notes")
        print(f"   Total: {len(notes)} notes")

    # ── Parse diagrams ────────────────────────────────────────
    for xml_path, label, parser_fn in [
        (args.miro,   "Miro",    parse_miro),
        (args.drawio, "draw.io", parse_drawio),
    ]:
        if xml_path:
            print(f"📐 Parsing {label}: {xml_path}")
            n, e = parser_fn(xml_path)
            nodes += n; edges += e
            print(f"   → {len(n)} nodes, {len(e)} edges")

    if args.xml:
        fmt = "draw.io" if is_drawio(args.xml) else "Miro"
        fn  = parse_drawio if fmt == "draw.io" else parse_miro
        print(f"📐 Auto-detected {fmt}: {args.xml}")
        n, e = fn(args.xml)
        nodes += n; edges += e
        print(f"   → {len(n)} nodes, {len(e)} edges")

    if len(notes) + len(nodes) == 0:
        print("❌ No content found. Is raw/ empty?")
        sys.exit(1)

    # ── Enrich ────────────────────────────────────────────────
    print(f"\n🧠 Sending {len(notes) + len(nodes)} items to Claude...")
    enriched = enrich(
        notes=notes or None,
        nodes=nodes or None,
        edges=edges or None
    )

    ne = len(enriched.get("entities", []))
    nr = len(enriched.get("relationships", []))
    nc = len(enriched.get("clusters", []))
    ng = len(enriched.get("gaps", []))
    print(f"✅ {ne} entities  {nr} relationships  {nc} clusters  {ng} gaps")

    if args.dry_run:
        print("\n[DRY RUN — no files written]\n")
        for e in enriched.get("entities", [])[:10]:
            print(f"  [{e['type']}] {e['label']}")
        print("\nGaps:")
        for g in enriched.get("gaps", [])[:5]:
            print(f"  💡 {g['suggested_entity']}: {g['description']}")
        return

    # ── Build graph ───────────────────────────────────────────
    G = build_graph(enriched)

    # Save graph.json inside .tools/ for reference
    if vault_path:
        save_graph_json(
            graph_to_json(G, enriched),
            str(vault_path / ".tools" / "graph.json")
        )

    # ── Write directly to wiki/ ───────────────────────────────
    if vault_path:
        print(f"\n📝 Writing to wiki/...")
        export_to_vault(G, enriched, str(vault_path))
    
    # Optional Miro export → reports/
    if not args.no_miro_export and vault_path:
        miro_path = vault_path / "reports" / "miro_enriched.xml"
        export_miro_xml(G, enriched, str(miro_path))

    # ── Mark inbox processed ──────────────────────────────────
    if args.mark_processed and vault_path and args.inbox_only:
        _mark_inbox_processed(vault_path / "raw" / "inbox")

    print(f"\n🎉 Done!")
    print(f"   Wiki updated:  wiki/")
    print(f"   Graph report:  wiki/meta/graph-report.md")
    print(f"   Graph data:    .tools/graph.json")


def _mark_inbox_processed(inbox_dir: Path):
    from datetime import date
    today = date.today().isoformat()
    count = 0
    for f in inbox_dir.glob("*.md"):
        if f.name.startswith("."):
            continue
        text = f.read_text(encoding="utf-8")
        if "#processed" not in text:
            if text.startswith("---"):
                text = text.replace("\n---\n", f"\nprocessed: {today}\n---\n", 1)
            else:
                text = f"processed: {today}\n\n" + text
            f.write_text(text, encoding="utf-8")
            count += 1
    if count:
        print(f"✅ Marked {count} inbox files as processed")


if __name__ == "__main__":
    main()
