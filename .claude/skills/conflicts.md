# Skill: contradiction tracker — /conflicts

## Triggers
- "conflicts" or "contradictions"
- "what contradicts" or "find conflicts"
- "conflicting claims"
- "what disagrees"

## What This Does

Scans all wiki pages for conflicting claims and maintains a live
`wiki/meta/conflicts.md` tracker. Each conflict is presented clearly
with both sides and a resolution prompt — so nothing gets silently buried.

---

## Steps

### 1. Load all wiki pages

Read every `.md` file in wiki/concepts/, wiki/tools/.
For each page, extract all factual claims — sentences that assert
something is true, false, better, worse, causes, prevents, etc.

Focus on:
- "X is Y" / "X is not Y"
- "X causes Y" / "X prevents Y"
- "X is better than Y" / "Y outperforms X"
- "X was created by Y" / "X was created by Z"
- Explicit `> [!warning]` callouts already flagged

### 2. Find conflicts

Compare claims across pages. Flag as a conflict when:
- Two pages make opposing factual claims about the same entity
- One page says X leads to Y; another says X leads to not-Y
- A confidence: high page directly contradicts another confidence: high page

Do NOT flag as conflicts:
- Nuanced perspectives ("X works well for A but not B")
- Temporal differences ("X was true before Y changed it")
- Already-resolved items in wiki/meta/conflicts.md

### 3. Read existing conflicts.md

Open `wiki/meta/conflicts.md` if it exists.
Skip any conflict already listed there (avoid duplicates).

### 4. Present conflicts for resolution

For each NEW conflict found, show:

```
⚡ Conflict: [short description]

Page A: [[Concept A]]
  Claim: "[exact sentence or paraphrase]"

Page B: [[Concept B]]
  Claim: "[exact sentence or paraphrase]"

Resolution options:
  1. Keep both — mark as contested (add [!warning] to both pages)
  2. Page A is correct — update Page B
  3. Page B is correct — update Page A
  4. Merge — create a nuanced page that holds both views
  5. Skip — not actually a conflict
```

Ask the user to choose, or say "auto" to mark all as contested.

### 5. Update wiki/meta/conflicts.md

Append each conflict (resolved or unresolved) to the tracker:

```markdown
## [Short conflict title] — YYYY-MM-DD

**Status:** unresolved | resolved | contested
**Pages:** [[Page A]], [[Page B]]
**Claim A:** [paraphrase]
**Claim B:** [paraphrase]
**Resolution:** [what was decided, or "pending"]
```

### 6. Apply resolutions

For "keep both as contested":
- Add `> [!warning] This claim is contested — see [[conflicts]]` to both pages

For "Page A is correct":
- Update Page B with corrected claim
- Add source attribution

For "merge":
- Create or update a concept page that holds both views with nuance
- Link both original pages to it

### 7. Final summary

```
⚡ Conflicts scan complete
  New conflicts found: N
  Already tracked: N
  Resolved this session: N
  Unresolved (in conflicts.md): N
```

---

## wiki/meta/conflicts.md format

```markdown
---
title: "Conflict Tracker"
tags: [meta, conflicts]
updated: YYYY-MM-DD
---

# Conflict Tracker

Unresolved conflicts are reviewed during /lint and /weekly.

## Active conflicts

[conflicts listed here]

## Resolved conflicts

[resolved items archived here]
```
