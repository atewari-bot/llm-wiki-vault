# Skill: smart index — auto-update wiki/meta/index.md

## Triggers
- Runs automatically after every: ingest, process inbox, process notes, build graph
- "update index" or "refresh index"

## What This Does

Keeps `wiki/meta/index.md` as a live dashboard by scanning the vault
and rewriting the index with current counts, recent activity, and open gaps.
Claude runs this silently at the end of every operation that modifies wiki/.

---

## Steps

### 1. Scan wiki/ structure

Count pages per subfolder:
- wiki/concepts/ — count .md files (exclude .gitkeep)
- wiki/people/   — count .md files
- wiki/tools/    — count .md files
- wiki/meta/     — count .md files (excluding index.md itself)

For each cluster in wiki/meta/*MOC*.md, count member pages.

### 2. Find recently updated pages

Scan all wiki/ pages for `updated: YYYY-MM-DD` in frontmatter.
Sort descending. Take top 7.

### 3. Read open gaps

Open wiki/meta/graph-report.md.
Extract the gaps list (lines under "## Gaps & Suggested Research").
Take top 3.

### 4. Find trending topics

Count how many wiki pages link to each concept via [[wikilinks]].
Top 3 most-linked pages = trending.

### 5. Rewrite index.md

```markdown
---
title: "Wiki Index"
tags: [meta, index]
updated: YYYY-MM-DD
---

# Knowledge Base Index

> Last updated: WEEKDAY MONTH DAY · TOTAL pages across N clusters

## Domains

| Cluster | MOC | Pages | Last updated |
|---------|-----|-------|-------------|
| [cluster] | [[Cluster (MOC)]] | N | YYYY-MM-DD |

## By type

| Type | Count |
|------|-------|
| Concepts | N |
| People | N |
| Tools | N |

## Recently updated
[Last 7 pages with updated date]
- [[Page]] — YYYY-MM-DD
  
## Open gaps
[Top 3 from graph-report]
1. [topic] — [description]

## Trending
[Top 3 most-linked pages]
- [[Page]] — linked from N pages

## Quick navigation
- [[graph-report]] — knowledge gaps and summary
- Raw sources: `raw/articles/` · `raw/notes/` · `raw/inbox/`
- Reports: `reports/`
```

### 6. Silent confirmation

After updating, Claude simply notes:
```
📊 Index updated — N total wiki pages
```

No further output unless the user asked for it explicitly.
