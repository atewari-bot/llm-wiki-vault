# Skill: slides — /slides <topic>

## Triggers
- "slides <topic>" or "slide deck <topic>"
- "presentation on <topic>" or "deck for <topic>"

## What This Does

Generates a Marp-compatible markdown slide deck from wiki content.
Saves to: reports/slides/<slug>.md

## Marp rendering (tell user after saving):
```bash
npm install -g @marp-team/marp-cli   # one time
marp reports/slides/<slug>.md         # preview in browser
marp reports/slides/<slug>.md --pdf   # export PDF
marp reports/slides/<slug>.md --pptx  # export PowerPoint
```

---

## Steps

1. Search wiki/ for up to 15 related pages, group by cluster for slide sections

2. Plan 8-12 slides:
   - Slide 1: Title slide
   - Slide 2: Agenda / overview
   - Slides 3-N: One slide per key concept or cluster
   - Second-to-last: Key takeaways (3 bullets max)
   - Last: Further reading / references

3. Save to reports/slides/<slug>.md

File format:
```
---
marp: true
theme: default
paginate: true
title: "<Topic>"
date: YYYY-MM-DD
type: slides
---
# <Topic>
### [one-line subtitle]
*YYYY-MM-DD*
---
## Agenda
- Section 1
- Section 2
---
## <Concept Name>
- [bullet — max 8 words]
- [bullet — max 8 words]
- [bullet — max 8 words]
> Key insight: [one memorable sentence]
---
## Key takeaways
1. [takeaway 1]
2. [takeaway 2]
3. [takeaway 3]
---
## Further reading
- [Source 1]
- [Source 2]
```

## Rules (strictly enforced)
- marp: true in frontmatter
- Max 3 bullets per slide
- Max 8 words per bullet
- One > blockquote per slide
- No wikilinks in output
- Max 12 slides total
- Each --- separates slides

## Confirm
```
Slides ready → reports/slides/<slug>.md
Slides: N  Wiki pages used: N
Render: marp reports/slides/<slug>.md
```
