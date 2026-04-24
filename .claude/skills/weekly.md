# Skill: weekly review — /weekly

## Triggers
- "weekly" or "weekly review"
- "week in review"
- "what happened this week"

## What This Does

A Friday ritual (or any day) that zooms out from daily todos to weekly patterns.
Reads the week's daily reports, EOD notes, wiki activity, and graph-report
to produce a structured weekly review saved to `reports/`.

---

## Steps

### 1. Identify the week
Calculate the current ISO week number (YYYY-WNN).
Find all `reports/YYYY-MM-DD-daily.md` files from this week (Mon–today).
Find all `raw/notes/YYYY-MM-DD-eod.md` files from this week.

### 2. Summarise todo completion
Across all daily reports this week:
- Count total todos (must / should / if-time)
- Count completed `- [x]` vs incomplete `- [ ]`
- Calculate completion rate
- List any item carried 3+ days without completion — flag as "persistent blockers"

### 3. Summarise knowledge activity
Scan wiki/ for pages with `updated: YYYY-MM-DD` matching this week.
Group by type: concepts / tools.
Count new pages created vs existing pages updated.

Scan raw/notes/ for files created this week.
Count: notes captured.

### 4. Read graph-report
From wiki/meta/graph-report.md:
- Which gaps were open at start of week?
- Were any filled (new wiki pages created matching gap names)?
- Which remain open?

### 5. Surface patterns
Claude reads across all sources and writes 2-3 observations:
- What topics dominated your attention this week?
- What did you keep avoiding (persistent carry-forwards)?
- What knowledge areas grew most?

### 6. Write weekly review

Save to `reports/YYYY-WNN-weekly.md`:

```markdown
---
title: "Weekly Review — Week NN, YYYY"
week: YYYY-WNN
date_range: Mon DD – Fri DD Month
type: weekly-review
---

# Week NN — Mon DD to Fri DD Month

## The week in one line
[Claude writes a one-sentence synthesis]

## Todo summary
- Completed: N / N total (N%)
- Completion rate: [progress bar in text: ████░░ 67%]
- Persistent blockers: [items carried 3+ days]

## Knowledge activity
- Notes captured: N
- Wiki pages created: N  updated: N
- Most active area: [cluster name]

## Gaps
- Filled this week: [[Page]], [[Page]]
- Still open: [topic], [topic]

## Patterns Claude noticed
1. [observation]
2. [observation]
3. [observation]

## Next week focus
[3 suggested priorities based on open gaps + persistent blockers]
- [ ] [suggestion 1]
- [ ] [suggestion 2]  
- [ ] [suggestion 3]

## Open items carrying into next week
[All incomplete todos from this week's daily reports]
- [ ] [item] *(carried N days)*
```

### 7. Confirm

```
📊 Weekly review → reports/YYYY-WNN-weekly.md
  Completion rate: N%
  Wiki pages touched: N
  Gaps filled: N  Open: N
```
