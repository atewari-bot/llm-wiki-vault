# Skill: /build-graph

**Trigger:** `/build-graph` (or run directly: `bash .tools/build-graph.sh`)

## What This Does

Reads the entire vault, sends all notes to Claude for deep semantic enrichment, and writes a fully cross-linked knowledge graph back into the wiki.

This goes deeper than `/ingest-url` — instead of processing one source at a time, it sees everything at once and surfaces connections across your entire knowledge base.

## When to Run

- Weekly, after a batch of ingests
- After importing a new domain of notes
- When `/lint-wiki` shows many orphan pages or gaps
- When you want to see how your knowledge clusters

## What Gets Generated

| Output | Location | What it is |
|--------|----------|------------|
| Entity pages | `.tools/output/obsidian/` | One `.md` per concept or tool |
| Cluster MOCs | `.tools/output/obsidian/` | Map-of-content pages per theme |
| Gap report | `.tools/output/obsidian/00 - Knowledge Graph Report.md` | Missing concepts Claude detected |
| Graph JSON | `.tools/output/graph.json` | Full graph data (nodes, edges, stats) |
| Miro XML | `.tools/output/miro_enriched.xml` | Optional: import into Miro |

## How to Run

```bash
# Mac/Linux
bash .tools/build-graph.sh

# Windows
powershell -File tools\build-graph.ps1

# With a draw.io diagram merged in
bash .tools/build-graph.sh --drawio mydiagram.xml

# With a Miro XML export merged in
bash .tools/build-graph.sh --miro board.xml

# Preview only, no files written
bash .tools/build-graph.sh --dry-run
```

## After Running

Review `.tools/output/obsidian/00 - Knowledge Graph Report.md` first — it has the summary and gap list.

Then import into your wiki:
```bash
# Mac/Linux
cp -r .tools/output/obsidian/* wiki/

# Windows
xcopy tools\output\obsidian\* wiki\ /E /Y
```

## What Claude Does Under the Hood

1. Parses all `.md` files in the vault (tags, wikilinks, frontmatter, body)
2. Sends up to 40 notes to Claude Sonnet in a single enrichment call
3. Claude extracts entities, infers relationships, clusters by theme, and detects gaps
4. Writes one `.md` page per entity with full frontmatter, relationships, and See Also
5. Writes one MOC page per cluster
6. Writes a gap + summary report
