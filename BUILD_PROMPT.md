# LLM Wiki Vault — Complete Build Prompt

Paste this entire file into a fresh Claude / Cowork session on any machine to recreate the vault from scratch. Claude will create every file, directory, and script needed to run the full system.

---

## INSTRUCTION TO CLAUDE

You are setting up a personal knowledge management vault called **LLM Wiki Vault** from scratch. The user wants you to create every file and directory listed below exactly as specified. This is a rebuild of an existing system — do not improvise structure or behaviour.

**Steps:**
1. Create the folder scaffold
2. Create `CLAUDE.md`, `HELP.md`, `.gitignore`, `.tools/requirements.txt`, `.tools/.env` template
3. Create every file in `.tools/` and `.claude/skills/` by copying faithfully from the canonical repo snapshot the user provides
4. Confirm completion and give the user their first commands

The vault root is the folder the user has open (their selected workspace folder). Create all files there.

---

## STEP 1 — Folder Scaffold

Create these directories (use `mkdir -p`):

```
raw/notes/.keep
raw/todos/.keep
wiki/concepts/.keep
wiki/tools/.keep
wiki/meta/.keep
reports/daily/.keep
reports/weekly/.keep
reports/discoveries/.keep
reports/review/.keep
reports/mindmap/.keep
reports/onepager/.keep
reports/slides/.keep
.tools/
.claude/skills/
```

---

## STEP 2 — CLAUDE.md (Operating Rules)

Create `CLAUDE.md` at the vault root with this exact content:

```markdown
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
```

---

## STEP 3 — .gitignore

Create `.gitignore` at vault root:

```
# Python
.tools/.venv/
.tools/__pycache__/
.tools/scripts/__pycache__/
*.pyc
*.pyo

# Secrets — never commit
.tools/.env
.tools/token.json

# Build artefacts
.tools/graph.json
.tools/output/
.tools/watch.log
```

---

## STEP 4 — .tools/requirements.txt

```
anthropic>=0.25.0
networkx>=3.2
watchdog>=4.0
python-dotenv>=1.0.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
google-api-python-client>=2.120.0
```

---

## STEP 5 — .tools/.env (template — user must fill in)

Create `.tools/.env.example`:

```
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
```

Copy to `.tools/.env` and instruct the user to paste their real key.

---

## STEP 6 — Python and Shell Scripts (.tools/)

Create these scripts inside `.tools/`. Copy each one faithfully from the canonical repo snapshot the user provides — do not improvise or re-design behaviour.

Python scripts (all load `.tools/.env` via `python-dotenv`):
- `daily.py` — daily briefing generator (Calendar + todos + carry-forward + gaps)
- `weekly.py` — weekly review aggregator
- `eod.py` — headless end-of-day capture
- `discover.py` — serendipity engine (bridges, sequences, anomalies)
- `review.py` — confidence decay audit
- `gcal.py` — Google Calendar fetch via OAuth token
- `gcal_auth.py` — one-time Google Calendar OAuth setup → writes `.tools/token.json`
- `knowledge_graph_builder.py` — full-vault knowledge graph enrichment
- `scripts/exporters.py` — vault exporters (Obsidian, Miro XML) used by graph builder

Shell scripts:
- `setup.sh` — creates venv, installs requirements
- `build-graph.sh` — invokes knowledge graph builder
- `run-daily.sh`, `run-weekly.sh`, `run-eod.sh`, `run-discover.sh`, `run-review.sh`, `run-mindmap.sh` — headless runners
- `run-gcal-auth.sh` — one-time Google Calendar OAuth flow
- `schedule.sh`, `schedule-discover.sh`, `schedule-mindmap.sh`, `schedule-eod.sh` — install/remove launchd (macOS) or cron (Linux) jobs

All shell scripts must reference `$VAULT/.tools/` (NOT `tools/`) in internal paths.

Schedule defaults:

| Script | PLIST_ID | Hour | Minute | RUNNER |
|--------|----------|------|--------|--------|
| schedule.sh | `com.llm-wiki-vault.daily` | 8 | 0 | run-daily.sh |
| schedule-discover.sh | `com.llm-wiki-vault.discover` | 6 | 0 | run-discover.sh |
| schedule-mindmap.sh | `com.llm-wiki-vault.mindmap` | 7 | 0 | run-mindmap.sh |
| schedule-eod.sh | `com.llm-wiki-vault.eod` | 18 | 0 | run-eod.sh |

---

## STEP 7 — Skills (.claude/skills/)

Create these skill files — each documents a trigger and its step-by-step behaviour. Copy faithfully from the canonical repo:

- `ingest-url.md` — `/ingest-url <URL>` → raw/notes/YYYY-MM/ + wiki pages
- `process-inbox.md` — `process notes` → wikify raw/notes/
- `build-graph.md` — full-vault graph enrichment via Python
- `smart-index.md` — silent index refresh after every wiki write
- `daily.md` — daily briefing
- `weekly.md` — weekly review
- `discover.md` — serendipity engine
- `mindmap.md` — Mermaid mind map per topic
- `onepager.md` — external-audience doc, no wikilinks
- `conflicts.md` — contradiction tracker
- `review.md` — confidence decay

---

## STEP 8 — HELP.md

Create `HELP.md` at the vault root with this content:

```markdown
# LLM Wiki Vault — Quick Reference

## Setup
```bash
bash .tools/setup.sh                       # one-time setup (Mac/Linux)
bash .tools/run-gcal-auth.sh               # enable Google Calendar (optional)
bash .tools/schedule.sh install            # daily briefing at 8am
bash .tools/schedule-discover.sh install   # discovery at 6am
bash .tools/schedule-mindmap.sh install    # mindmap at 7am
bash .tools/schedule-eod.sh install        # EOD capture at 6pm
cd llm-wiki-vault && claude                # start Claude Code
```

## Daily habit
| Time | Command | What happens |
|------|---------|-------------|
| Morning | `daily` | Calendar + todos → reports/daily/YYYY-MM-DD.md |
| During day | `ingest https://...` | Article → wiki pages |
| During day | `process notes` | Wikify raw/notes/ |
| During day | `todo <text>` | Append to today's raw/todos/YYYY-MM-DD.md |
| Evening | `eod` | Check completions, capture bullets |
| Friday | `weekly` | Week summary → reports/weekly/YYYY-WNN.md |

## All Claude Code commands
| Say | Action |
|-----|--------|
| `ingest <url>` | Fetch article → wiki |
| `process notes` | Wikify raw/notes/ |
| `lint` | Wiki health check |
| `build graph` | Run `bash .tools/build-graph.sh` |
| `todo <text>` / `add todo <text>` | Append task to today's raw/todos/ |
| `show todos` / `clear todos` | Read or mark-done today's todos |
| `plan day` | Interactive multi-todo input + briefing |
| `daily` | Morning briefing with Calendar |
| `eod` | End-of-day capture |
| `weekly` | Weekly review |
| `discover` | Find hidden connections |
| `mindmap <topic>` | Mermaid mindmap → reports/mindmap/ |
| `conflicts` | Scan contradictions |
| `review` | Confidence decay audit |
| `onepager <topic>` | Shareable doc → reports/onepager/ |
| `slides <topic>` | Marp deck → reports/slides/ |
| `report on <topic>` | Write document → reports/ |

## File locations
| What | Where |
|------|-------|
| Fleeting notes / articles / EOD | raw/notes/YYYY-MM/ |
| Manual todos | raw/todos/YYYY-MM-DD.md |
| Wiki pages | wiki/concepts/ tools/ |
| Daily briefings | reports/daily/YYYY-MM-DD.md |
| Weekly reviews | reports/weekly/YYYY-WNN.md |
| Mindmaps | reports/mindmap/<slug>.md |
| One-pagers | reports/onepager/<slug>.md |
| Slide decks | reports/slides/<slug>.md |
| Discoveries | reports/discoveries/YYYY-MM-DD.md |
| Wiki dashboard | wiki/meta/index.md |
| Gap report | wiki/meta/graph-report.md |
| Conflict tracker | wiki/meta/conflicts.md |

## Cadence
| Feature | When |
|---------|------|
| `discover` | Weekly, after build-graph |
| `conflicts` | After large batch of ingests |
| `review` | Monthly |
| `build-graph` | Weekly or after big ingest |

## Auth notes
- Claude Code → uses your claude.ai login (no API key needed)
- Python tools → use ANTHROPIC_API_KEY from `.tools/.env`
- Do NOT export ANTHROPIC_API_KEY in same terminal as `claude`
- Google Calendar → OAuth token saved to `.tools/token.json` (gitignored)
```

---

## STEP 9 — Confirm Completion

After creating all files, print:

```
✅ LLM Wiki Vault — Setup Complete

Vault structure created with:
  raw/ — drop your notes and todos here
  wiki/ — Claude will build knowledge here
  reports/ — daily briefings, weekly reviews, etc.
  .tools/ — automation scripts (hidden from Obsidian)

Next steps:
  1. Edit .tools/.env with your ANTHROPIC_API_KEY
  2. bash .tools/setup.sh — create Python venv and install dependencies
  3. bash .tools/run-gcal-auth.sh — enable Google Calendar headless access
  4. bash .tools/schedule.sh install — daily briefing at 8am
  5. bash .tools/schedule-discover.sh install
  6. bash .tools/schedule-mindmap.sh install
  7. bash .tools/schedule-eod.sh install

Open this folder in Cowork or Claude Code, then say:
  daily           → generate your first briefing
  ingest <url>    → capture your first article
```

---

## Important Notes for Claude

- The `.tools/` folder starts with a dot — Obsidian hides it automatically (no noise in sidebar)
- All shell scripts must reference `.tools/` (not `tools/`) in internal paths
- Python script source of truth is the canonical repo checkout. When rebuilding, copy the current `.tools/` contents verbatim — do not re-derive behaviour from scratch
- Skill source of truth is `.claude/skills/*.md` in the canonical repo. Copy each faithfully
