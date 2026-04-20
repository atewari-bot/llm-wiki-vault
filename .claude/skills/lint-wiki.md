# Skill: /lint-wiki

**Trigger:** `/lint-wiki`

## What This Does
Audits the entire wiki for health issues and generates a report with actionable fixes.

## Checks to Run

### 1. Broken Wikilinks
Scan all `[[links]]` across every wiki page. Check if the target file exists.
Report as: `⚠️ BROKEN: [[Target]] referenced in wiki/concepts/page.md`

### 2. Orphan Pages
Find wiki pages that have **zero incoming links** from other wiki pages.
These are dead ends — no other page points to them.
Report as: `🏝️ ORPHAN: wiki/concepts/page.md (no incoming links)`

### 3. Stubs
Find pages with `confidence: low` in frontmatter, or pages with fewer than 150 words.
Report as: `📄 STUB: wiki/concepts/page.md — needs enrichment`

### 4. Missing Frontmatter
Find wiki pages missing required frontmatter fields (title, tags, created, updated, confidence).
Report as: `❌ MISSING FRONTMATTER: wiki/concepts/page.md — missing: confidence, updated`

### 5. Contradictions
Scan for pages that make conflicting claims about the same topic.
Look for: "X is Y" on one page and "X is not Y" on another.
Report as: `⚡ CONTRADICTION: wiki/concepts/a.md vs wiki/concepts/b.md — conflicting claim about [topic]`

### 6. Stale Pages
Find pages with `updated:` more than 90 days ago that have `confidence: low` or `medium`.
These may need revisiting.

### 7. Gaps (Suggested Research)
Identify topics that are:
- Frequently referenced via `[[wikilinks]]` but don't have a dedicated page yet
- Mentioned in multiple raw sources but not yet compiled into the wiki

Report the **top 5 gaps** as:
`💡 GAP: "Topic Name" — referenced in N pages, no wiki page exists`

## Output Format

```
# Wiki Health Report — YYYY-MM-DD

## Summary
- Total wiki pages: N
- Total raw sources: N
- Overall health: 🟢 Good / 🟡 Needs attention / 🔴 Critical

## Issues Found

### ⚠️ Broken Links (N)
...

### 🏝️ Orphan Pages (N)
...

### 📄 Stubs (N)
...

### ⚡ Contradictions (N)
...

## 💡 Suggested Next Research
1. [[Topic A]] — referenced in 8 pages, no wiki entry
2. [[Topic B]] — mentioned in 5 raw articles, not yet synthesized
3. ...

## Recommended Actions
1. Fix broken links first (structural integrity)
2. Stub-fill top 3 orphan pages
3. Run /ingest-url on suggested topics above
```
