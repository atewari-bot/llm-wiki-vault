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
    Skips wiki/, reports/, tools/ — only reads source material.

    subfolders: optional list like ['inbox', 'articles'] to narrow further.
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
    skip_dirs = {"wiki", "reports", "tools", ".claude", ".obsidian"}

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
        "pink": "person", "red": "question", "purple": "process",
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
        return tree.getroot().tag == "mxGraphModel" or any(
            True for _ in ET.parse(xml_path).getroot().iter("mxGraphModel")
        )
    except Exception:
        return False


def parse_drawio(xml_path: str) -> tuple[list[dict], list[dict]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    graph_roots = []
    if root.tag == "mxfile":
        for diagram in root.findall("diagram"):
            content = diagram.text or ""
            try:
                decoded = base64.b64decode(content)
                xml_str = zlib.decompress(decoded, -zlib.MAX_WBITS).decode("utf-8")
                graph_roots.append(ET.fromstring(unquote(xml_str)))
            except Exception:
                try:
                    graph_roots.append(ET.fromstring(unquote(content)))
                except Exception:
                    pass
    else:
        graph_roots.append(root)

    nodes, edges = [], []
    for gr in graph_roots:
        for cell in gr.iter("mxCell"):
            cid = cell.get("id", "")
            value = _clean_html(cell.get("value", ""))
            style = cell.get("style", "")
            edge = cell.get("edge") == "1"
            vertex = cell.get("vertex") == "1"
            if edge:
                src = cell.get("source", "")
                tgt = cell.get("target", "")
                if src and tgt:
                    edges.append({"source": src, "target": tgt, "label": value or "relates_to"})
            elif vertex and value and cid not in ("0", "1"):
                etype = _drawio_style_to_type(style)
                nodes.append({"id": cid, "label": value[:200], "type": etype, "source": "drawio"})
    return nodes, edges


def _drawio_style_to_type(style: str) -> str:
    s = style.lower()
    if "ellipse" in s or "circle" in s: return "concept"
    if "rhombus" in s or "diamond" in s: return "question"
    if "cylinder" in s: return "tool"
    if "person" in s or "actor" in s: return "person"
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
    return re.sub(r"<[^>]+>", "", text or "").strip()
