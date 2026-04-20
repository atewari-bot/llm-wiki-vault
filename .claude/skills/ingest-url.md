# Skill: /ingest-url

**Trigger:** `/ingest-url <URL>`

## What This Does
Fetches an article from a URL, saves a clean markdown copy to `raw/articles/`, then compiles the content into 5–15 wiki pages.

## Steps

### 1. Fetch & Clean
- Retrieve the full article content from the URL
- Strip ads, nav, footers — keep title, author, date, body, and any images worth preserving
- Save to `raw/articles/YYYY-MM-DD-slug.md` with this frontmatter:

```yaml
---
title: "Article Title"
author: "Author Name"
source_url: "https://..."
fetched: YYYY-MM-DD
tags: [raw, article]
status: processed
---
```

### 2. Extract Concepts
Read the full article and identify:
- **Key concepts** — ideas, frameworks, mental models
- **People mentioned** — researchers, practitioners, thinkers
- **Tools/systems mentioned** — software, methods, workflows
- **Claims** — specific assertions worth tracking
- **Connections** — what existing wiki pages does this relate to?

### 3. Update the Wiki
For each concept identified:
1. Check if a page already exists in `wiki/concepts/`
2. If yes — add new information, new sources, update `updated:` date
3. If no — create a new page using the standard frontmatter format
4. Wikilink aggressively — every concept, person, tool gets `[[linked]]`
5. Add a `## See Also` section at the bottom

Target: touch **5–15 wiki pages** per ingest. More is better.

### 4. Update Index
Add the newly created/updated pages to `wiki/meta/index.md` under "Recently Updated."

## Example Output
After running `/ingest-url https://example.com/article`:
```
✅ Saved raw article → raw/articles/2026-04-18-article-title.md
📝 Created: wiki/concepts/concept-a.md
📝 Created: wiki/people/researcher-name.md
✏️  Updated: wiki/concepts/existing-concept.md (+3 paragraphs, +1 source)
✏️  Updated: wiki/tools/relevant-tool.md
📊 Index updated: 2 new pages, 2 updated
```
