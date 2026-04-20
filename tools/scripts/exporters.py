"""
exporters.py — Write enriched graph directly into the vault's wiki/ folder.
No intermediate output/ staging. Entity pages go to wiki/{type}/, 
graph report goes to wiki/meta/graph-report.md.
"""
import networkx as nx
from pathlib import Path
from datetime import date
import xml.etree.ElementTree as ET

TODAY = date.today().isoformat()

TYPE_TO_SUBFOLDER = {
    "concept":      "concepts",
    "person":       "people",
    "tool":         "tools",
    "project":      "concepts",
    "question":     "concepts",
    "insight":      "concepts",
    "event":        "concepts",
    "process":      "concepts",
    "architecture": "concepts",
}


# ─────────────────────────────────────────────
# Main export entry point
# ─────────────────────────────────────────────

def export_to_vault(G: nx.DiGraph, enriched: dict, vault_path: str):
    """
    Write all outputs directly into the vault:
      wiki/concepts/, wiki/people/, wiki/tools/  ← entity pages
      wiki/meta/                                  ← cluster MOCs
      wiki/meta/graph-report.md                  ← gap report + summary
    """
    vault = Path(vault_path)
    wiki  = vault / "wiki"

    # Ensure subdirs exist
    for sub in ["concepts", "people", "tools", "meta"]:
        (wiki / sub).mkdir(parents=True, exist_ok=True)

    entity_map = {nid: G.nodes[nid]["label"] for nid in G.nodes}
    counts = {"created": 0, "updated": 0, "moc": 0}

    # ── Entity pages ──────────────────────────────────────────
    for nid in G.nodes:
        node   = G.nodes[nid]
        label  = node["label"]
        ntype  = node.get("type", "concept")
        subfolder = TYPE_TO_SUBFOLDER.get(ntype, "concepts")
        target_dir = wiki / subfolder
        safe_name  = _safe_filename(label)
        page_path  = target_dir / f"{safe_name}.md"

        outgoing = [
            (entity_map.get(t, t), d.get("type", "relates_to"), d.get("rationale", ""))
            for _, t, d in G.out_edges(nid, data=True)
        ]
        incoming = [
            (entity_map.get(s, s), d.get("type", "relates_to"))
            for s, _, d in G.in_edges(nid, data=True)
        ]
        related = list(dict.fromkeys(
            [tl for tl, _, _ in outgoing] + [sl for sl, _ in incoming]
        ))[:5]

        md = _entity_page(node, outgoing, incoming, related, nid)

        existed = page_path.exists()
        page_path.write_text(md, encoding="utf-8")
        if existed:
            counts["updated"] += 1
        else:
            counts["created"] += 1

    print(f"📄 Entity pages — created: {counts['created']}, updated: {counts['updated']}")

    # ── Cluster MOC pages → wiki/meta/ ───────────────────────
    for cluster in enriched.get("clusters", []):
        name    = cluster["name"]
        theme   = cluster.get("theme", "")
        members = [entity_map.get(eid, eid) for eid in cluster.get("entity_ids", [])]
        moc_path = wiki / "meta" / f"{_safe_filename(name)} (MOC).md"
        moc_path.write_text(_cluster_moc(name, theme, members), encoding="utf-8")
        counts["moc"] += 1

    print(f"🗺️  Cluster MOCs: {counts['moc']} → wiki/meta/")

    # ── Graph report → wiki/meta/graph-report.md ─────────────
    report_path = wiki / "meta" / "graph-report.md"
    report_path.write_text(_graph_report(enriched, G), encoding="utf-8")
    print(f"📊 Graph report → wiki/meta/graph-report.md")


# ─────────────────────────────────────────────
# Page builders
# ─────────────────────────────────────────────

def _entity_page(node, outgoing, incoming, related, nid) -> str:
    label   = node["label"]
    ntype   = node.get("type", "concept")
    desc    = node.get("description", "")
    aliases = node.get("aliases", [])
    cluster = node.get("cluster", "")

    lines = [
        "---",
        f'title: "{label}"',
        f"type: {ntype}",
        f"tags: [{ntype}, knowledge-graph]",
        f"created: {TODAY}",
        f"updated: {TODAY}",
        f"node_id: {nid}",
        f'cluster: "{cluster}"',
        "confidence: medium",
        "---",
        "",
        f"# {label}",
        "",
    ]

    if desc:
        lines += [desc, ""]

    if aliases:
        lines += [f"> Also known as: {', '.join(aliases)}", ""]

    if cluster:
        lines += [f"> Part of cluster: [[{cluster} (MOC)]]", ""]

    if outgoing:
        lines += ["## Relationships", ""]
        for tgt, rtype, rationale in outgoing:
            suffix = f" — {rationale}" if rationale else ""
            lines.append(f"- **{rtype}** → [[{tgt}]]{suffix}")
        lines.append("")

    if incoming:
        lines += ["## Referenced By", ""]
        for src, rtype in incoming:
            lines.append(f"- [[{src}]] **{rtype}** this")
        lines.append("")

    if related:
        lines += ["## See Also", ""]
        for r in related:
            lines.append(f"- [[{r}]]")
        lines.append("")

    return "\n".join(lines)


def _cluster_moc(name, theme, members) -> str:
    lines = [
        "---",
        f'title: "{name}"',
        "type: moc",
        "tags: [moc, cluster, knowledge-graph]",
        f"created: {TODAY}",
        f"updated: {TODAY}",
        "---",
        "",
        f"# {name}",
        "",
    ]
    if theme:
        lines += [f"**Theme:** {theme}", ""]
    lines += ["## Pages in this cluster", ""]
    for m in members:
        lines.append(f"- [[{m}]]")
    lines.append("")
    return "\n".join(lines)


def _graph_report(enriched: dict, G: nx.DiGraph) -> str:
    lines = [
        "---",
        'title: "Knowledge Graph Report"',
        "tags: [meta, report, knowledge-graph]",
        f"updated: {TODAY}",
        "---",
        "",
        "# Knowledge Graph Report",
        f"*Last built: {TODAY}*",
        "",
        "## Summary",
        "",
        enriched.get("summary", "No summary generated."),
        "",
        "## Stats",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Entities | {G.number_of_nodes()} |",
        f"| Relationships | {G.number_of_edges()} |",
        f"| Clusters | {len(enriched.get('clusters', []))} |",
        f"| Gaps identified | {len(enriched.get('gaps', []))} |",
        f"| Graph density | {round(nx.density(G), 4)} |",
        "",
    ]

    gaps = enriched.get("gaps", [])
    if gaps:
        entity_map = {nid: G.nodes[nid]["label"] for nid in G.nodes}
        lines += ["## Gaps & Suggested Research", ""]
        for i, gap in enumerate(gaps, 1):
            entity = gap.get("suggested_entity", "Unknown")
            desc   = gap.get("description", "")
            connected = [
                f"[[{entity_map.get(c, c)}]]"
                for c in gap.get("connected_to", [])
            ]
            lines.append(f"### {i}. {entity}")
            lines.append(desc)
            if connected:
                lines.append(f"*Connected to: {', '.join(connected)}*")
            lines.append("")

    clusters = enriched.get("clusters", [])
    if clusters:
        lines += ["## Clusters", ""]
        for c in clusters:
            lines.append(f"- **[[{c['name']} (MOC)]]** — {c.get('theme', '')}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Miro XML export (optional)
# ─────────────────────────────────────────────

def export_miro_xml(G: nx.DiGraph, enriched: dict, output_path: str):
    """Write a Miro-compatible XML board to the given path."""
    board = ET.Element("board")
    type_colors = {
        "concept": "#FFD700", "person": "#FF6B9D", "tool": "#4ECDC4",
        "question": "#FF6B35", "insight": "#95E1D3", "process": "#A8E6CF",
        "project": "#88D8B0", "event": "#FFAAA5", "architecture": "#B4A0FF",
    }
    cols, sx, sy = 6, 250, 180
    for i, (nid, data) in enumerate(G.nodes(data=True)):
        x = (i % cols) * sx + 50
        y = (i // cols) * sy + 50
        color = type_colors.get(data.get("type", "concept"), "#FFD700")
        ET.SubElement(board, "widget", {
            "type": "sticker", "id": nid,
            "x": str(x), "y": str(y),
            "width": "220", "height": "120",
            "style": f"backgroundColor:{color};",
            "text": f"<b>{data.get('label', nid)}</b>",
        })
    for u, v, data in G.edges(data=True):
        ET.SubElement(board, "widget", {
            "type": "line",
            "startWidgetId": u, "endWidgetId": v,
            "text": data.get("type", "relates_to"),
        })
    tree = ET.ElementTree(board)
    ET.indent(tree, space="  ")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"🗂️  Miro XML → {output_path}")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    import re
    return re.sub(r'[<>:"/\\|?*]', "-", name).strip()[:80]
