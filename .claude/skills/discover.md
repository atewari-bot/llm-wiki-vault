# Skill: serendipity engine — /discover

## Triggers
- "discover" or "discoveries"
- "what connections am I missing"
- "surprise me" or "find connections"
- "what should I link"

## What This Does

Reads the entire wiki and surfaces 3–5 non-obvious connections Claude
notices that you haven't explicitly linked yet. These are bridges between
pages that share underlying structure but live in separate clusters.

This is the most creative operation — it looks for:
- **Structural parallels** — two concepts that solve the same problem differently
- **Hidden contradictions** — pages that imply conflicting things without flagging it
- **Missing bridges** — a person frequently cited in concept pages who has no person page
- **Cluster leakage** — a concept that belongs in two clusters but only sits in one
- **Implicit sequences** — concepts that logically follow each other but aren't linked

---

## Steps

### 1. Load the full wiki graph

Read all pages in wiki/concepts/, wiki/people/, wiki/tools/.
For each page, extract:
- Title, description, tags, confidence
- All outgoing `[[wikilinks]]`
- All relationship types from `## Relationships` section

Build a mental map of: what links to what, what doesn't link but probably should.

### 2. Find unlinked clusters

Identify pairs of wiki pages that:
- Share 2+ tags but have zero wikilinks between them
- Are both linked FROM the same third page but not to each other
- Live in different clusters but use overlapping vocabulary

### 3. Check for implicit people

Scan all concept pages for mentions of names (proper nouns that aren't
already wikilinked). If a name appears in 3+ pages without a [[person page]],
flag it as a missing person page.

### 4. Look for structural parallels

Find concept pairs where:
- Both describe a system that has an "input → process → output" structure
- Both address the same failure mode (maintenance cost, scale limits, etc.)
- Both were created by the same person or school of thought

### 5. Identify implicit sequences

Find triplets of concepts where A leads to B and B leads to C,
but A doesn't directly link to C — surfacing the full chain.

### 6. Write discoveries report

Save to `reports/YYYY-MM-DD-discoveries.md`:

```markdown
---
title: "Discoveries — YYYY-MM-DD"
date: YYYY-MM-DD
type: discoveries
wiki_pages_scanned: N
---

# Discoveries — MONTH DAY

## Bridge connections

### 1. [[Concept A]] ↔ [[Concept B]]
**Why this matters:** [1-2 sentences on the non-obvious link]
**Suggested link type:** relates_to / contrasts_with / supports / etc.
**Action:** Add to [[Concept A]]: `- **relates_to** → [[Concept B]] — [rationale]`

[repeat for each bridge, max 3]

## Missing pages

### [[Person Name]] has no wiki page
Referenced in: [[Page 1]], [[Page 2]], [[Page 3]]
**Action:** `ingest` an article about them, or create a stub page.

[repeat for missing pages, max 2]

## Implicit sequences

### [[A]] → [[B]] → [[C]] (but A doesn't link to C)
**The chain:** [explain the logical progression]
**Action:** Add to [[A]]: `- **leads_to** → [[C]]`

[repeat for sequences, max 2]

## One surprising observation
[One thing Claude noticed that doesn't fit the above categories —
a pattern, an anomaly, a question the wiki raises but doesn't answer]
```

### 7. Confirm

```
🔍 Discoveries → reports/YYYY-MM-DD-discoveries.md
  Bridge connections: N
  Missing pages: N
  Implicit sequences: N
```

---

## Cadence

Run this weekly, ideally after a `/build-graph` pass so the wiki is fresh.
The value compounds — each discovery you act on creates new surface area
for the next run to find connections across.
