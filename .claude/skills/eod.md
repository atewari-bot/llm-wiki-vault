# Skill: end of day — /eod

## Triggers
- "eod" or "end of day" or "end of day capture"
- "wrap up" or "day done"

## What This Does

A lightweight evening capture that:
1. Scans what actually happened today
2. Checks which todos were completed
3. Captures quick notes for tomorrow
4. Saves a short EOD note to `raw/notes/` to feed tomorrow's `/daily`

---

## Steps

### 1. Read today's daily report
Open `reports/daily/YYYY-MM-DD.md` (today's date).
Find all `- [ ]` (incomplete) and `- [x]` (complete) items.

If no daily report exists, skip to step 3.

### 2. Summarise completion
```
✅ Completed: N items
⏳ Incomplete: N items → will carry forward
```

List incomplete items — these will auto-carry into tomorrow's daily.

### 3. Prompt for quick captures
Ask the user (in chat):
> "Anything to capture from today? Drop 1-3 quick bullets and I'll save them."

Wait for response. If user says "nothing" or "no", skip to step 4.

Take the user's bullets and format them as a clean note.

### 4. Check notes state
Count files in raw/notes/ that are still unprocessed.
If > 0: suggest running `process notes` before closing out.

### 5. Write EOD note

Save to `raw/notes/YYYY-MM/YYYY-MM-DD-eod.md`:

```markdown
---
title: "EOD Note — YYYY-MM-DD"
date: YYYY-MM-DD
type: eod
processed: false
---

# EOD — WEEKDAY MONTH DAY

## Completed today
[list of checked-off todos from daily report]

## Incomplete → carry forward
[list of unchecked todos — these surface in tomorrow's daily]

## Quick captures
[user's bullets, cleaned up]

## Notes state
[N unprocessed files remaining / notes clear]
```

### 6. Confirm

Tell the user:
```
🌙 EOD note saved → raw/notes/YYYY-MM/YYYY-MM-DD-eod.md
  ✅ Completed: N  ⏳ Carrying forward: N
  [notes status]
  Tomorrow's /daily will pick this up automatically.
```
