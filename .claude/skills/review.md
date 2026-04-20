# Skill: confidence decay — /review

## Triggers
- "review" or "confidence review"
- "what's gone stale"
- "review wiki"
- "decay check"

## What This Does

Prevents stale knowledge from silently accumulating authority.
Wiki pages have `confidence: high/medium/low` — but confidence should
decay over time if a page hasn't been updated or re-verified.

This skill audits the entire wiki for staleness and produces a
prioritised review queue.

---

## Decay rules

| Condition | Action |
|-----------|--------|
| `confidence: high` + not updated in 90+ days | Downgrade to `medium`, flag for re-verification |
| `confidence: medium` + not updated in 180+ days | Flag as potentially stale |
| `confidence: low` + created 30+ days ago | Flag as abandoned stub |
| Any page + source URL returns 404 | Flag as dead source |
| Any page that contradicts a newer page | Flag for reconciliation |

**Re-verification means:** finding a current source that confirms
the claim, or updating the content from your own knowledge.

---

## Steps

### 1. Scan all wiki pages

For each page in wiki/concepts/, wiki/people/, wiki/tools/:
- Read `confidence:`, `updated:`, `created:`, `sources:` from frontmatter
- Calculate days since last update
- Check if any source wikilinks point to raw/ files that are themselves old

### 2. Apply decay rules

Categorise each affected page:

**Downgrade candidates** (high → medium, 90+ days):
- List page, current confidence, days since update, original sources

**Stale flagged** (medium, 180+ days):
- List page, days since update

**Abandoned stubs** (low, 30+ days since creation):
- List page, created date

### 3. Show review queue

Present a prioritised list:

```
📋 Review queue — N pages need attention

🔴 Downgrade to medium (high → medium, 90+ days old)
  1. [[Concept A]] — last updated 143 days ago
  2. [[Person B]] — last updated 97 days ago

🟡 Stale — verify or update (medium, 180+ days)
  3. [[Tool C]] — last updated 201 days ago

⚪ Abandoned stubs — complete or delete (low, 30+ days)
  4. [[Concept D]] — created 45 days ago, 80 words
  5. [[Concept E]] — created 38 days ago, 60 words
```

### 4. Apply downgrades automatically

For each downgrade candidate:
- Update frontmatter: `confidence: medium`
- Add a review note at the bottom of the page:

```markdown
> [!warning] Confidence downgraded
> This page was marked high-confidence but hasn't been updated in N days.
> Re-verify claims before relying on this page.
> Last reviewed: YYYY-MM-DD
```

Update `updated:` date in frontmatter to today.

### 5. For stale and stub pages — prompt

For each stale/stub page, ask the user:
```
[[Page Name]] — what would you like to do?
  1. Re-verify — I'll search for a current source
  2. Update — paste new content or a URL
  3. Delete — remove this page from the wiki
  4. Keep — extend the staleness window (skip for 90 more days)
```

### 6. Write review report

Save to `reports/YYYY-MM-DD-review.md`:

```markdown
---
title: "Wiki Review — YYYY-MM-DD"
date: YYYY-MM-DD
type: confidence-review
pages_scanned: N
---

# Wiki Review — MONTH DAY

## Summary
- Pages scanned: N
- Downgraded (high → medium): N
- Stale flagged: N
- Abandoned stubs: N
- User actions taken: N

## Downgraded pages
[list]

## Still needs attention
[pages user deferred]

## Resolved this session
[pages re-verified or deleted]
```

### 7. Update smart index

After review, update wiki/meta/index.md with fresh confidence counts.

### 8. Confirm

```
🔍 Review complete → reports/YYYY-MM-DD-review.md
  Downgraded: N  Stale: N  Stubs: N
  Actions taken: N  Deferred: N
```

---

## Cadence

Run monthly, or after a large batch of ingests when many new pages
might contradict older ones. The `/weekly` review surfaces a reminder
if the last `/review` was more than 30 days ago.
