#!/usr/bin/env python3
"""
ingest_drawio.py — Ingest a draw.io diagram into the LLM Wiki vault.

Design contract (the *one* invariant of this tool):
    One .xml = one substantive companion note.
    Wiki pages are a selective, gated output — not a per-node fanout.

The previous flow (knowledge_graph_builder.py --drawio) created one wiki page
per mxCell vertex, populated with a 1-2 sentence "description" field and a
list of relationship rationales. That produces 15-20 thin orphan pages from
a single diagram with no real content.

This tool replaces that flow:

  1. Stage the .xml under raw/notes/<topic>/diagrams/
  2. Parse all <diagram> pages and gather context from existing wiki pages
     and adjacent raw/notes/<topic>/ files
  3. Send a SINGLE Claude call with the full diagram + context, asking for:
       - a substantive companion-note body (real prose, organized as a
         walkthrough — not bullet lists of node labels)
       - a SHORT list of wiki-page actions, each one of:
           create  — a genuinely reusable concept that doesn't exist yet,
                     with ≥250 words of real content
           enrich  — append a "Seen in <diagram>" section to an existing page
                     with concrete additions (not a generic relates_to list)
           skip    — most diagram entities. They live as bold terms in the
                     companion note prose and never become standalone pages.
  4. Write the companion note (frontmatter + AI prose + Mermaid + collapsed XML)
  5. Apply the wiki-page actions

Usage:
    python .tools/ingest_drawio.py <path/to/diagram.drawio>
    python .tools/ingest_drawio.py <path> --topic auth-flow
    python .tools/ingest_drawio.py <path> --dry-run
    python .tools/ingest_drawio.py <path> --vault /path/to/llm-wiki-vault
    python .tools/ingest_drawio.py <path> --no-svg   # Mermaid-only (no SVG sidecar)

Run from the vault root, or pass --vault.

SVG output (default on):
    Each diagram page is rendered as a standalone .svg file saved alongside the
    staged XML in raw/notes/<topic>/diagrams/ and embedded in the companion note
    via Obsidian's ![[path/to/file.svg]] syntax.  SVG preserves the exact spatial
    layout (x/y, nesting, swimlanes) that Mermaid's auto-layout discards.  A
    Mermaid block is kept inside a collapsed <details> for text-search fallback.
    Pass --no-svg to skip SVG and embed Mermaid only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

# Load .tools/.env (ANTHROPIC_API_KEY)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass  # dotenv is optional; user might have ANTHROPIC_API_KEY exported

# Reuse the existing parser
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from parsers import parse_drawio, is_drawio  # noqa: E402

try:
    import anthropic  # type: ignore
except ImportError:  # pragma: no cover
    print("❌ The `anthropic` package is required. `pip install anthropic`", file=sys.stderr)
    sys.exit(1)


MODEL = "claude-sonnet-4-20250514"
TODAY = date.today().isoformat()
SLUG_RE = re.compile(r"[^a-z0-9]+")


# ────────────────────────────────────────────────────────────────────────────
# Data structures
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class DiagramPage:
    """One <diagram> page from an mxfile."""
    page_index: int
    page_name: str
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)


@dataclass
class IngestPlan:
    source_xml: Path        # the user's input
    vault: Path
    topic: str              # kebab-case slug — folder under raw/notes/
    slug: str               # kebab-case slug — for the diagram filename
    title: str              # human-readable title
    staged_xml: Path        # raw/notes/<topic>/diagrams/<date>-<slug>.drawio.xml
    companion_note: Path    # raw/notes/<topic>/<date>-<slug>-diagram.md
    pages: list[DiagramPage]
    raw_xml_text: str       # full source content
    use_svg: bool = True    # render SVG sidecars (default on); False → Mermaid only


@dataclass
class WikiContext:
    """What we know about the wiki + adjacent notes when prompting Claude."""
    existing_titles: dict[str, Path] = field(default_factory=dict)  # title -> path
    topic_notes: list[tuple[str, str]] = field(default_factory=list)  # (title, body)


# ────────────────────────────────────────────────────────────────────────────
# Step 1: validate + resolve topic/slug + stage
# ────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    s = SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return s or "untitled"


def _clean_filename_stem(stem: str) -> str:
    """Strip a leading YYYY-MM-DD- date and a trailing .drawio if present."""
    s = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]", "", stem)
    s = re.sub(r"\.drawio$", "", s, flags=re.IGNORECASE)
    s = s.replace("_", " ").replace("-", " ").strip()
    # Title-case unless it already has uppercase mid-word (e.g. "OAuth")
    if s and s == s.lower():
        s = " ".join(w.capitalize() for w in s.split())
    return s


def resolve_title_from_xml(xml_path: Path, raw_text: str) -> str:
    """Best-effort title resolution. Order:
        1. <mxfile name="..."> — explicit, user-set
        2. Filename stem (date prefix stripped) — user chose this deliberately
        3. First <diagram name="..."> stripped of "01 - " ordering prefix
        4. xml_path.stem as last resort
    A multi-page tutorial deck typically has per-page names like "01 - images"
    which are meaningless as a document title, so we prefer the filename stem.
    """
    m = re.search(r'<mxfile[^>]*\sname="([^"]+)"', raw_text)
    if m and m.group(1).strip():
        return m.group(1).strip()

    fn = _clean_filename_stem(xml_path.stem)
    if fn:
        return fn

    m = re.search(r'<diagram[^>]*\sname="([^"]+)"', raw_text)
    if m and m.group(1).strip():
        return re.sub(r"^\s*\d+\s*[-_.\s]+", "", m.group(1).strip())

    return xml_path.stem


def parse_pages(xml_path: Path) -> list[DiagramPage]:
    """Extract every <diagram> page individually so we can preserve structure.

    parse_drawio() already flattens all pages into one nodes/edges list; here
    we inspect the raw XML so we can attach a per-page index and name.
    """
    import xml.etree.ElementTree as ET
    import base64
    import zlib
    from urllib.parse import unquote

    tree = ET.parse(xml_path)
    root = tree.getroot()

    pages: list[DiagramPage] = []

    if root.tag != "mxfile":
        # Single-page mxGraphModel
        nodes, edges = parse_drawio(str(xml_path))
        pages.append(DiagramPage(page_index=0, page_name="diagram", nodes=nodes, edges=edges))
        return pages

    for idx, diag in enumerate(root.findall("diagram")):
        page_name = (diag.get("name") or f"page-{idx+1}").strip()

        # draw.io stores diagram content in one of three forms:
        #   (a) inline <mxGraphModel> child (uncompressed XML — common for hand-edited files)
        #   (b) base64+deflate-compressed text body (standard export from app.diagrams.net)
        #   (c) URL-encoded raw XML in the text body (rare, older saves)
        graph_root = None
        inline_model = diag.find("mxGraphModel")
        if inline_model is not None:
            graph_root = inline_model
        else:
            content = (diag.text or "").strip()
            if content:
                try:
                    decoded = base64.b64decode(content)
                    xml_str = zlib.decompress(decoded, -zlib.MAX_WBITS).decode("utf-8")
                    graph_root = ET.fromstring(unquote(xml_str))
                except Exception:
                    try:
                        graph_root = ET.fromstring(unquote(content))
                    except Exception:
                        graph_root = None

        nodes: list[dict] = []
        edges: list[dict] = []
        if graph_root is not None:
            for cell in graph_root.iter("mxCell"):
                cid = cell.get("id", "")
                value = _strip_html(cell.get("value", ""))
                style = cell.get("style", "")
                if cell.get("edge") == "1":
                    src, tgt = cell.get("source", ""), cell.get("target", "")
                    if src and tgt:
                        edges.append({"source": src, "target": tgt, "label": value or ""})
                elif cell.get("vertex") == "1" and value and cid not in ("0", "1"):
                    nodes.append({"id": cid, "label": value[:200], "style": style})

        pages.append(DiagramPage(page_index=idx, page_name=page_name, nodes=nodes, edges=edges))

    return pages


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def build_plan(args: argparse.Namespace) -> IngestPlan:
    src = Path(args.path).expanduser().resolve()
    if not src.exists():
        sys.exit(f"❌ File not found: {src}")
    if not is_drawio(str(src)):
        sys.exit(f"❌ Not a draw.io export (root must be <mxfile>/<mxGraphModel>): {src}")

    raw_text = src.read_text(encoding="utf-8", errors="ignore")
    title = resolve_title_from_xml(src, raw_text)
    slug = slugify(args.slug or title)

    # Resolve topic
    if args.topic:
        topic = slugify(args.topic)
    else:
        # If filename has a clear topic prefix, use that; else fall back to slug
        topic = slugify(src.stem.split("_")[0]) if "_" in src.stem else slug
        if topic == slug:
            # Last resort: ask the user
            topic = slugify(input(f"Topic slug for this diagram [{slug}]: ").strip() or slug)

    vault = Path(args.vault).expanduser().resolve() if args.vault else Path.cwd().resolve()
    if not (vault / "raw").exists() or not (vault / "wiki").exists():
        sys.exit(f"❌ {vault} doesn't look like a vault (no raw/ or wiki/). Pass --vault.")

    diagrams_dir = vault / "raw" / "notes" / topic / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    # --no-date drops the YYYY-MM-DD prefix from staged xml + companion note.
    date_prefix = "" if args.no_date else f"{TODAY}-"

    staged_name = f"{date_prefix}{slug}.drawio.xml"
    staged_xml = diagrams_dir / staged_name
    # Don't silently overwrite a previously staged copy
    n = 2
    while staged_xml.exists():
        staged_xml = diagrams_dir / f"{date_prefix}{slug}-{n}.drawio.xml"
        n += 1

    companion_note = vault / "raw" / "notes" / topic / f"{date_prefix}{slug}-diagram.md"
    n = 2
    while companion_note.exists():
        companion_note = vault / "raw" / "notes" / topic / f"{date_prefix}{slug}-{n}-diagram.md"
        n += 1

    pages = parse_pages(src)
    n_nodes = sum(len(p.nodes) for p in pages)
    n_edges = sum(len(p.edges) for p in pages)
    print(f"📐 {src.name}: {len(pages)} page(s), {n_nodes} nodes, {n_edges} edges")

    return IngestPlan(
        source_xml=src,
        vault=vault,
        topic=topic,
        slug=slug,
        title=title,
        staged_xml=staged_xml,
        companion_note=companion_note,
        pages=pages,
        raw_xml_text=raw_text,
        use_svg=not getattr(args, "no_svg", False),
    )


# ────────────────────────────────────────────────────────────────────────────
# Step 2: gather wiki + topic context
# ────────────────────────────────────────────────────────────────────────────

def gather_context(plan: IngestPlan) -> WikiContext:
    ctx = WikiContext()
    wiki = plan.vault / "wiki"
    for sub in ("concepts", "tools"):
        d = wiki / sub
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            if p.name.startswith("."):
                continue
            ctx.existing_titles[p.stem] = p

    topic_dir = plan.vault / "raw" / "notes" / plan.topic
    if topic_dir.exists():
        for p in sorted(topic_dir.glob("*.md")):
            if p.name.startswith(".") or p == plan.companion_note:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                # Strip frontmatter for prompt budget
                body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL).strip()
                ctx.topic_notes.append((p.stem, body[:1500]))
            except Exception:
                pass

    print(f"📚 Context: {len(ctx.existing_titles)} wiki pages, "
          f"{len(ctx.topic_notes)} adjacent topic note(s)")
    return ctx


# ────────────────────────────────────────────────────────────────────────────
# Step 3: build the prompt + call Claude
# ────────────────────────────────────────────────────────────────────────────

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
   ≥250 words of real content combining your training knowledge of the public concept, \
   the diagram's specific take, and adjacent topic notes. If you cannot write substantive \
   content beyond restating the label, return `skip`.
   - `enrich`: only if an existing wiki page is named in `existing_wiki_pages` AND the \
   diagram contributes something concrete to add (a mechanism, a caveat, a new \
   relationship). The enrichment must be specific — not a generic "this diagram \
   relates to X" sentence.
   - `skip`: the default. Pedagogical labels, scratch text, sentence-shaped nodes, \
   one-off examples, callouts, and most diagram entities go here. They live as **bold \
   terms** in the companion note's prose, never as standalone pages.

Hard rules:
- Wikilinks `[[Name]]` in the companion note ONLY when (a) the page already exists \
or (b) you are about to create it via a `create` action. Otherwise use **bold**.
- No "Nodes" or "Edges" bullet lists in the companion note. The prose IS the structure.
- No frontmatter fields like `node_id` or `cluster: "None"` on wiki pages.
- No `(MOC)` pages.
- No relationship lists that just restate edges as `relates_to` with vacuous rationales.
- The companion note's title should be the diagram's actual title, not a generic one.
- Be honest about the diagram's scope. If it's a 16-page tutorial deck, say so. If it's \
a single architecture sketch, say so.

Return ONLY valid JSON (no markdown fences, no commentary):

{
  "companion_note_title": "Human-readable title",
  "companion_note_body": "Full markdown body for the companion note. Starts with `# Title`.\
 Includes ## What this models (2-4 sentences). Then a ## Walkthrough section organized as \
prose paragraphs (with subsections for multi-page diagrams). Optionally ## Key takeaways. \
Optionally ## Entities not given wiki pages — a brief explanation of which diagram \
entities you skipped and why. Do NOT include the Mermaid block, the source XML, or \
frontmatter — those are added by the calling code.",
  "wiki_actions": [
    {
      "action": "create",
      "title": "Concept Name",
      "type": "concept|tool|insight|process|architecture",
      "body": "Full markdown body, ≥250 words. Real content. Starts with a definition \
paragraph, then sections like ## How it works, ## In this diagram, ## See Also. \
Use [[wikilinks]] only to existing pages or to other entries you are creating.",
      "rationale": "One sentence: why this passes the bar."
    },
    {
      "action": "enrich",
      "title": "Existing Page Title (must match an entry in existing_wiki_pages)",
      "addition": "Markdown to append to the existing page. Should be a section starting \
with `## Seen in: <Diagram Title>` followed by 2-4 sentences of CONCRETE additions \
the diagram contributes. Not a generic 'relates to' list.",
      "rationale": "One sentence: what concrete thing this adds."
    },
    {
      "action": "skip",
      "title": "Diagram Entity Label",
      "rationale": "One sentence: why this doesn't merit a page (e.g. 'pedagogical \
callout', 'one-off example', 'covered in companion note prose')."
    }
  ]
}
"""


def build_user_prompt(plan: IngestPlan, ctx: WikiContext) -> str:
    sections: list[str] = []
    sections.append(f"# Diagram: {plan.title}")
    sections.append(f"Topic: `{plan.topic}`  ·  Pages: {len(plan.pages)}")
    sections.append("")

    for page in plan.pages:
        sections.append(f"## Page {page.page_index + 1}: {page.page_name}")
        if page.nodes:
            sections.append("Nodes:")
            for n in page.nodes:
                shape = _shape_hint(n.get("style", ""))
                shape_tag = f" [{shape}]" if shape else ""
                sections.append(f"  - {n['label']}{shape_tag}")
        if page.edges:
            id_to_label = {n["id"]: n["label"] for n in page.nodes}
            sections.append("Edges:")
            for e in page.edges:
                src = id_to_label.get(e["source"], e["source"])
                tgt = id_to_label.get(e["target"], e["target"])
                lbl = f" [{e['label']}]" if e.get("label") else ""
                sections.append(f"  - {src} → {tgt}{lbl}")
        sections.append("")

    sections.append("## existing_wiki_pages")
    if ctx.existing_titles:
        sections.append("(`enrich` actions must reference one of these titles exactly.)")
        for title in sorted(ctx.existing_titles):
            sections.append(f"- {title}")
    else:
        sections.append("(none yet)")
    sections.append("")

    if ctx.topic_notes:
        sections.append(f"## adjacent_topic_notes (raw/notes/{plan.topic}/)")
        for title, body in ctx.topic_notes[:6]:
            sections.append(f"### {title}")
            sections.append(body[:1200])
            sections.append("")

    sections.append("---")
    sections.append("Produce the JSON described in the system prompt. "
                    "Be honest and selective. Most entities should be `skip`.")
    return "\n".join(sections)


def _shape_hint(style: str) -> str:
    s = (style or "").lower()
    if "ellipse" in s or "circle" in s:
        return "ellipse"
    if "rhombus" in s or "diamond" in s:
        return "decision"
    if "cylinder" in s:
        return "store"
    if "swimlane" in s or "container" in s:
        return "group"
    return ""


def call_claude(plan: IngestPlan, ctx: WikiContext) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("❌ ANTHROPIC_API_KEY not set. Add it to .tools/.env.")

    client = anthropic.Anthropic()
    user_msg = build_user_prompt(plan, ctx)

    print(f"🧠 Calling {MODEL} ({len(user_msg):,} chars of prompt)...")
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
    except json.JSONDecodeError as e:
        # Try to recover by finding the outermost JSON object
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            sys.exit(f"❌ Claude returned non-JSON output: {e}\n{raw[:500]}")
        data = json.loads(m.group(0))

    actions = data.get("wiki_actions", [])
    counts = {"create": 0, "enrich": 0, "skip": 0}
    for a in actions:
        counts[a.get("action", "skip")] = counts.get(a.get("action", "skip"), 0) + 1
    print(f"   Actions: {counts.get('create', 0)} create / "
          f"{counts.get('enrich', 0)} enrich / {counts.get('skip', 0)} skip")
    return data


# ────────────────────────────────────────────────────────────────────────────
# Step 4: write outputs
# ────────────────────────────────────────────────────────────────────────────

def stage_xml(plan: IngestPlan):
    shutil.copyfile(plan.source_xml, plan.staged_xml)
    print(f"📂 Staged → {plan.staged_xml.relative_to(plan.vault)}")


def render_mermaid(plan: IngestPlan) -> str:
    """Render each <diagram> page as its own Mermaid block under an H3 heading.

    Multi-page mxfiles produce multiple readable diagrams instead of one
    merged box-soup. Falls back to a stub on parse error.
    """
    try:
        sys.path.insert(0, str(plan.vault / ".tools" / "scripts"))
        from drawio_to_mermaid import to_mermaid_pages  # type: ignore
        pages = to_mermaid_pages(str(plan.staged_xml))
    except Exception as e:
        return f"<!-- Mermaid conversion failed: {e} -->\n"

    if not pages:
        return "*(diagram has no parseable nodes or edges)*\n"

    # Single-page mxfiles: one block, no per-page heading needed
    if len(pages) == 1:
        _, body = pages[0]
        return f"```mermaid\n{body}```\n"

    parts = []
    for page_name, body in pages:
        parts.append(f"### {page_name}")
        parts.append("")
        parts.append(f"```mermaid\n{body}```")
        parts.append("")
    return "\n".join(parts) + "\n"


def render_svg(plan: IngestPlan) -> str:
    """Render each diagram page as a standalone .svg sidecar file and return
    Obsidian embed markdown (![[path/to/file.svg]]) for each page.

    SVG is saved alongside the staged XML in raw/notes/<topic>/diagrams/ so
    Obsidian can resolve the embed natively.  The key advantage over Mermaid:
    SVG preserves the original x/y coordinates, nested swimlane containers,
    and per-cell styling that Mermaid's auto-layout collapses into a flat graph.
    """
    try:
        sys.path.insert(0, str(plan.vault / ".tools" / "scripts"))
        from drawio_to_svg import to_svg_pages  # type: ignore
        pages = to_svg_pages(str(plan.staged_xml))
    except Exception as e:
        return f"<!-- SVG conversion failed: {e} -->\n"

    if not pages:
        return "*(diagram has no renderable content)*\n"

    diagrams_dir = plan.staged_xml.parent

    # staged_xml stem looks like "2026-05-03-my-slug.drawio" (ET strips ".xml").
    # Strip the trailing ".drawio" so SVG filenames are "2026-05-03-my-slug.svg".
    base_stem = plan.staged_xml.stem
    if base_stem.endswith(".drawio"):
        base_stem = base_stem[: -len(".drawio")]

    parts: list[str] = []
    saved: list[Path] = []
    for page_name, svg_string in pages:
        if len(pages) == 1:
            svg_filename = f"{base_stem}.svg"
        else:
            svg_filename = f"{base_stem}-{slugify(page_name)}.svg"

        svg_path = diagrams_dir / svg_filename
        svg_path.write_text(svg_string, encoding="utf-8")
        saved.append(svg_path)

        # Obsidian resolves ![[vault-relative-path]] from the vault root.
        vault_rel = svg_path.relative_to(plan.vault)

        if len(pages) > 1:
            parts.append(f"### {page_name}")
            parts.append("")
        parts.append(f"![[{vault_rel}]]")
        parts.append("")

    print(f"   🖼️  SVG: {len(saved)} file(s) → "
          f"raw/notes/{plan.topic}/diagrams/")
    return "\n".join(parts) + "\n"


def write_companion_note(plan: IngestPlan, ai_data: dict, applied_titles: set[str]) -> str:
    body = (ai_data.get("companion_note_body") or "").strip()
    if not body:
        body = f"# {plan.title}\n\n(Claude returned an empty body.)"

    # Ensure body starts with an H1 — if not, prepend the title
    if not body.lstrip().startswith("# "):
        body = f"# {plan.title}\n\n{body}"

    # Linked-wiki frontmatter reflects only ACTUALLY-APPLIED actions, so it
    # never points to a page that wasn't created or enriched.
    linked_titles = sorted(applied_titles)

    lines: list[str] = ["---"]
    lines.append(f'title: "{plan.title}"')
    lines.append(f'source_file: "[[raw/notes/{plan.topic}/diagrams/{plan.staged_xml.name}]]"')
    lines.append(f"fetched: {TODAY}")
    lines.append(f"tags: [raw, diagram, drawio, {plan.topic}]")
    lines.append(f"diagram_pages: {len(plan.pages)}")
    if linked_titles:
        lines.append("linked_wiki_pages:")
        for t in linked_titles:
            lines.append(f'  - "[[{t}]]"')
    lines.append("status: processed")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    lines.append("## Diagram")
    lines.append("")
    if plan.use_svg:
        lines.append(render_svg(plan))
        lines.append("<details>")
        lines.append("<summary>Mermaid (text fallback)</summary>")
        lines.append("")
        lines.append(render_mermaid(plan))
        lines.append("</details>")
        lines.append("")
    else:
        lines.append(render_mermaid(plan))
    lines.append("## Source")
    lines.append("")
    lines.append("<details>")
    lines.append("<summary>Raw draw.io XML</summary>")
    lines.append("")
    lines.append("```xml")
    lines.append(plan.raw_xml_text.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    out = "\n".join(lines)
    plan.companion_note.write_text(out, encoding="utf-8")
    return out


def apply_wiki_actions(plan: IngestPlan, ai_data: dict, ctx: WikiContext) -> tuple[int, int, set[str]]:
    """Returns (created_count, enriched_count, applied_titles).

    `applied_titles` is the set of wiki page titles that were actually written
    or enriched — i.e., proposals that passed every gate. This is what the
    companion note's `linked_wiki_pages` frontmatter should reference.
    """
    actions = ai_data.get("wiki_actions", [])
    created, enriched = 0, 0
    applied: set[str] = set()

    for a in actions:
        action = a.get("action")
        title = (a.get("title") or "").strip()
        if not title:
            continue

        if action == "create":
            body = (a.get("body") or "").strip()
            if len(body.split()) < 200:
                # Enforce the bar at the post-processing stage too
                print(f"   ⚠️  Skipping create '{title}' — body under 200 words "
                      "(failed wiki-worthiness gate).")
                continue
            etype = (a.get("type") or "concept").lower()
            subfolder = "tools" if etype == "tool" else "concepts"
            target = plan.vault / "wiki" / subfolder / f"{_safe_filename(title)}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                # Don't clobber. Treat as enrichment instead.
                _append_seen_in(target, plan, body[:600])
                enriched += 1
                applied.add(title)
                print(f"   ✏️  enriched (existed) → {target.relative_to(plan.vault)}")
                continue

            page = _wiki_page(title=title, etype=etype, body=body, plan=plan)
            target.write_text(page, encoding="utf-8")
            created += 1
            applied.add(title)
            print(f"   📄 created → {target.relative_to(plan.vault)}")

        elif action == "enrich":
            target = ctx.existing_titles.get(title)
            if not target:
                # Title didn't match anything — skip rather than create a stub
                print(f"   ⚠️  Skipping enrich '{title}' — no existing wiki page with that title.")
                continue
            addition = (a.get("addition") or "").strip()
            if not addition:
                continue
            _append_seen_in(target, plan, addition)
            enriched += 1
            applied.add(title)
            print(f"   ✏️  enriched → {target.relative_to(plan.vault)}")

        else:  # skip
            continue

    return created, enriched, applied


def _wiki_page(*, title: str, etype: str, body: str, plan: IngestPlan) -> str:
    body = (body or "").strip()
    # Ensure the body has an H1 — Claude sometimes opens with a definition
    # paragraph instead. Don't double-stack if the body already starts with H1.
    if not body.lstrip().startswith("# "):
        body = f"# {title}\n\n{body}"
    fm = [
        "---",
        f'title: "{title}"',
        f"type: {etype}",
        f"tags: [{etype}]",
        f"created: {TODAY}",
        f"updated: {TODAY}",
        f'sources: ["[[raw/notes/{plan.topic}/{plan.companion_note.stem}]]"]',
        "confidence: medium",
        "---",
        "",
    ]
    return "\n".join(fm) + body.rstrip() + "\n"


def _append_seen_in(target: Path, plan: IngestPlan, addition: str):
    existing = target.read_text(encoding="utf-8", errors="ignore")
    section = (
        f"\n\n## Seen in: {plan.title}\n\n"
        f"*Source: [[raw/notes/{plan.topic}/{plan.companion_note.stem}]]*\n\n"
        f"{addition.strip()}\n"
    )
    # Bump the `updated:` field if present
    new_text = re.sub(r"^updated:\s*\d{4}-\d{2}-\d{2}",
                      f"updated: {TODAY}", existing, count=1, flags=re.MULTILINE)
    if section.strip() in new_text:
        return  # idempotent: don't double-append the same addition
    new_text = new_text.rstrip() + section
    target.write_text(new_text, encoding="utf-8")


def _safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "-", name).strip()[:80]


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Ingest a draw.io diagram into the LLM Wiki vault.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python .tools/ingest_drawio.py ~/Downloads/auth.drawio
              python .tools/ingest_drawio.py auth.drawio --topic auth-flow
              python .tools/ingest_drawio.py auth.drawio --dry-run
              python .tools/ingest_drawio.py auth.drawio --no-svg   # Mermaid only
        """)
    )
    ap.add_argument("path", help="Path to the .drawio or .xml export")
    ap.add_argument("--vault", help="Vault root (defaults to current working directory)")
    ap.add_argument("--topic", help="Topic slug (folder under raw/notes/). Defaults to inferred.")
    ap.add_argument("--slug", help="Diagram slug (filename stem). Defaults to inferred.")
    ap.add_argument("--no-date", action="store_true",
                    help="Drop the YYYY-MM-DD prefix from the staged XML and companion note filenames.")
    ap.add_argument("--no-svg", action="store_true",
                    help="Skip SVG sidecar files; embed Mermaid only in the companion note.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Plan, prompt, and print outputs to stdout — write nothing.")
    args = ap.parse_args()

    plan = build_plan(args)
    ctx = gather_context(plan)

    if args.dry_run:
        print()
        print("=" * 60)
        print("DRY RUN — prompt that would be sent to Claude:")
        print("=" * 60)
        print(build_user_prompt(plan, ctx)[:4000])
        print("...")
        print()
        print(f"Would stage to: {plan.staged_xml}")
        print(f"Would write:    {plan.companion_note}")
        return

    ai_data = call_claude(plan, ctx)

    # Order matters: stage XML so the Mermaid renderer can read it; apply wiki
    # actions first so we know which titles actually landed; THEN write the
    # companion note with the verified applied_titles in its frontmatter.
    stage_xml(plan)
    created, enriched, applied = apply_wiki_actions(plan, ai_data, ctx)
    write_companion_note(plan, ai_data, applied)
    print(f"📝 Companion note → {plan.companion_note.relative_to(plan.vault)}")

    print()
    print(f"✅ Done.")
    print(f"   Companion note: 1")
    print(f"   Wiki pages created: {created}")
    print(f"   Wiki pages enriched: {enriched}")
    print(f"   Total wiki updates: {created + enriched}")


if __name__ == "__main__":
    main()
