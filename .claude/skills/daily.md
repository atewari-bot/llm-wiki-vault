# Skill: daily briefing — /daily

## Triggers
- "daily" or "daily briefing" or "morning briefing"
- "what's my day look like"
- "prepare my day"

## What This Does

Synthesizes four sources into a single prioritised daily briefing saved to `reports/YYYY-MM-DD-daily.md`.

**Sources:**
1. **Google Calendar** — today's meetings via MCP
2. **raw/notes/ + raw/todos/** — unprocessed content and planned todos
3. **wiki/meta/graph-report.md** — open knowledge gaps
4. **reports/** — yesterday's daily report for carry-forward items

---

## Steps

### 1. Pull today's calendar
Use Google Calendar MCP to fetch today's events.
For each event, check wiki/ for relevant pages:
- Search wiki/concepts/, wiki/tools/ for pages matching event title keywords
- List up to 3 relevant wiki pages per meeting as prep material

### 2. Check notes state
Count unprocessed files in raw/notes/.
If > 0: add "process notes" as a must-do item.

### 3. Read graph-report gaps
Open wiki/meta/graph-report.md, extract top 3 open gaps.
Convert into "learning todo" items ranked by relevance to today's calendar.

### 4. Carry forward from yesterday
Look for reports/YYYY-MM-DD-daily.md from the previous day.
Extract any unchecked `- [ ]` items.
Label each with how many days it has been carried:
- 1 day: (carried 1 day)
- 2-4 days: (carried N days) — amber flag
- 5+ days: (carried N days — consider dropping) — red flag

### 5. Score and rank todos
Each todo gets a priority score based on:
- **Urgency** — tied to a meeting today? (+3)
- **Carry age** — carried 3+ days? (+2)
- **Knowledge leverage** — fills a wiki gap? (+1)
- **Inbox debt** — unprocessed notes pile > 5? (+1)

Output ranked Must / Should / If-time tiers.

### 6. Write briefing

Save to `reports/YYYY-MM-DD-daily.md`:

```markdown
---
title: "Daily Briefing — WEEKDAY MONTH DAY"
date: YYYY-MM-DD
type: daily-briefing
---

# Daily Briefing — Monday April 21

## Today's focus
[One sentence synthesising what today is really about]

## Calendar
[For each event:]
- HH:MM — Event name (duration)
  → Wiki: [[Relevant Page]], [[Another Page]]
  → Prep: [one-line suggestion]

## Todo

### Must do
- [ ] [item] [rationale in italics]

### Should do
- [ ] [item]

### If time
- [ ] [item]

## Carry-forward
[Only if items exist — list with age labels]
- [ ] [item] *(carried N days)*

## Knowledge pulse
[3 bullets from wiki activity this week]
- New: [[Page]] — [one line]
- Gap: [topic] — suggested ingest
- Conflict: [if any flagged in graph-report]

## Open questions
[Unresolved items from recent reports/]
```

---

## After writing

Tell the user:
```
📅 Daily briefing ready → reports/YYYY-MM-DD-daily.md
  Meetings today: N
  Todos: N must, N should, N if-time
  Carried forward: N items
```
