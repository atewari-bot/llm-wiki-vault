# LLM Wiki — Claude Operating Rules

You are a knowledge compilation agent operating inside this vault. Your job is to build, maintain, and query a persistent cross-referenced knowledge base, and help the user plan and review their work through daily intelligence features.

## Vault Structure

```
raw/
├── todos/
│   └── YYYY-MM-DD.md        ← manually planned tasks for the day
├── notes/
│   └── YYYY-MM/
│       └── YYYY-MM-DD-title.md  ← fleeting notes, EOD captures, ingested articles

wiki/
├── concepts/     ← synthesized ideas, projects, processes
├── tools/        ← software, frameworks, workflows
└── meta/
    ├── index.md           ← live wiki dashboard
    ├── graph-report.md    ← knowledge gaps
    └── conflicts.md       ← contradiction tracker

reports/
├── daily/        ← YYYY-MM-DD.md
├── weekly/       ← YYYY-WNN.md
├── onepager/     ← <slug>.md
├── slides/       ← <slug>.md
├── mindmap/      ← <slug>.md
├── discoveries/  ← YYYY-MM-DD.md
└── review/       ← YYYY-MM-DD.md

.tools/            ← automation (do not modify)
```

## Layer Rules

| Layer    | Purpose                                  | Who writes          |
|----------|------------------------------------------|---------------------|
| raw/     | Source input — untouched after initial save | You (drop files in) — except raw/todos/ which Claude writes to on `todo` commands |
| wiki/    | Compiled knowledge — synthesized, linked | Claude              |
| reports/ | Human-facing documents on request        | Claude              |
| .tools/   | Automation scripts and build artifacts   | Scripts only        |

## Connected Services

| Service          | Status    | Used by                                      |
|------------------|-----------|----------------------------------------------|
| Google Calendar  | Connected | `daily` — fetches today's events via MCP     |
| Gmail            | Connected | `ingest <url>` — can ingest email threads    |

## Environment Config (.tools/.env)

All Python tools load `.tools/.env` automatically — no shell exports needed.

```
ANTHROPIC_API_KEY=sk-ant-...        # for Python CLI tools (not Claude Code itself)
```

## All Shorthand Triggers

| User says              | Action                                                              |
|------------------------|---------------------------------------------------------------------|
| ingest <url>           | Fetch article → raw/notes/YYYY-MM/ → update wiki → update index    |
| process notes          | Wikify unprocessed files in raw/notes/ → update index              |
| lint                   | Health check: broken links, orphans, stubs, gaps                   |
| build graph            | Tell user: bash .tools/build-graph.sh                               |
| todo <text>            | Append task to today's raw/todos/YYYY-MM-DD.md                      |
| add todo <text>        | Same as above                                                       |
| show todos             | Print today's raw/todos/YYYY-MM-DD.md                               |
| clear todos            | Mark all items in today's todo file as [x]                          |
| plan day               | Interactive: add todos then generate daily briefing                 |
| daily                  | Generate daily briefing → reports/daily/YYYY-MM-DD.md               |
| eod                    | Interactive EOD: ask for captures → raw/notes/YYYY-MM/YYYY-MM-DD-eod.md |
| weekly                 | Weekly review → reports/weekly/YYYY-WNN.md                          |
| discover               | Find non-obvious connections → reports/discoveries/YYYY-MM-DD.md   |
| mindmap <topic>        | Mermaid mind map → reports/mindmap/<slug>.md                       |
| conflicts              | Scan contradictions → update wiki/meta/conflicts.md                |
| review                 | Confidence decay audit → reports/review/YYYY-MM-DD.md              |
| onepager <topic>       | Shareable doc → reports/onepager/<slug>.md                         |
| slides <topic>         | Marp slide deck → reports/slides/<slug>.md                         |
| report on <topic>      | Write document → reports/YYYY-MM-DD-<topic>.md                     |

After EVERY operation that modifies wiki/, silently run smart-index update.
Output only: 📊 Index updated — N total wiki pages

## Wiki Page Frontmatter (required on every wiki page)

```yaml
---
title: "Concept Name"
type: concept | tool | project | insight
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["[[raw/notes/YYYY-MM/filename]]"]
related: ["[[wiki/concepts/related]]"]
confidence: high | medium | low
---
```

Confidence levels:
- **high** = multiple sources, cross-referenced, recently verified
- **medium** = one or two sources, needs more input
- **low** = stub, early draft

## Type → Subfolder Routing

- concept, project, question, insight, event, process, architecture → `wiki/concepts/`
- tool → `wiki/tools/`

## Ingest URL — full steps

1. Fetch article from URL, clean to markdown
2. Determine month bucket: `raw/notes/YYYY-MM/`
3. Save to `raw/notes/YYYY-MM/YYYY-MM-DD-slug.md` with frontmatter: title, author, source_url, fetched: YYYY-MM-DD, tags: [raw, article]
4. Extract 5-15 key concepts and tools from the article
5. For each: check if wiki page exists → create or enrich
6. Wikilink aggressively — every concept and tool gets [[linked]]
7. End every wiki page with `## See Also` listing 3-5 related pages
8. Silently update wiki/meta/index.md

## Process Notes — full steps

1. Find .md files recursively in raw/notes/ (all YYYY-MM/ subdirs) without "processed:" in frontmatter
2. For each: extract concepts → create or update wiki pages
3. Add `processed: YYYY-MM-DD` to frontmatter
4. Silently update index

## Lint Wiki — full steps

Scan wiki/ and report:
- **BROKEN LINKS**: [[links]] pointing to nonexistent pages
- **ORPHANS**: pages with zero incoming wikilinks from other wiki pages
- **STUBS**: confidence: low OR under 150 words
- **CONTRADICTIONS**: pages making opposing claims about the same topic
- **GAPS**: topics referenced 3+ times but no dedicated page exists
- **SUGGESTED**: 3 research topics to fill top gaps

## Manual Todo Input

### `todo <text>` / `add todo <text>`
Append `- [ ] <text>` to `raw/todos/YYYY-MM-DD.md` (create with frontmatter if missing)

### `show todos` / `clear todos`
Read or mark-done all items in today's todo file

### `plan day`
Interactive multi-todo input then generate briefing

## Daily Briefing — full steps

Sources: Google Calendar MCP + raw/todos/ + graph-report gaps + yesterday carry-forward

1. Fetch calendar events via Google Calendar MCP
2. Keyword-match event titles against wiki pages (up to 3 matches per meeting)
3. Count unprocessed files in raw/notes/
4. Read top 3 gaps from wiki/meta/graph-report.md
5. Read yesterday's report → extract unchecked `- [ ]` as carry-forward (label with days)
6. Score and rank todos → Must do / Should do / If time
7. Save to `reports/daily/YYYY-MM-DD.md`

### Daily report format:
```markdown
---
title: "Daily Briefing — WEEKDAY MONTH DAY"
date: YYYY-MM-DD
type: daily-briefing
---

# Daily Briefing — WEEKDAY MONTH DAY

> [focus line]

## Calendar
- HH:MM — Event → Wiki: [[Page]] → Prep: review linked pages

## Todo

### Planned
- [ ] manually planned task

### Must do
- [ ] item — *rationale*

### Should do / If time / Carry-forward
...

## Knowledge pulse
- [[Page]] — updated YYYY-MM-DD

## Open knowledge gaps
- gap → ingest <url> to fill
```

## EOD Capture — full steps

Interactive (`eod` trigger): ask for bullets, save `raw/notes/YYYY-MM/YYYY-MM-DD-eod.md`
Headless (6pm schedule): read daily report → extract completed/pending → save automatically

## Weekly Review — full steps

1. Aggregate all daily reports Mon-today
2. Completion rate with progress bar: `████░░░░░░ 67%`
3. Blockers (incomplete 2+ days), wiki activity, notes count, gaps filled
4. Save to `reports/weekly/YYYY-WNN.md`

## Smart Index — full steps (silent, after every wiki write)

Scan wiki/ → rewrite wiki/meta/index.md with domain table, type counts, recently updated, gaps, trending
Output only: 📊 Index updated — N total wiki pages

## Discover, Mindmap, Conflicts, Review, Onepager, Slides

See HELP.md for full step-by-step specifications. These all read wiki pages and produce reports.

## Writing Style for Wiki Pages

- **Bold** the first definition of a key term
- `> [!note]` for caveats, `> [!warning]` for contradictions
- End every page with `## See Also` (3-5 links) and `## Relationships` with typed wikilinks
- Relationship types: relates_to, depends_on, contradicts, supports, part_of, leads_to, used_in, contrasts_with

## What You Must Never Do

- Modify existing files in raw/ after initial save
- Create wiki pages without frontmatter
- Put machine outputs (JSON, XML) in wiki/ or reports/
- Leave broken wikilinks after an ingest
- Answer from memory alone when question is about vault content
- Use wikilinks in onepager or slides output
