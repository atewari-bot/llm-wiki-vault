# Skill: onepager — /onepager <topic>

## Triggers
- "onepager <topic>" or "one pager <topic>"
- "summary of <topic>" or "write a onepager on <topic>"

## What This Does

Generates a clean, self-contained document about a topic for sharing with people
who don't have access to the vault. No wikilinks, no internal references — written
for an external reader. Max 600 words.

Saves to: reports/onepager/<slug>.md

---

## Steps

1. Search wiki/concepts/, wiki/people/, wiki/tools/ for up to 10 pages related to <topic>
   (direct name match, tag match, or wikilink proximity)

2. If no wiki pages found: tell user to ingest first before generating a onepager

3. Synthesize from all relevant pages:
   - Core definition (what is this, in plain language?)
   - Why it matters (what problem does it solve?)
   - How it works (3-5 numbered steps or principles)
   - Key people and tools (names + one-line descriptions)
   - Tradeoffs (strengths vs limitations table)
   - Further reading (real URLs from wiki page source frontmatter only)

4. Save to reports/onepager/<slug>.md

Format:
---
title: "<Topic>"
date: YYYY-MM-DD
type: onepager
audience: external
wiki_pages_used: N
---
# <Topic>
## What it is
[2-3 sentence plain-language definition]
## Why it matters
[2-3 sentences on significance]
## How it works
1. [step]
2. [step]
3. [step]
## Key people & tools
- Name — one line description
## Tradeoffs
| Strength | Limitation |
|----------|-----------|
| ...      | ...        |
## Further reading
- [source title](url)
---
*Generated from personal knowledge base · YYYY-MM-DD*

## Rules (strictly enforced)
- NO wikilinks [[like this]] anywhere in output
- NO internal vault references
- Plain language — assume zero prior context
- Max 600 words total
- Every claim must trace to a wiki page or raw source

## Confirm
```
Onepager ready → reports/onepager/<slug>.md
Wiki pages used: N  Word count: ~N
Ready to share
```
