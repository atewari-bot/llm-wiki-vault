#!/usr/bin/env python3
"""
batch_docker_notes.py — Generate companion notes for all unprocessed Docker diagrams.

Unlike running ingest_drawio.py per-file, this script:
  * Skips re-staging the XMLs (they're already in diagrams/).
  * Skips re-generating SVGs (already created by the batch SVG pass).
  * Calls the Claude API once per diagram for companion-note prose + wiki actions.
  * Writes companion notes with correct ![[...svg]] embed paths pointing to the
    already-existing SVG sidecar files.

Usage (from the vault root, with .venv active):
    python .tools/batch_docker_notes.py
    python .tools/batch_docker_notes.py --dry-run        # print prompts, write nothing
    python .tools/batch_docker_notes.py --chapter 08     # process one chapter only
    python .tools/batch_docker_notes.py --skip-existing  # skip if note already exists

Prerequisites:
    pip install anthropic python-dotenv
    echo "ANTHROPIC_API_KEY=sk-ant-..." > .tools/.env
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from datetime import date
from pathlib import Path

# Load API key from .tools/.env
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
try:
    from parsers import parse_drawio_pages  # type: ignore
except ImportError:
    sys.exit("❌ Cannot import parsers — run from vault root or check .tools/scripts/.")

try:
    import anthropic  # type: ignore
except ImportError:
    sys.exit("❌ `anthropic` not installed. Run: pip install anthropic")

# ─────────────────────────────────────────────────────────────────────────────

MODEL    = "claude-sonnet-4-20250514"
TODAY    = date.today().isoformat()
VAULT    = Path(__file__).parent.parent          # one level up from .tools/
DIAGRAMS = VAULT / "raw/notes/docker/diagrams"
NOTES    = VAULT / "raw/notes/docker"
TOPIC    = "docker"

# Already have companion notes — skip.
ALREADY_DONE = {"01-why-docker", "02-docker-cli"}
# Truly empty diagram — skip.
SKIP_EMPTY   = {"05-empty"}

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    s = SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return s or "untitled"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _shape_hint(style: str) -> str:
    s = (style or "").lower()
    if "ellipse" in s or "circle" in s: return "ellipse"
    if "rhombus" in s or "diamond" in s: return "decision"
    if "cylinder" in s: return "store"
    if "swimlane" in s or "container" in s: return "group"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Diagram parsing (mirrors ingest_drawio.py's build_user_prompt approach)
# ─────────────────────────────────────────────────────────────────────────────

def parse_xml(xml_path: Path) -> list[dict]:
    """Return a list of page dicts: [{name, nodes, edges}]."""
    import xml.etree.ElementTree as ET
    import base64, zlib
    from urllib.parse import unquote

    tree = ET.parse(xml_path)
    root = tree.getroot()

    def _decode(diag):
        inline = diag.find("mxGraphModel")
        if inline is not None:
            return inline
        content = (diag.text or "").strip()
        if not content:
            return None
        try:
            raw = base64.b64decode(content)
            xml_str = zlib.decompress(raw, -zlib.MAX_WBITS).decode("utf-8")
            return ET.fromstring(unquote(xml_str))
        except Exception:
            try:
                return ET.fromstring(unquote(content))
            except Exception:
                return None

    def _cells(graph_root):
        nodes, edges = [], []
        for cell in graph_root.iter("mxCell"):
            cid   = cell.get("id", "")
            value = _strip_html(cell.get("value", ""))
            style = cell.get("style", "")
            if cell.get("edge") == "1":
                src, tgt = cell.get("source", ""), cell.get("target", "")
                if src and tgt:
                    edges.append({"source": src, "target": tgt, "label": value or ""})
            elif cell.get("vertex") == "1" and value and cid not in ("0", "1"):
                nodes.append({"id": cid, "label": value[:200], "style": style})
        return nodes, edges

    if root.tag != "mxfile":
        nodes, edges = _cells(root)
        return [{"name": "diagram", "nodes": nodes, "edges": edges}]

    pages = []
    for idx, diag in enumerate(root.findall("diagram")):
        name = (diag.get("name") or f"page-{idx+1}").strip()
        gr = _decode(diag)
        if gr is None:
            continue
        nodes, edges = _cells(gr)
        pages.append({"name": name, "nodes": nodes, "edges": edges})
    return pages


def build_prompt(title: str, pages: list[dict], existing_wiki: list[str],
                 adjacent_notes: list[tuple[str, str]]) -> str:
    secs = [f"# Diagram: {title}", f"Topic: `{TOPIC}`  ·  Pages: {len(pages)}", ""]
    for i, page in enumerate(pages):
        secs.append(f"## Page {i+1}: {page['name']}")
        if page["nodes"]:
            secs.append("Nodes:")
            for n in page["nodes"]:
                hint = _shape_hint(n.get("style", ""))
                secs.append(f"  - {n['label']}" + (f" [{hint}]" if hint else ""))
        if page["edges"]:
            id_to = {n["id"]: n["label"] for n in page["nodes"]}
            secs.append("Edges:")
            for e in page["edges"]:
                src = id_to.get(e["source"], e["source"])
                tgt = id_to.get(e["target"], e["target"])
                lbl = f" [{e['label']}]" if e.get("label") else ""
                secs.append(f"  - {src} → {tgt}{lbl}")
        secs.append("")

    secs.append("## existing_wiki_pages")
    if existing_wiki:
        secs.append("(`enrich` actions must reference one of these titles exactly.)")
        for t in sorted(existing_wiki):
            secs.append(f"- {t}")
    else:
        secs.append("(none yet)")
    secs.append("")

    if adjacent_notes:
        secs.append(f"## adjacent_topic_notes (raw/notes/{TOPIC}/)")
        for title_, body in adjacent_notes[:5]:
            secs.append(f"### {title_}")
            secs.append(body[:1000])
            secs.append("")

    secs.append("---")
    secs.append("Produce the JSON described in the system prompt. "
                "Be honest and selective. Most entities should be `skip`.")
    return "\n".join(secs)


SYSTEM_PROMPT = """\
You are a knowledge synthesis agent for a personal wiki vault. You are ingesting a single \
draw.io diagram and producing TWO things:

1. A substantive **companion note** that walks the reader through what the diagram \
models — written as real prose, organized by the diagram's structure (its pages, \
its clusters, or its primary data/control flow). The companion note IS the deliverable.

2. A SHORT, GATED list of **wiki-page actions** for entities that genuinely warrant \
a standalone wiki entry. Most diagram entities should NOT get a wiki page. The bar:

   - `create`: only if the entity is a proper reusable concept (not a verb phrase, \
   not a sentence, not a prompt label, not a one-off example) AND you can write \
   ≥250 words of real content. If you cannot, return `skip`.
   - `enrich`: only if an existing wiki page is named in `existing_wiki_pages` AND the \
   diagram contributes something concrete to add.
   - `skip`: the default for most entities.

Hard rules:
- Wikilinks `[[Name]]` in the companion note ONLY when the page already exists or you \
are creating it via a `create` action. Otherwise use **bold**.
- No "Nodes" or "Edges" bullet lists in the companion note. Prose only.
- No frontmatter fields like `node_id` or `cluster: "None"` on wiki pages.
- No `(MOC)` pages.
- The companion note's title should be the diagram's actual title, not a generic one.

Return ONLY valid JSON (no markdown fences, no commentary):

{
  "companion_note_title": "Human-readable title",
  "companion_note_body": "Full markdown body. Starts with `# Title`. \
Includes ## What this models (2-4 sentences). Then ## Walkthrough as prose paragraphs \
(subsections for multi-page diagrams). Optionally ## Key takeaways. Do NOT include \
the Mermaid block, SVG, or frontmatter — those are added by the calling code.",
  "wiki_actions": [
    {
      "action": "create|enrich|skip",
      "title": "Page Title",
      "type": "concept|tool|insight|process|architecture",
      "body": "Full markdown body ≥250 words (create only).",
      "addition": "Markdown section to append (enrich only).",
      "rationale": "One sentence."
    }
  ]
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Wiki context
# ─────────────────────────────────────────────────────────────────────────────

def gather_wiki_titles() -> dict[str, Path]:
    titles = {}
    for sub in ("concepts", "tools"):
        d = VAULT / "wiki" / sub
        if d.exists():
            for p in d.glob("*.md"):
                if not p.name.startswith("."):
                    titles[p.stem] = p
    return titles


def gather_adjacent_notes(exclude_stems: set[str]) -> list[tuple[str, str]]:
    out = []
    if NOTES.exists():
        for p in sorted(NOTES.glob("*.md")):
            if p.name.startswith(".") or p.stem in exclude_stems:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL).strip()
                out.append((p.stem, body[:1200]))
            except Exception:
                pass
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SVG embed builder — uses the already-generated SVG sidecars
# ─────────────────────────────────────────────────────────────────────────────

def build_svg_section(base_stem: str, pages: list[dict]) -> str:
    """Return Obsidian ![[...]] embed markdown for each existing SVG sidecar."""
    parts: list[str] = []
    for page in pages:
        if len(pages) == 1:
            svg_filename = f"{base_stem}.svg"
        else:
            page_slug = slugify(page["name"])
            svg_filename = f"{base_stem}-{page_slug}.svg"
        svg_path = DIAGRAMS / svg_filename
        if not svg_path.exists():
            continue
        vault_rel = svg_path.relative_to(VAULT)
        if len(pages) > 1:
            parts.append(f"### {page['name']}")
            parts.append("")
        parts.append(f"![[{vault_rel}]]")
        parts.append("")
    return "\n".join(parts) + "\n" if parts else "*(no SVG sidecars found)*\n"


def build_mermaid_section(pages: list[dict]) -> str:
    """Simple Mermaid fallback — flat flowchart of nodes/edges per page."""
    SAFE_ID = re.compile(r"[^A-Za-z0-9_]")

    def safe_id(raw, idx):
        c = SAFE_ID.sub("_", raw or "")
        if not c or c[0].isdigit():
            c = f"n{idx}_{c}".rstrip("_")
        return c or f"n{idx}"

    def esc(label):
        label = (label or "").replace("\n", " ").replace('"', "'")
        label = label.replace("[", "(").replace("]", ")")
        return f'"{label[:120]}"' if label else '" "'

    out_parts: list[str] = []
    for page in pages:
        if not page["nodes"] and not page["edges"]:
            continue
        id_map: dict[str, str] = {}
        lines = ["flowchart TD"]
        for idx, n in enumerate(page["nodes"]):
            sid = safe_id(n["id"], idx)
            suf, orig = 0, sid
            while sid in id_map.values():
                suf += 1
                sid = f"{orig}_{suf}"
            id_map[n["id"]] = sid
            lines.append(f"    {sid}[{esc(n['label'])}]")
        for e in page["edges"]:
            s, t = id_map.get(e["source"]), id_map.get(e["target"])
            if s and t:
                lbl = (e.get("label") or "").strip()
                if lbl and lbl != "relates_to":
                    lines.append(f"    {s} -->|{esc(lbl)}| {t}")
                else:
                    lines.append(f"    {s} --> {t}")

        if len(pages) > 1:
            out_parts.append(f"### {page['name']}")
            out_parts.append("")
        out_parts.append(f"```mermaid\n" + "\n".join(lines) + "\n```")
        out_parts.append("")

    return "\n".join(out_parts) + "\n" if out_parts else "*(empty diagram)*\n"


# ─────────────────────────────────────────────────────────────────────────────
# Claude call
# ─────────────────────────────────────────────────────────────────────────────

def call_claude(title: str, pages: list[dict],
                wiki_titles: dict, adjacent: list) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("❌ ANTHROPIC_API_KEY not set — add it to .tools/.env")
    client = anthropic.Anthropic()
    user_msg = build_prompt(title, pages, list(wiki_titles.keys()), adjacent)
    print(f"   🧠 {MODEL} ({len(user_msg):,} chars)…", flush=True)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = resp.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            print(f"   ⚠️  Claude returned non-JSON — skipping wiki actions")
            return {"companion_note_body": raw, "wiki_actions": []}
        data = json.loads(m.group(0))

    actions = data.get("wiki_actions", [])
    cnts = {k: sum(1 for a in actions if a.get("action") == k) for k in ("create", "enrich", "skip")}
    print(f"   Actions: {cnts['create']} create / {cnts['enrich']} enrich / {cnts['skip']} skip")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Wiki action application (mirrors ingest_drawio.py)
# ─────────────────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "-", name).strip()[:80]


def _wiki_page(title: str, etype: str, body: str, note_stem: str) -> str:
    if not body.lstrip().startswith("# "):
        body = f"# {title}\n\n{body}"
    fm = [
        "---",
        f'title: "{title}"',
        f"type: {etype}",
        f"tags: [{etype}]",
        f"created: {TODAY}",
        f"updated: {TODAY}",
        f'sources: ["[[raw/notes/{TOPIC}/{note_stem}]]"]',
        "confidence: medium",
        "---",
        "",
    ]
    return "\n".join(fm) + body.rstrip() + "\n"


def apply_wiki_actions(data: dict, wiki_titles: dict, note_stem: str,
                       diagram_title: str) -> set[str]:
    applied: set[str] = set()
    for a in data.get("wiki_actions", []):
        action = a.get("action")
        title  = (a.get("title") or "").strip()
        if not title:
            continue

        if action == "create":
            body = (a.get("body") or "").strip()
            if len(body.split()) < 200:
                print(f"   ⚠️  skip create '{title}' — under 200 words")
                continue
            etype = (a.get("type") or "concept").lower()
            sub   = "tools" if etype == "tool" else "concepts"
            target = VAULT / "wiki" / sub / f"{_safe_filename(title)}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                # Treat as enrich instead
                existing = target.read_text(encoding="utf-8", errors="ignore")
                section  = (
                    f"\n\n## Seen in: {diagram_title}\n\n"
                    f"*Source: [[raw/notes/{TOPIC}/{note_stem}]]*\n\n"
                    f"{body[:600].strip()}\n"
                )
                new_text = re.sub(r"^updated:\s*\d{4}-\d{2}-\d{2}",
                                  f"updated: {TODAY}", existing, count=1, flags=re.MULTILINE)
                if section.strip() not in new_text:
                    target.write_text(new_text.rstrip() + section, encoding="utf-8")
                applied.add(title)
                print(f"   ✏️  enriched (existed) → wiki/{sub}/{target.name}")
            else:
                target.write_text(_wiki_page(title, etype, body, note_stem), encoding="utf-8")
                applied.add(title)
                wiki_titles[title] = target  # register for subsequent diagrams
                print(f"   📄 created → wiki/{sub}/{target.name}")

        elif action == "enrich":
            target = wiki_titles.get(title)
            if not target:
                print(f"   ⚠️  skip enrich '{title}' — no matching wiki page")
                continue
            addition = (a.get("addition") or "").strip()
            if not addition:
                continue
            existing = target.read_text(encoding="utf-8", errors="ignore")
            section  = (
                f"\n\n## Seen in: {diagram_title}\n\n"
                f"*Source: [[raw/notes/{TOPIC}/{note_stem}]]*\n\n"
                f"{addition.strip()}\n"
            )
            new_text = re.sub(r"^updated:\s*\d{4}-\d{2}-\d{2}",
                              f"updated: {TODAY}", existing, count=1, flags=re.MULTILINE)
            if section.strip() not in new_text:
                target.write_text(new_text.rstrip() + section, encoding="utf-8")
            applied.add(title)
            print(f"   ✏️  enriched → {target.relative_to(VAULT)}")

    return applied


# ─────────────────────────────────────────────────────────────────────────────
# Companion note writer
# ─────────────────────────────────────────────────────────────────────────────

def write_note(note_path: Path, data: dict, title: str,
               base_stem: str, pages: list[dict], applied: set[str],
               xml_name: str) -> None:
    body = (data.get("companion_note_body") or "").strip()
    if not body:
        body = f"# {title}\n\n(Claude returned an empty body.)"
    if not body.lstrip().startswith("# "):
        body = f"# {title}\n\n{body}"

    linked = sorted(applied)
    lines: list[str] = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f'source_file: "[[raw/notes/{TOPIC}/diagrams/{xml_name}]]"')
    lines.append(f"fetched: {TODAY}")
    lines.append(f"tags: [raw, diagram, drawio, {TOPIC}]")
    lines.append(f"diagram_pages: {len(pages)}")
    if linked:
        lines.append("linked_wiki_pages:")
        for t in linked:
            lines.append(f'  - "[[{t}]]"')
    lines.append("status: processed")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    lines.append("## Diagram")
    lines.append("")
    lines.append(build_svg_section(base_stem, pages))
    lines.append("<details>")
    lines.append("<summary>Mermaid (text fallback)</summary>")
    lines.append("")
    lines.append(build_mermaid_section(pages))
    lines.append("</details>")
    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append("<details>")
    lines.append("<summary>Raw draw.io XML</summary>")
    lines.append("")
    lines.append("```xml")
    xml_path = DIAGRAMS / xml_name
    lines.append(xml_path.read_text(encoding="utf-8", errors="ignore").rstrip())
    lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    note_path.write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def _human_title(base_stem: str) -> str:
    """03-building-images → 'Building Images (Ch. 3)'"""
    m = re.match(r"^(\d+)[-_](.*)", base_stem)
    if m:
        ch  = int(m.group(1))
        rest = m.group(2).replace("-", " ").replace("_", " ")
        return f"{rest.title()} (Ch. {ch})"
    return base_stem.replace("-", " ").title()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the Claude prompt for each diagram; write nothing.")
    ap.add_argument("--chapter", metavar="NN",
                    help="Process only this chapter number (e.g. '08').")
    ap.add_argument("--skip-existing", action="store_true",
                    help="Skip diagrams whose companion note already exists.")
    args = ap.parse_args()

    xmls = sorted(DIAGRAMS.glob("*.drawio.xml"))
    if args.chapter:
        xmls = [x for x in xmls if x.name.startswith(args.chapter)]
        if not xmls:
            sys.exit(f"❌ No diagram found for chapter '{args.chapter}'")

    wiki_titles = gather_wiki_titles()
    print(f"📚 {len(wiki_titles)} existing wiki pages loaded\n")

    total_notes, total_wiki = 0, 0

    for xml_path in xmls:
        # base_stem: "03-building-images.drawio" → "03-building-images"
        stem = xml_path.stem
        base_stem = stem[: -len(".drawio")] if stem.endswith(".drawio") else stem

        # Skip rules
        if base_stem in ALREADY_DONE or base_stem in SKIP_EMPTY:
            print(f"⏭️  {xml_path.name} — skipped (already done / empty)")
            continue

        note_path = NOTES / f"{base_stem}-diagram.md"
        if args.skip_existing and note_path.exists():
            print(f"⏭️  {xml_path.name} — companion note exists, skipping")
            continue

        title = _human_title(base_stem)
        print(f"\n📐 {xml_path.name}  →  \"{title}\"", flush=True)

        pages = parse_xml(xml_path)
        n_nodes = sum(len(p["nodes"]) for p in pages)
        n_edges = sum(len(p["edges"]) for p in pages)
        print(f"   {len(pages)} page(s), {n_nodes} nodes, {n_edges} edges")

        adjacent = gather_adjacent_notes(exclude_stems={note_path.stem})

        if args.dry_run:
            prompt = build_prompt(title, pages, list(wiki_titles.keys()), adjacent)
            print("─" * 60)
            print(prompt[:3000])
            if len(prompt) > 3000:
                print(f"… ({len(prompt):,} total chars)")
            print("─" * 60)
            continue

        data    = call_claude(title, pages, wiki_titles, adjacent)
        applied = apply_wiki_actions(data, wiki_titles, note_path.stem, title)
        write_note(note_path, data, title, base_stem, pages, applied, xml_path.name)

        total_notes += 1
        total_wiki  += len(applied)
        print(f"   📝 {note_path.relative_to(VAULT)}")

    if not args.dry_run:
        print(f"\n✅ Done — {total_notes} companion note(s), {total_wiki} wiki page(s) created/enriched")


if __name__ == "__main__":
    main()
