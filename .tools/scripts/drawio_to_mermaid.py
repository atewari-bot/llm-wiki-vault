#!/usr/bin/env python3
"""
drawio_to_mermaid.py — Convert a draw.io XML export to a Mermaid flowchart block.

Reuses parse_drawio() from parsers.py to extract nodes/edges, then emits a
``mermaid flowchart TD`` block to stdout. The output is intended to be embedded
inside the companion note that `ingest drawio <path>` creates so that Obsidian
can render the diagram inline even when the user doesn't have the draw.io
viewer plugin installed.

Usage:
    python .tools/scripts/drawio_to_mermaid.py path/to/diagram.drawio.xml
    python .tools/scripts/drawio_to_mermaid.py diagram.xml --direction LR

Exit codes:
    0  success
    1  file not found / not a draw.io export
    2  parse failed
"""

import argparse
import re
import sys
from pathlib import Path

# Allow running from anywhere — resolve sibling parsers.py
sys.path.insert(0, str(Path(__file__).parent))

from parsers import parse_drawio, parse_drawio_pages, is_drawio  # noqa: E402


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_]")


def _safe_id(raw_id: str, fallback_idx: int) -> str:
    """Mermaid node ids must be alphanumeric/underscore. Fall back to n<idx>."""
    cleaned = _SAFE_ID_RE.sub("_", raw_id or "")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"n{fallback_idx}_{cleaned}".rstrip("_")
    return cleaned or f"n{fallback_idx}"


def _escape_label(label: str) -> str:
    """Mermaid label inside [..] — strip newlines, escape quotes/brackets."""
    label = (label or "").replace("\n", " ").replace("\r", " ").strip()
    label = label.replace('"', "'").replace("[", "(").replace("]", ")")
    # Mermaid recommends quoting labels with special chars
    return f'"{label[:120]}"' if label else '" "'


def _shape_for(etype: str, label: str) -> tuple[str, str]:
    """Return the (open, close) bracket pair for the node shape."""
    t = (etype or "").lower()
    if t == "question":
        return ("{", "}")        # diamond
    if t == "tool":
        return ("[(", ")]")      # cylinder-ish
    if t == "insight":
        return ("([", "])")      # stadium
    return ("[", "]")            # default rectangle


def _render_one_page(nodes, edges, direction: str = "TD") -> str:
    """Render a single page's nodes/edges as a flowchart body (no fence)."""
    if not nodes and not edges:
        return f"flowchart {direction}\n    %% (empty diagram)\n"

    id_map = {}
    lines = [f"flowchart {direction}"]

    for idx, n in enumerate(nodes):
        sid = _safe_id(n["id"], idx)
        # Avoid collisions when sanitization produces duplicates
        suffix = 0
        original = sid
        while sid in id_map.values():
            suffix += 1
            sid = f"{original}_{suffix}"
        id_map[n["id"]] = sid
        open_b, close_b = _shape_for(n.get("type", ""), n["label"])
        lines.append(f"    {sid}{open_b}{_escape_label(n['label'])}{close_b}")

    for e in edges:
        src = id_map.get(e["source"])
        tgt = id_map.get(e["target"])
        if not src or not tgt:
            continue
        label = (e.get("label") or "").strip()
        if label and label != "relates_to":
            lines.append(f"    {src} -->|{_escape_label(label)}| {tgt}")
        else:
            lines.append(f"    {src} --> {tgt}")

    return "\n".join(lines) + "\n"


def to_mermaid(xml_path: str, direction: str = "TD") -> str:
    """Backward-compatible: render the entire XML as ONE flowchart body.

    Multi-page mxfiles get their pages flattened into a single graph here.
    For per-page rendering — strongly preferred — use :func:`to_mermaid_pages`.
    """
    pages = parse_drawio_pages(xml_path)
    nodes, edges = [], []
    for _name, n, e in pages:
        nodes.extend(n)
        edges.extend(e)
    return _render_one_page(nodes, edges, direction=direction)


def to_mermaid_pages(xml_path: str, direction: str = "TD"):
    """Render each ``<diagram>`` page as its own Mermaid flowchart body.

    Returns a list of ``(page_name, mermaid_body)`` tuples. Pages with zero
    nodes are skipped. The caller is responsible for wrapping each body in a
    ```mermaid fence and a heading.
    """
    out = []
    for page_name, nodes, edges in parse_drawio_pages(xml_path):
        if not nodes and not edges:
            continue
        out.append((page_name, _render_one_page(nodes, edges, direction=direction)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml_path", help="Path to the .drawio or .xml export")
    ap.add_argument("--direction", default="TD",
                    choices=["TD", "TB", "BT", "LR", "RL"],
                    help="Mermaid flowchart direction (default: TD)")
    ap.add_argument("--no-fence", action="store_true",
                    help="Print bare Mermaid (no ```mermaid fence)")
    args = ap.parse_args()

    p = Path(args.xml_path).expanduser()
    if not p.exists():
        print(f"❌ File not found: {p}", file=sys.stderr)
        sys.exit(1)
    if not is_drawio(str(p)):
        print(f"❌ Not a draw.io export (root is not <mxGraphModel>/<mxfile>): {p}", file=sys.stderr)
        sys.exit(1)

    try:
        body = to_mermaid(str(p), direction=args.direction)
    except Exception as ex:
        print(f"❌ Parse failed: {ex}", file=sys.stderr)
        sys.exit(2)

    if args.no_fence:
        sys.stdout.write(body)
    else:
        sys.stdout.write("```mermaid\n")
        sys.stdout.write(body)
        sys.stdout.write("```\n")


if __name__ == "__main__":
    main()
