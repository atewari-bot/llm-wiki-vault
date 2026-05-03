"""
parsers.py — Parse raw notes from vault, Miro XML, and draw.io XML into nodes/edges.
"""
import os
import re
import xml.etree.ElementTree as ET
import base64
import zlib
from pathlib import Path
from urllib.parse import unquote


# ─────────────────────────────────────────────
# Raw folder parser (scoped to raw/ only)
# ─────────────────────────────────────────────

def parse_raw(vault_path: str, subfolders: list[str] = None) -> list[dict]:
    """
    Walk only the raw/ directory of a vault.
    Skips wiki/, reports/, .tools/ — only reads source material.

    subfolders: optional list like ['notes', 'todos'] to narrow further.
                Defaults to all of raw/.
    """
    vault = Path(vault_path)
    raw_dir = vault / "raw"

    if not raw_dir.exists():
        print(f"⚠️  No raw/ directory found at {raw_dir}")
        return []

    search_dirs = []
    if subfolders:
        for sf in subfolders:
            d = raw_dir / sf
            if d.exists():
                search_dirs.append(d)
            else:
                print(f"⚠️  Subfolder raw/{sf}/ not found, skipping")
    else:
        search_dirs = [raw_dir]

    notes = []
    for search_dir in search_dirs:
        for md_file in sorted(search_dir.rglob("*.md")):
            # Skip .gitkeep and hidden files
            if md_file.name.startswith(".") or md_file.stem == ".gitkeep":
                continue

            raw_text = md_file.read_text(encoding="utf-8", errors="ignore")
            if not raw_text.strip():
                continue

            title = md_file.stem
            frontmatter = _parse_frontmatter(raw_text)
            body = _strip_frontmatter(raw_text)
            tags = _extract_tags(raw_text, frontmatter)
            links = _extract_wikilinks(raw_text)

            # Track which subfolder it came from
            try:
                rel = md_file.relative_to(raw_dir)
                subfolder = rel.parts[0] if len(rel.parts) > 1 else "raw"
            except ValueError:
                subfolder = "raw"

            notes.append({
                "id":          str(md_file.relative_to(vault)),
                "title":       title,
                "body":        body[:3000],
                "tags":        tags,
                "links":       links,
                "frontmatter": frontmatter,
                "path":        str(md_file),
                "subfolder":   subfolder,
                "status":      frontmatter.get("status", "unprocessed"),
            })

    return notes


def parse_obsidian(vault_path: str) -> list[dict]:
    """
    Legacy: walk the entire vault. Kept for backward compatibility.
    Prefer parse_raw() for targeted ingestion.
    """
    vault = Path(vault_path)
    notes = []
    skip_dirs = {"wiki", "reports", ".tools", ".claude", ".obsidian"}

    for md_file in sorted(vault.rglob("*.md")):
        # Skip non-raw directories
        parts = md_file.relative_to(vault).parts
        if any(p in skip_dirs for p in parts):
            continue
        if md_file.name.startswith("."):
            continue

        raw_text = md_file.read_text(encoding="utf-8", errors="ignore")
        if not raw_text.strip():
            continue

        title = md_file.stem
        frontmatter = _parse_frontmatter(raw_text)
        body = _strip_frontmatter(raw_text)
        tags = _extract_tags(raw_text, frontmatter)
        links = _extract_wikilinks(raw_text)

        notes.append({
            "id":          str(md_file.relative_to(vault)),
            "title":       title,
            "body":        body[:3000],
            "tags":        tags,
            "links":       links,
            "frontmatter": frontmatter,
            "path":        str(md_file),
            "subfolder":   "raw",
            "status":      frontmatter.get("status", "unprocessed"),
        })

    return notes


# ─────────────────────────────────────────────
# Miro
# ─────────────────────────────────────────────

def parse_miro(xml_path: str) -> tuple[list[dict], list[dict]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    nodes, edges = [], []
    color_to_type = {
        "yellow": "concept", "blue": "tool", "green": "insight",
        "red": "question", "purple": "process",
    }
    for widget in root.iter("widget"):
        wtype = widget.get("type", "")
        wid = widget.get("id", "")
        text = _clean_html(widget.get("text", "") or widget.findtext("text") or "")
        if wtype in ("text", "sticker", "card", "shape") and text:
            color = widget.get("style", "")
            etype = next((v for k, v in color_to_type.items() if k in color.lower()), "concept")
            nodes.append({"id": wid, "label": text[:200], "type": etype, "source": "miro"})
        elif wtype == "line":
            src = widget.get("startWidgetId") or widget.get("startWidget", {})
            tgt = widget.get("endWidgetId") or widget.get("endWidget", {})
            label = _clean_html(widget.get("text", ""))
            if src and tgt:
                edges.append({"source": src, "target": tgt, "label": label or "relates_to"})
    return nodes, edges


# ─────────────────────────────────────────────
# draw.io
# ─────────────────────────────────────────────

def is_drawio(xml_path: str) -> bool:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        return root.tag in ("mxGraphModel", "mxfile") or any(
            True for _ in root.iter("mxGraphModel")
        )
    except Exception:
        return False


def parse_drawio(xml_path: str) -> tuple[list[dict], list[dict]]:
    """Flat parse — concatenates nodes and edges across all pages.

    Kept for backward compatibility. New code should prefer
    :func:`parse_drawio_pages` because flattening multi-page mxfiles
    produces unreadable Mermaid output.
    """
    pages = parse_drawio_pages(xml_path)
    nodes, edges = [], []
    for _name, n, e in pages:
        nodes.extend(n)
        edges.extend(e)
    return nodes, edges


def parse_drawio_pages(xml_path: str):
    """Parse a draw.io export into a list of pages, one entry per ``<diagram>``.

    Returns a list of ``(page_name, nodes, edges)`` tuples. Multi-page mxfiles
    return one entry per page; single-page ``mxGraphModel`` files return one entry.

    Edge recovery: edges with loose endpoints (no ``source``/``target`` attr,
    coordinates in ``<mxPoint as="sourcePoint"/targetPoint">`` instead) get
    matched to the nearest vertex by Manhattan distance. Vertices with empty
    labels are kept if they're referenced by an edge so endpoints aren't lost.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    page_specs = []
    if root.tag == "mxfile":
        for idx, diag in enumerate(root.findall("diagram")):
            page_name = (diag.get("name") or f"page-{idx+1}").strip()
            graph_root = _decode_diagram(diag)
            if graph_root is not None:
                page_specs.append((page_name, graph_root))
    else:
        page_specs.append(("diagram", root))

    return [_parse_page(name, gr) for name, gr in page_specs]


def _decode_diagram(diag):
    """Resolve a ``<diagram>`` element to its graph root, handling all three
    storage formats:
        (a) inline ``<mxGraphModel>`` child (uncompressed)
        (b) base64+deflate-compressed text body (standard export)
        (c) URL-encoded raw XML in the text body (older saves)
    """
    inline = diag.find("mxGraphModel")
    if inline is not None:
        return inline
    content = (diag.text or "").strip()
    if not content:
        return None
    try:
        decoded = base64.b64decode(content)
        xml_str = zlib.decompress(decoded, -zlib.MAX_WBITS).decode("utf-8")
        return ET.fromstring(unquote(xml_str))
    except Exception:
        try:
            return ET.fromstring(unquote(content))
        except Exception:
            return None


def _parse_page(page_name: str, graph_root):
    """Parse a single page, capturing nodes, edges, and loose-endpoint edges.

    Page-scoping matters: cell IDs are only unique within a page, so we
    resolve source/target IDs against THIS page's vertex map only.
    """
    by_id = {}
    for cell in graph_root.iter("mxCell"):
        by_id[cell.get("id", "")] = cell

    # Vertex registry with geometry. Keep ALL vertex cells (including
    # empty-value ones) so they can serve as edge endpoints.
    vertex_geom = {}
    for cid, cell in by_id.items():
        if cell.get("vertex") != "1" or cid in ("0", "1"):
            continue
        geom = cell.find("mxGeometry")
        x = float(geom.get("x", 0)) if geom is not None else 0.0
        y = float(geom.get("y", 0)) if geom is not None else 0.0
        w = float(geom.get("width", 0)) if geom is not None else 0.0
        h = float(geom.get("height", 0)) if geom is not None else 0.0
        vertex_geom[cid] = {
            "x": x, "y": y, "w": w, "h": h,
            "cx": x + w / 2.0, "cy": y + h / 2.0,
            "label": _clean_html(cell.get("value", "")),
            "style": cell.get("style", ""),
        }

    # Edges with loose-endpoint recovery
    edges_raw = []
    for cid, cell in by_id.items():
        if cell.get("edge") != "1":
            continue
        src = cell.get("source") or ""
        tgt = cell.get("target") or ""
        label = _clean_html(cell.get("value", ""))

        geom = cell.find("mxGeometry")
        src_pt, tgt_pt = None, None
        if geom is not None:
            for p in geom.findall("mxPoint"):
                role = p.get("as")
                try:
                    pt = (float(p.get("x", 0)), float(p.get("y", 0)))
                except (TypeError, ValueError):
                    continue
                if role == "sourcePoint":
                    src_pt = pt
                elif role == "targetPoint":
                    tgt_pt = pt

        if src and src in vertex_geom:
            src_id = src
        elif src_pt is not None:
            src_id = _nearest_vertex(src_pt, vertex_geom)
        else:
            src_id = None

        if tgt and tgt in vertex_geom:
            tgt_id = tgt
        elif tgt_pt is not None:
            tgt_id = _nearest_vertex(tgt_pt, vertex_geom)
        else:
            tgt_id = None

        if src_id and tgt_id and src_id != tgt_id:
            edges_raw.append({
                "source": src_id,
                "target": tgt_id,
                "label": label,
            })

    # Surface a vertex as a node if it has a label OR is referenced by an edge.
    # Empty-label container/group cells with no edge references stay hidden.
    referenced = set()
    for e in edges_raw:
        referenced.add(e["source"])
        referenced.add(e["target"])

    nodes = []
    for cid, g in vertex_geom.items():
        if g["label"] or cid in referenced:
            etype = _drawio_style_to_type(g["style"])
            label = g["label"] or "(unlabeled)"
            nodes.append({
                "id": cid,
                "label": label[:200],
                "type": etype,
                "source": "drawio",
                "x": g["x"], "y": g["y"],
            })

    nodes.sort(key=lambda n: (n["y"], n["x"]))
    return page_name, nodes, edges_raw


def _nearest_vertex(point, vertex_geom):
    """Return the id of the vertex whose centre is closest to the given point."""
    if not vertex_geom:
        return None
    px, py = point
    best_id, best_d = None, float("inf")
    for vid, g in vertex_geom.items():
        d = abs(g["cx"] - px) + abs(g["cy"] - py)
        if d < best_d:
            best_d, best_id = d, vid
    return best_id


def _drawio_style_to_type(style: str) -> str:
    s = style.lower()
    if "ellipse" in s or "circle" in s: return "concept"
    if "rhombus" in s or "diamond" in s: return "question"
    if "cylinder" in s: return "tool"
    return "concept"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL).strip()


def _extract_tags(text: str, frontmatter: dict) -> list[str]:
    inline = re.findall(r"#([a-zA-Z][\w/-]*)", text)
    fm_tags = re.findall(r"[\w/-]+", frontmatter.get("tags", ""))
    return list(set(inline + fm_tags))


def _extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|#]+)", text)


def _clean_html(text: str) -> str:
    """Strip HTML tags AND decode entities, so '&gt; Run' becomes '> Run'."""
    import html as _html
    stripped = re.sub(r"<[^>]+>", "", text or "")
    return _html.unescape(stripped).strip()
