"""
enricher.py — Send parsed content to Claude for semantic enrichment.
"""
import json
import anthropic


def enrich(notes=None, nodes=None, edges=None):
    content_block = _build_content_block(notes, nodes, edges)

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system="""You are a knowledge graph builder. Extract a rich semantic graph from the provided notes/diagrams.

Return ONLY valid JSON (no markdown fences):
{
  "entities": [{"id": "e1", "label": "Name", "type": "concept", "aliases": [], "description": "1-2 sentences"}],
  "relationships": [{"source": "e1", "target": "e2", "type": "relates_to", "confidence": 0.9, "rationale": "why"}],
  "clusters": [{"name": "Cluster", "entity_ids": ["e1"], "theme": "what unifies"}],
  "gaps": [{"description": "what is missing", "suggested_entity": "name", "connected_to": ["e1"]}],
  "summary": "One paragraph overview."
}

Entity types: concept, tool, project, question, insight, event, process, architecture
Relationship types: relates_to, depends_on, contradicts, supports, part_of, leads_to, created_by, used_in, contrasts_with

Be generous with relationships. Surface non-obvious connections.""",
        messages=[{"role": "user", "content": content_block}]
    )

    raw = response.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Warning: JSON parse error: {e}")
        print("Raw:", raw[:300])
        return {"entities": [], "relationships": [], "clusters": [], "gaps": [], "summary": "Parse error."}


def _build_content_block(notes, nodes, edges):
    parts = []
    if notes:
        parts.append("## Obsidian Notes\n")
        for n in notes[:40]:
            parts.append(f"### {n['title']}\n")
            if n.get("tags"):
                parts.append(f"Tags: {', '.join(n['tags'])}\n")
            if n.get("links"):
                parts.append(f"Links to: {', '.join(n['links'])}\n")
            parts.append(n["body"][:800] + "\n\n")
    if nodes:
        parts.append("## Diagram Nodes\n")
        for nd in nodes:
            parts.append(f"- [{nd['type']}] {nd['label']} (id: {nd['id']})\n")
    if edges:
        parts.append("\n## Diagram Edges\n")
        for e in edges:
            parts.append(f"- {e['source']} --[{e['label']}]--> {e['target']}\n")
    parts.append("\n\nExtract a comprehensive knowledge graph from all content above.")
    return "".join(parts)
