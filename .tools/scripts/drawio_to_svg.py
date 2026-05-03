#!/usr/bin/env python3
"""
drawio_to_svg.py — Convert a draw.io XML export to inline SVG, one per page.

Why SVG (and not Mermaid):
  * Mermaid's flowchart auto-layout discards spatial information. A draw.io
    diagram of a "Linux VM" frame containing a "Container" containing a
    process — visually nested — becomes a flat graph in Mermaid because the
    nesting is encoded purely by overlapping bounding boxes, not by parent
    references.
  * SVG preserves the exact (x, y, width, height) from draw.io, so visually
    nested boxes stay visually nested when rendered.
  * Inline SVG embeds in Obsidian markdown without any plugin.

What it captures:
  * Vertex shapes: rectangle (rounded or square), ellipse/circle, rhombus
    (decision), cylinder (data store), swimlane (group container).
  * Per-cell styling: fillColor, strokeColor, strokeWidth, fontSize, fontColor,
    text alignment, dashed/solid strokes.
  * Edges: rendered as polylines with arrow markers. Loose-endpoint edges
    (matched to nearest vertex) draw from the vertex they were resolved to.
  * Text wrapping: split the label into lines that fit inside the box width.

Usage:
    python .tools/scripts/drawio_to_svg.py path/to/diagram.drawio.xml
    python .tools/scripts/drawio_to_svg.py path --no-fence

API:
    from drawio_to_svg import to_svg_pages
    pages = to_svg_pages("file.drawio.xml")
    for page_name, svg_string in pages: ...
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).parent))
from parsers import is_drawio, _decode_diagram, _clean_html  # type: ignore  # noqa: E402


# ────────────────────────────────────────────────────────────────────────────
# Style parsing
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_FILL = "#ffffff"
DEFAULT_STROKE = "#000000"
DEFAULT_FONT_SIZE = 12
DEFAULT_STROKE_WIDTH = 1.0


def _parse_style(style: str) -> dict:
    """draw.io style strings are 'k1=v1;k2=v2;shape;...' with bare keys
    (like 'ellipse' or 'shape=cylinder') for the shape itself."""
    out = {"shape": "rect"}
    if not style:
        return out
    for piece in style.split(";"):
        piece = piece.strip()
        if not piece:
            continue
        if "=" in piece:
            k, _, v = piece.partition("=")
            out[k.strip()] = v.strip()
        else:
            # Bare keyword — usually the shape (ellipse, rhombus, etc.)
            out["shape"] = piece

    # Normalize the shape: "shape=cylinder" wins over a bare keyword
    if "shape" in out and out["shape"] not in ("rect", "ellipse", "rhombus"):
        # Already set by 'shape=...' — leave as-is
        pass
    elif out.get("ellipse") is None and "ellipse" in style.lower():
        out["shape"] = "ellipse"
    elif "rhombus" in style.lower():
        out["shape"] = "rhombus"

    return out


def _shape_kind(style: dict) -> str:
    s = style.get("shape", "rect").lower()
    if s in ("ellipse", "ellipse;"): return "ellipse"
    if s in ("rhombus", "rhombus;"): return "rhombus"
    if "cylinder" in s: return "cylinder"
    if "curlybracket" in s: return "bracket"
    if "swimlane" in s: return "swimlane"
    return "rect"


# ────────────────────────────────────────────────────────────────────────────
# XML escape
# ────────────────────────────────────────────────────────────────────────────

def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ────────────────────────────────────────────────────────────────────────────
# Per-page extraction (richer than parsers._parse_page — keeps full geometry/style)
# ────────────────────────────────────────────────────────────────────────────

def _extract_page(graph_root) -> dict:
    """Return {vertices: list[dict], edges: list[dict]} with full styling info."""
    by_id = {c.get("id", ""): c for c in graph_root.iter("mxCell")}

    vertices = {}
    for cid, cell in by_id.items():
        if cell.get("vertex") != "1" or cid in ("0", "1"):
            continue
        geom = cell.find("mxGeometry")
        if geom is None:
            continue
        try:
            x = float(geom.get("x", 0))
            y = float(geom.get("y", 0))
            w = float(geom.get("width", 0))
            h = float(geom.get("height", 0))
        except (TypeError, ValueError):
            continue
        style = _parse_style(cell.get("style", "") or "")
        vertices[cid] = {
            "id": cid,
            "x": x, "y": y, "w": w, "h": h,
            "cx": x + w / 2.0, "cy": y + h / 2.0,
            "label": _clean_html(cell.get("value", "") or ""),
            "style": style,
            "kind": _shape_kind(style),
        }

    edges = []
    for cid, cell in by_id.items():
        if cell.get("edge") != "1":
            continue
        src = cell.get("source") or ""
        tgt = cell.get("target") or ""
        label = _clean_html(cell.get("value", "") or "")
        style = _parse_style(cell.get("style", "") or "")

        # Loose endpoints from <mxPoint as="sourcePoint"/targetPoint">
        geom = cell.find("mxGeometry")
        src_pt = tgt_pt = None
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

        if src and src in vertices:
            src_id = src
        elif src_pt is not None:
            src_id = _nearest(src_pt, vertices)
        else:
            src_id = None

        if tgt and tgt in vertices:
            tgt_id = tgt
        elif tgt_pt is not None:
            tgt_id = _nearest(tgt_pt, vertices)
        else:
            tgt_id = None

        if src_id and tgt_id and src_id != tgt_id:
            edges.append({
                "source": src_id, "target": tgt_id,
                "label": label, "style": style,
            })

    return {"vertices": vertices, "edges": edges}


def _nearest(pt, vertices):
    if not vertices:
        return None
    px, py = pt
    return min(vertices, key=lambda vid:
               abs(vertices[vid]["cx"] - px) + abs(vertices[vid]["cy"] - py))


# ────────────────────────────────────────────────────────────────────────────
# Text wrapping (rough — uses an average char-width estimate)
# ────────────────────────────────────────────────────────────────────────────

def _wrap_text(label: str, box_w: float, font_size: int) -> list[str]:
    """Split a label into lines that fit roughly within box_w pixels.
    A monospace approximation: ~0.55 * font_size pixels per char average.
    """
    if not label:
        return []
    label = label.replace(" ", " ").replace("&nbsp;", " ").strip()
    # Hard newlines first
    paragraphs = label.split("\n")
    lines = []
    char_w = max(font_size * 0.55, 4.0)
    max_chars = max(int((box_w - 8) / char_w), 6)
    for para in paragraphs:
        words = para.split()
        if not words:
            continue
        current = words[0]
        for w in words[1:]:
            if len(current) + 1 + len(w) <= max_chars:
                current += " " + w
            else:
                lines.append(current)
                current = w
        lines.append(current)
    return lines


# ────────────────────────────────────────────────────────────────────────────
# Edge-endpoint clipping — bring the line endpoint to the box edge
# ────────────────────────────────────────────────────────────────────────────

def _clip_to_box(cx, cy, target_x, target_y, w, h):
    """Given a vertex at center (cx,cy) with size (w,h) and a target point,
    return the point on the box edge along the cx→target line. Used to
    avoid arrowheads stabbing into the middle of a box."""
    dx = target_x - cx
    dy = target_y - cy
    if dx == 0 and dy == 0:
        return cx, cy
    half_w = w / 2.0
    half_h = h / 2.0
    # Scale dx, dy so that |dx|=half_w or |dy|=half_h (whichever hits first)
    if abs(dx) * half_h > abs(dy) * half_w:
        s = half_w / abs(dx) if dx != 0 else 0
    else:
        s = half_h / abs(dy) if dy != 0 else 0
    return cx + dx * s, cy + dy * s


# ────────────────────────────────────────────────────────────────────────────
# Per-vertex SVG rendering
# ────────────────────────────────────────────────────────────────────────────

def _render_vertex(v: dict) -> str:
    style = v["style"]
    kind = v["kind"]
    fill = style.get("fillColor", DEFAULT_FILL)
    stroke = style.get("strokeColor", DEFAULT_STROKE)
    stroke_w = float(style.get("strokeWidth", DEFAULT_STROKE_WIDTH) or 1.0)
    font_size = int(float(style.get("fontSize", DEFAULT_FONT_SIZE) or 12))
    font_color = style.get("fontColor", "#000000")
    rounded = style.get("rounded") == "1"
    dashed = style.get("dashed") == "1"

    # Skip "none" fill
    if fill.lower() in ("none", ""):
        fill = "none"
    if stroke.lower() in ("none", ""):
        stroke = "none"

    x, y, w, h = v["x"], v["y"], v["w"], v["h"]
    cx, cy = v["cx"], v["cy"]

    parts = []
    dash_attr = ' stroke-dasharray="4,3"' if dashed else ""

    if kind == "ellipse":
        parts.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w/2:.1f}" ry="{h/2:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.1f}"{dash_attr}/>'
        )
    elif kind == "rhombus":
        # Diamond: top, right, bottom, left
        pts = f"{cx:.1f},{y:.1f} {x+w:.1f},{cy:.1f} {cx:.1f},{y+h:.1f} {x:.1f},{cy:.1f}"
        parts.append(
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_w:.1f}"{dash_attr}/>'
        )
    elif kind == "cylinder":
        # Body + top ellipse — a stylized data-store shape
        rx = w / 2
        ry = min(h * 0.15, 12)
        parts.append(
            f'<path d="M {x:.1f} {y+ry:.1f} L {x:.1f} {y+h-ry:.1f} '
            f'A {rx:.1f} {ry:.1f} 0 0 0 {x+w:.1f} {y+h-ry:.1f} '
            f'L {x+w:.1f} {y+ry:.1f} '
            f'A {rx:.1f} {ry:.1f} 0 0 0 {x:.1f} {y+ry:.1f} Z" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.1f}"{dash_attr}/>'
        )
        parts.append(
            f'<ellipse cx="{cx:.1f}" cy="{y+ry:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.1f}"{dash_attr}/>'
        )
    elif kind == "bracket":
        # Real curly bracket — orientation depends on style.direction. Default
        # in draw.io is east-pointing (opens to the right), so the brace's
        # "tip" is on the LEFT edge of the bbox. We trace a path that draws a
        # `}` shape using two cubic Beziers meeting at the tip.
        direction = (style.get("direction") or "east").lower()
        cx, cy = v["cx"], v["cy"]
        if direction in ("east", "west"):
            # Vertical brace
            tip_x = (x + w) if direction == "west" else x  # tip on the spine side
            spine_x = x if direction == "west" else (x + w)
            mid_y = cy
            curl = min(w * 0.6, 16)
            path = (
                f"M {spine_x:.1f} {y:.1f} "
                f"Q {spine_x - curl if direction=='west' else spine_x + curl:.1f} {y:.1f} "
                f"  {spine_x - curl if direction=='west' else spine_x + curl:.1f} {y + h*0.25:.1f} "
                f"L {spine_x - curl if direction=='west' else spine_x + curl:.1f} {mid_y - 4:.1f} "
                f"Q {spine_x - curl if direction=='west' else spine_x + curl:.1f} {mid_y:.1f} "
                f"  {tip_x:.1f} {mid_y:.1f} "
                f"Q {spine_x - curl if direction=='west' else spine_x + curl:.1f} {mid_y:.1f} "
                f"  {spine_x - curl if direction=='west' else spine_x + curl:.1f} {mid_y + 4:.1f} "
                f"L {spine_x - curl if direction=='west' else spine_x + curl:.1f} {y + h*0.75:.1f} "
                f"Q {spine_x - curl if direction=='west' else spine_x + curl:.1f} {y + h:.1f} "
                f"  {spine_x:.1f} {y + h:.1f}"
            )
        else:
            # Horizontal brace (north/south) — tip on top or bottom
            tip_y = y if direction == "south" else (y + h)
            spine_y = (y + h) if direction == "south" else y
            mid_x = cx
            curl = min(h * 0.6, 16)
            sign = -1 if direction == "south" else 1
            path = (
                f"M {x:.1f} {spine_y:.1f} "
                f"Q {x:.1f} {spine_y + sign * curl:.1f} "
                f"  {x + w*0.25:.1f} {spine_y + sign * curl:.1f} "
                f"L {mid_x - 4:.1f} {spine_y + sign * curl:.1f} "
                f"Q {mid_x:.1f} {spine_y + sign * curl:.1f} "
                f"  {mid_x:.1f} {tip_y:.1f} "
                f"Q {mid_x:.1f} {spine_y + sign * curl:.1f} "
                f"  {mid_x + 4:.1f} {spine_y + sign * curl:.1f} "
                f"L {x + w*0.75:.1f} {spine_y + sign * curl:.1f} "
                f"Q {x + w:.1f} {spine_y + sign * curl:.1f} "
                f"  {x + w:.1f} {spine_y:.1f}"
            )
        parts.append(
            f'<path d="{path}" fill="none" stroke="{stroke}" '
            f'stroke-width="{max(stroke_w, 1.5):.1f}" stroke-linecap="round"/>'
        )
    elif kind == "swimlane":
        # Group container — render as a rect with a header strip at top
        header_h = min(h * 0.15, 30)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.1f}"{dash_attr}/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{header_h:.1f}" '
            f'fill="{stroke}" opacity="0.15" stroke="none"/>'
        )
    else:  # rect (default)
        rx_attr = ' rx="6"' if rounded else ""
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w:.1f}"{dash_attr}{rx_attr}/>'
        )

    # Label, wrapped
    label = v["label"]
    if label:
        lines = _wrap_text(label, w, font_size)
        if lines:
            line_h = font_size * 1.2
            total_h = line_h * len(lines)
            start_y = cy - total_h / 2 + font_size  # baseline of first line
            for i, line in enumerate(lines):
                ly = start_y + i * line_h
                parts.append(
                    f'<text x="{cx:.1f}" y="{ly:.1f}" font-size="{font_size}" '
                    f'font-family="Helvetica, Arial, sans-serif" '
                    f'fill="{font_color}" text-anchor="middle">{_xml_escape(line)}</text>'
                )

    return "\n".join(parts)


def _render_edge(edge: dict, vertices: dict, marker_id: str) -> str:
    src = vertices.get(edge["source"])
    tgt = vertices.get(edge["target"])
    if not src or not tgt:
        return ""
    style = edge["style"]
    stroke = style.get("strokeColor", DEFAULT_STROKE)
    stroke_w = float(style.get("strokeWidth", DEFAULT_STROKE_WIDTH) or 1.0)
    dashed = style.get("dashed") == "1"
    dash_attr = ' stroke-dasharray="4,3"' if dashed else ""

    # Clip both ends to the box edge so the arrowhead lands at the boundary
    sx, sy = _clip_to_box(src["cx"], src["cy"], tgt["cx"], tgt["cy"], src["w"], src["h"])
    tx, ty = _clip_to_box(tgt["cx"], tgt["cy"], src["cx"], src["cy"], tgt["w"], tgt["h"])

    parts = []
    parts.append(
        f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
        f'stroke="{stroke}" stroke-width="{stroke_w:.1f}"{dash_attr} '
        f'marker-end="url(#{marker_id})"/>'
    )

    label = (edge.get("label") or "").strip()
    if label:
        mid_x = (sx + tx) / 2
        mid_y = (sy + ty) / 2 - 4
        font_color = style.get("fontColor", "#000000")
        parts.append(
            f'<text x="{mid_x:.1f}" y="{mid_y:.1f}" font-size="11" '
            f'font-family="Helvetica, Arial, sans-serif" fill="{font_color}" '
            f'text-anchor="middle" '
            f'style="paint-order:stroke;stroke:#ffffff;stroke-width:3px;">'
            f'{_xml_escape(label[:80])}</text>'
        )
    return "\n".join(parts)


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────

def to_svg_pages(xml_path: str, page_id_prefix: str = "p") -> list[tuple[str, str]]:
    """Render each <diagram> page as its own SVG.

    Returns ``[(page_name, svg_string)]``. Empty pages (no vertices, no edges)
    are skipped.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    page_specs = []
    if root.tag == "mxfile":
        for idx, diag in enumerate(root.findall("diagram")):
            page_name = (diag.get("name") or f"page-{idx+1}").strip()
            graph_root = _decode_diagram(diag)
            if graph_root is not None:
                page_specs.append((page_name, graph_root, idx))
    else:
        page_specs.append(("diagram", root, 0))

    results = []
    for page_name, graph_root, idx in page_specs:
        page = _extract_page(graph_root)
        if not page["vertices"] and not page["edges"]:
            continue
        svg = _render_page_svg(page, page_id=f"{page_id_prefix}{idx}")
        results.append((page_name, svg))
    return results


def _render_page_svg(page: dict, page_id: str = "p0") -> str:
    """Build a complete <svg> string for one parsed page."""
    vertices = page["vertices"]
    edges = page["edges"]

    if not vertices:
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 50"><text x="10" y="30">(no nodes)</text></svg>'

    pad = 20
    min_x = min(v["x"] for v in vertices.values())
    min_y = min(v["y"] for v in vertices.values())
    max_x = max(v["x"] + v["w"] for v in vertices.values())
    max_y = max(v["y"] + v["h"] for v in vertices.values())

    vw = max_x - min_x + 2 * pad
    vh = max_y - min_y + 2 * pad
    vb = f"{min_x - pad:.1f} {min_y - pad:.1f} {vw:.1f} {vh:.1f}"

    marker_id = f"arrow-{page_id}"
    marker = (
        f'<defs><marker id="{marker_id}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/>'
        f'</marker></defs>'
    )

    # Render order: edges below vertices so vertex fills cover the line stubs
    edge_svgs = [_render_edge(e, vertices, marker_id) for e in edges]
    # Render swimlanes/big containers BEFORE other vertices so smaller boxes
    # appear on top — sort by area descending
    vlist = sorted(vertices.values(), key=lambda v: -(v["w"] * v["h"]))
    vertex_svgs = [_render_vertex(v) for v in vlist]

    # Background rect drawn inside the SVG (not via CSS) so renderers that
    # ignore CSS — like cairosvg — still get a white canvas + visible border.
    bg = (
        f'<rect x="{min_x - pad:.1f}" y="{min_y - pad:.1f}" '
        f'width="{vw:.1f}" height="{vh:.1f}" '
        f'fill="#ffffff" stroke="#dddddd" stroke-width="1"/>'
    )

    body = "\n".join([marker, bg] + edge_svgs + vertex_svgs)

    # Explicit width/height drive the rendered canvas size in cairosvg / browsers.
    # `class="drawio-page"` lets readers add their own CSS (e.g. max-width:100%)
    # without the inline `height:auto` trap that collapses the canvas in some
    # SVG renderers when an explicit `height` is also present.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
        f'width="{vw:.0f}" height="{vh:.0f}" class="drawio-page">\n'
        f'{body}\n'
        f'</svg>'
    )


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml_path")
    ap.add_argument("--page", help="Print only this page (by name)")
    args = ap.parse_args()

    p = Path(args.xml_path).expanduser()
    if not p.exists():
        sys.exit(f"❌ File not found: {p}")
    if not is_drawio(str(p)):
        sys.exit(f"❌ Not a draw.io export: {p}")

    pages = to_svg_pages(str(p))
    if args.page:
        for name, svg in pages:
            if name == args.page:
                print(svg)
                return
        sys.exit(f"❌ Page not found: {args.page}")

    for name, svg in pages:
        print(f"<!-- ─── {name} ─── -->")
        print(svg)
        print()


if __name__ == "__main__":
    main()
