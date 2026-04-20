# LLM Wiki Vault — Master Build Prompt

> **Usage:** Paste this entire file into any Claude conversation with file creation
> capability to rebuild the complete vault from scratch.
>
> **Secrets policy:** All API keys, tokens, channel IDs, and user IDs are replaced
> with dummy placeholder values. Replace them in `tools/.env` after setup.
>
> **Auto-updated:** This file is maintained by the vault's `CLAUDE.md` rules.
> Whenever a feature is added or design changes, Claude Code updates this file.

---

Build me a complete "LLM Wiki Vault" from scratch as a downloadable zip file
named `llm-wiki-vault.zip`. Build every file completely — no placeholders, no
truncation, no stubs. Every Python script must be fully functional. Every skill
file must contain complete step-by-step instructions. Provide the zip when done.

---

## SECTION 1: DIRECTORY STRUCTURE

llm-wiki-vault/
├── CLAUDE.md
├── README.md
├── HELP.md
├── BUILD_PROMPT.md          ← this file
├── .gitignore
├── raw/
│   ├── inbox/
│   ├── articles/YYYY-MM/
│   ├── notes/YYYY-MM/
│   ├── todos/YYYY-MM-DD.md          ← manual daily task input (one file per day)
│   └── slack/YYYY-MM-DD/<channel>/
│       ├── digest.md
│       └── data.json
├── wiki/
│   ├── concepts/
│   ├── people/
│   ├── tools/
│   └── meta/
│       ├── index.md
│       ├── graph-report.md
│       └── conflicts.md
├── reports/
│   ├── daily/
│   ├── weekly/
│   ├── onepager/
│   ├── slides/
│   ├── mindmap/
│   ├── discoveries/
│   ├── review/
│   └── README.md
└── tools/
    ├── .env
    ├── setup.sh / setup.ps1
    ├── requirements.txt
    ├── check-notes.sh          ← CRITICAL: mtime-based change detector
    ├── build-graph.sh
    ├── watch-inbox.sh
    ├── schedule.sh
    ├── run-daily.sh / run-weekly.sh / run-discover.sh / run-review.sh
    ├── run-enrich.sh
    ├── run-slack-ingest.sh / run-slack-channels.sh
    ├── knowledge_graph_builder.py
    ├── daily.py / weekly.py / discover.py / review.py
    ├── enrich_tag.py
    ├── slack_ingest.py / slack_channels.py
    └── scripts/
        ├── parsers.py          ← with smart change detection
        ├── enricher.py
        ├── graph_builder.py
        └── exporters.py

.claude/skills/
├── ingest-url.md
├── process-inbox.md          ← includes check-notes.sh + #llm enrichment
├── lint-wiki.md / build-graph.md
├── daily.md / eod.md / weekly.md / smart-index.md
├── discover.md / mindmap.md / conflicts.md / review.md
├── enrich-tag.md
├── onepager.md / slides.md
└── slack-ingest.md / slack-channels.md

---

## SECTION 2: LAYER RULES

raw/     = input only. Claude NEVER modifies existing files after initial save.
wiki/    = Claude writes here. Compiled, cross-linked knowledge pages.
reports/ = Claude writes here on request. Human-facing documents.
tools/   = automation scripts + build artifacts only. NO output/ staging folder.
           Graph builder writes directly to wiki/.

---

## SECTION 3: CLAUDE.md — COMPLETE CONTENT

# LLM Wiki — Claude Operating Rules

You are a knowledge compilation agent. Build, maintain, query a persistent
cross-referenced knowledge base and help the user plan and review their work.

## Connected Services

| Service         | Used by                                       |
|-----------------|-----------------------------------------------|
| Google Calendar | daily — fetches today's events via MCP        |
| Gmail           | ingest <url> — can ingest email threads       |
| Slack           | refresh slack — fetches channels via MCP      |

## Environment Config (tools/.env)

All Python tools load tools/.env automatically via python-dotenv.
ANTHROPIC_API_KEY=sk-ant-REPLACE_WITH_YOUR_KEY
SLACK_BOT_TOKEN=                           # optional
SLACK_CHANNEL_IDS=REPLACE_WITH_CHANNEL_ID  # comma-separated
SLACK_LOOKBACK_HOURS=24
SLACK_MY_USER_ID=REPLACE_WITH_YOUR_ID

Note: Do NOT export ANTHROPIC_API_KEY in the same shell as 'claude'.
Claude Code uses claude.ai login. Python tools use tools/.env.

## All Shorthand Triggers

ingest <url>               → fetch article → raw/articles/ → update wiki → index
process inbox              → check-notes.sh --inbox → enrich → classify → wikify
process notes              → check-notes.sh → enrich tagged → wikify changed files
process all                → process inbox + process notes
lint                       → health check: broken links, orphans, stubs, gaps
build graph                → tell user: bash tools/build-graph.sh
refresh slack              → Slack MCP → raw/slack/YYYY-MM-DD/<ch>/digest.md + data.json
ingest slack               → alias for refresh slack
list/add/remove/search slack channel <x> → python tools/slack_channels.py <cmd>
daily                      → Slack → Calendar → raw/todos/ → briefing → reports/daily/
todo <text>                → append task to raw/todos/YYYY-MM-DD.md (### Inbox)
add todo <text>            → same as todo <text>
show todos                 → display today's raw/todos/YYYY-MM-DD.md with counts
complete todo <item>       → mark matching task [x] in today's file
clear todos                → mark all unchecked [x] in today's file
plan day                   → interactive task entry then full briefing
eod                        → end-of-day capture → raw/notes/YYYY-MM/YYYY-MM-DD-eod.md
weekly                     → review → reports/weekly/YYYY-WNN.md
discover                   → connections → reports/discoveries/YYYY-MM-DD.md
mindmap <topic>            → Mermaid mindmap → reports/mindmap/<slug>.md
conflicts                  → contradictions → wiki/meta/conflicts.md
review                     → confidence decay → reports/review/YYYY-MM-DD.md
enrich                     → #llm-tagged files → web enrichment inline
onepager <topic>           → reports/onepager/<slug>.md (no wikilinks, max 600w)
slides <topic>             → Marp deck → reports/slides/<slug>.md
report on <topic>          → reports/YYYY-MM-DD-<topic>.md

After EVERY wiki write: silently update wiki/meta/index.md.
Output only: Index updated — N total wiki pages

## Wiki Page Frontmatter

---
title: "Concept Name"
type: concept | person | tool | project | insight
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["[[raw/articles/filename]]"]
related: ["[[wiki/concepts/related]]"]
confidence: high | medium | low
---

## Type Routing

concept/project/question/insight/event/process/architecture → wiki/concepts/
person → wiki/people/
tool   → wiki/tools/

## Process Notes — MANDATORY FIRST STEP

ALWAYS run before processing anything:
  bash tools/check-notes.sh          # for notes
  bash tools/check-notes.sh --inbox  # for inbox
  bash tools/check-notes.sh --all    # for both

Read the output. Process exactly what it says ([NEW]/[MODIFIED]/[FORCE]).
Do not decide independently by reading frontmatter.

If "Nothing to process" output:
  Show user output + "To re-process: edit and save in Obsidian, or add
  #llm-reprocess to the note body"

## Change Detection Rules

A note needs re-processing when ANY of these:
  1. No processed: date in frontmatter
  2. File mtime > processed: date
  3. #llm-reprocess tag in body (remove after processing)
  4. Substantial content after last --- that is not an LLM Enrichment block

## #llm Tag Enrichment

When raw note has #llm and no <!-- llm-enriched --> marker:
  1. Extract topics (title → capitalized nouns → hashtags → first sentence)
  2. Search web for current references, insights, related concepts
  3. Append enrichment block below original — NEVER modify original text
  4. Add enriched: YYYY-MM-DD to frontmatter

Enrichment block format:
---
## LLM Enrichment  ·  YYYY-MM-DD
*Auto-generated from web research*
### Summary
[2-3 sentences]
### Key insights
- [finding]
### References
- [Title](url)
  *relevance*
### Related concepts
- [concept]
<!-- llm-enriched -->

Runs automatically BEFORE wikification in process notes/inbox.

## Daily Briefing

Sources: Slack MCP + Google Calendar MCP + inbox state + gaps + yesterday carry-forward
Scoring: meeting +3, carried 3+d +2, Slack≥3 +2, Slack=2 +1, gap +1, inbox>5 +1
Save to reports/daily/YYYY-MM-DD.md. Omit ## From Slack if no Slack items.

## Confidence Decay

high + 90+ days → downgrade to medium + [!warning]
medium + 180+ days → flag stale
low + 30+ days OR <150 words → flag abandoned stub

## Onepager Rules

NO wikilinks. NO internal refs. Plain language. Max 600 words.
What it is / Why it matters / How it works / Key people & tools / Tradeoffs / References

## Slides Rules

marp: true. Max 12 slides. Max 3 bullets/slide. Max 8 words/bullet.
One > blockquote per slide. No wikilinks.

## Never Do

- Modify existing raw/ files after initial save
- Create wiki pages without frontmatter
- Put JSON/XML in wiki/ or reports/
- Leave broken wikilinks after ingest
- Answer from memory when question is about vault content
- Use wikilinks in onepager or slides
- Decide what to process without running check-notes.sh first

## Keeping BUILD_PROMPT.md Current

Update BUILD_PROMPT.md after ANY of:
- New skill or trigger added
- Python tool created or significantly changed
- Shell script added or behaviour changed
- Design decision changed (layer rules, routing, formats)
- Bug fix changes how a core operation works
- New feature built in any conversation

How to update:
  1. Find the relevant SECTION in BUILD_PROMPT.md and update it
  2. Replace ALL real secrets with dummies:
     - API keys → sk-ant-REPLACE_WITH_YOUR_KEY
     - Slack tokens → xoxb-REPLACE_WITH_TOKEN
     - Channel IDs → REPLACE_WITH_CHANNEL_ID
     - User IDs → REPLACE_WITH_YOUR_ID
  3. Confirm: BUILD_PROMPT.md updated — [what changed]

Never put real credentials in BUILD_PROMPT.md.

---

## SECTION 4: PYTHON TOOLS — SPECIFICATIONS

Every Python file loads tools/.env at startup:
  from pathlib import Path
  from dotenv import load_dotenv
  load_dotenv(Path(__file__).parent / ".env")

### tools/requirements.txt
  anthropic>=0.25.0
  networkx>=3.2
  watchdog>=4.0
  python-dotenv>=1.0.0
  slack-sdk>=3.27.0

### tools/scripts/parsers.py

parse_raw(vault_path, subfolders=None, skip_processed=True) -> list[dict]
  Walk raw/ only (skip wiki/reports/tools/.claude/)
  Per file: id, title, body[:3000], tags, links, frontmatter, path,
  subfolder, status, needs_processing (bool), process_reason (str)
  Change detection (_needs_processing):
    1. No processed: date → True, "never processed"
    2. #llm-reprocess in body → True, "manual #llm-reprocess tag"
    3. mtime > processed date → True, "file modified DATE (processed DATE)"
    4. Content after last --- not matching LLM Enrichment block >50 chars → True
    5. Else → False, "up to date"
  skip_processed=True: skip up-to-date files, print count skipped

parse_obsidian(vault_path) -> list[dict]  [legacy]
parse_miro(xml_path) -> tuple[list, list]
parse_drawio(xml_path) -> tuple[list, list]  [handles base64+zlib]
is_drawio(xml_path) -> bool

### tools/scripts/enricher.py

enrich(notes=None, nodes=None, edges=None) -> dict
  Model: claude-sonnet-4-20250514, max_tokens=4000
  Returns: {entities, relationships, clusters, gaps, summary}
  Entity types: concept person tool project question insight event process architecture
  Relationship types: relates_to depends_on contradicts supports part_of
                      leads_to created_by used_in contrasts_with

### tools/scripts/graph_builder.py

build_graph(enriched) -> nx.DiGraph
graph_to_json(G, enriched) -> dict  [nodes, edges, clusters, gaps, summary, stats]
save_graph_json(data, path)

### tools/scripts/exporters.py

TYPE_TO_SUBFOLDER: concept/project/question/insight/event/process/architecture → concepts
                   person → people / tool → tools

export_to_vault(G, enriched, vault_path)
  Entity pages → wiki/{subfolder}/{name}.md
  Cluster MOCs → wiki/meta/{Name} (MOC).md
  Gap report → wiki/meta/graph-report.md
  NO staging folder — write directly to wiki/

export_miro_xml(G, enriched, output_path)
  Grid: 6 cols, 250px x, 180px y spacing
  Colors: concept=#FFD700 person=#FF6B9D tool=#4ECDC4
          question=#FF6B35 insight=#95E1D3 process=#A8E6CF

### tools/knowledge_graph_builder.py

CLI: --vault PATH, --inbox-only, --notes-only, --miro XML, --drawio XML,
     --xml XML, --output DIR, --dry-run, --no-miro-export, --mark-processed
When --vault: read raw/ → enrich() → build_graph() → export_to_vault()
Save tools/graph.json. Optional reports/miro_enriched.xml.

### tools/enrich_tag.py

ENRICHMENT_MARKER = "<!-- llm-enriched -->"
TAG_PATTERN = re.compile(r"(?:^|\s)#llm\b", re.MULTILINE)
CLI: --vault PATH, --folder inbox|notes|articles, --file PATH, --dry-run, --force

_extract_topics(text): title > capitalized noun pairs > hashtags > first sentence
_build_enrichment(text, filename) -> dict | None
  Claude + web_search tool (web_search_20250305)
  Returns {summary, key_insights[3], references[3-5: title+url+relevance],
           related_concepts[3]}
_inject_enrichment(original, enrichment, today_str) -> str
  NEVER modify original — only append
  Add enriched: date to frontmatter
  Append block with <!-- llm-enriched --> marker
enrich_tagged_files(vault, folders=None, dry_run=False) -> {found, enriched, skipped}

### tools/daily.py

CLI: --vault PATH, --date YYYY-MM-DD, --no-calendar, --no-slack
fetch_calendar(date_str) → Google Calendar MCP
  mcp_servers=[{"type":"url","url":"https://calendarmcp.googleapis.com/mcp/v1"}]
count_unprocessed(folder) → .md files without "processed:"
read_gaps(path) → gap names from graph-report.md
read_carry_forward(daily_dir, today_str) → unchecked todos last 7 days, deduplicated
read_manual_todos(vault, today_str) → unchecked items from raw/todos/YYYY-MM-DD.md
  Strips inline HTML comments. Returns [{text, source:"manual"}]
enrich_events(events, wiki_dir) → add wiki_pages[] per event
wiki_pulse(wiki_dir, today) → pages updated this week
fetch_slack_todos(vault, date_str) → read raw/slack/ JSON sidecars
build_todos(..., slack_todos=None, manual_todos=None) → scored/ranked list
  Manual todos: score=3, tier=must, source=manual (inserted first)
  Scores: meeting+3, carried3+d+2, Slack≥3+2, Slack2+1, gap+1, inbox>5+1
render_briefing(..., manual_todos=None) → markdown
  ## Todo block: ### Planned (manual, `Manual` badge) then Must/Should/If-time
  Focus line includes "N planned tasks for today" if manual todos present
  ## From Slack omitted if empty
Save to reports/daily/YYYY-MM-DD.md

### tools/weekly.py

CLI: --vault PATH, --week YYYY-WNN, --no-slack
Parse daily reports: total/completed/incomplete, blockers (2+ days)
Completion bar: ■■■■░░░░░░ 40% (10 chars, filled=■ empty=░)
Slack stats from raw/slack/ sidecars
Save to reports/weekly/YYYY-WNN.md with ## Slack Activity section

### tools/discover.py

CLI: --vault PATH, --dry-run, --max-bridges 3
load_wiki_pages(wiki_dir) → [{id,path,type,title,cluster,confidence,
                              tags,links,words(set),body[:1500],fm}]
find_bridge_connections(pages, max_results=3):
  Tags signal: shared meaningful tags (skip: knowledge-graph,concept,person,tool,moc)
               score += len(shared)*2
  Co-citation: both linked from same 3rd page → score += count*3
  Word overlap: ≥8 meaningful words shared → score += 1
  Same cluster → score += 2. Include if score ≥ 4.
  Guess rel: unlike/contrast→contrasts_with, requires→depends_on,
             leads to→leads_to, part of→part_of, default→relates_to
find_missing_person_pages(pages, wiki_dir) → proper nouns 2+ times, no people/ page
find_implicit_sequences(pages, max_results=2) → A→B→C where A doesn't link C
find_anomaly(pages) → hub/island/orphan string
Save to reports/discoveries/YYYY-MM-DD.md

### tools/review.py

CLI: --vault PATH, --dry-run, --auto
Thresholds: HIGH_TO_MEDIUM=90d MEDIUM_STALE=180d STUB_ABANDONED=30d STUB_WORDS=150
Auto-downgrade high→medium: update confidence frontmatter, update updated: date,
  add > [!warning] Confidence downgraded — N days. Re-verify.
Interactive stale+stubs (skip if --auto): (k)eep/(d)elete/(s)kip
  keep → update updated: date to today
Ensure wiki/meta/conflicts.md exists
Save to reports/review/YYYY-MM-DD.md

### tools/slack_ingest.py

CLI: --vault PATH, --hours N, --since YYYY-MM-DD, --channels IDs, --dry-run
Requires SLACK_BOT_TOKEN. Without token: Cowork MCP writes same sidecars.
Scoring: +2 action patterns / +2 @self / +1 @anyone / +1 ends? / -1 <4 words
Score ≥2 → action item
save_results → raw/slack/YYYY-MM-DD/<channel>/digest.md + data.json
fetch_slack_todos(vault, date_str) → action items for daily.py
fetch_slack_weekly_stats(vault, mon, today) → aggregate for weekly.py

### tools/slack_channels.py

CLI: list | add <id_or_name> | remove <id_or_name> | search <query>
Reads/writes SLACK_CHANNEL_IDS in tools/.env, preserving all other lines.
Without SLACK_BOT_TOKEN: add requires ID format, search unavailable.

---

## SECTION 5: SHELL SCRIPTS

All .sh scripts:
  SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
  VAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
  source "$VAULT/tools/.venv/bin/activate"
Use ASCII status labels (OK WARN ERR) not emoji.

### tools/check-notes.sh — CRITICAL

Flags: (none)=notes, --inbox=inbox, --all=both
For each .md file in target folder:
  - No processed: → [NEW]
  - #llm-reprocess in body → [FORCE]
  - mtime > processed date → [MODIFIED]
    Mac: stat -f '%Sm' -t '%Y-%m-%d'
    Linux: stat -c '%y' | cut -d' ' -f1
  - New content after last --- not LLM Enrichment → [MODIFIED]
  - Else → [OK]
Output format:
  === Note processing scan ===
    [NEW]      reason
                 filepath
    [MODIFIED] reason
                 filepath
    [FORCE]    reason
                 filepath
  === Summary ===
    Need processing: N (new: N, modified: N, forced: N)
    Up to date: N
If nothing to process: show re-process guidance.

### tools/setup.sh

Check Python 3.10+ / Claude Code / create .venv / pip install / check API key
Print all available commands.

### tools/build-graph.sh

knowledge_graph_builder.py --vault $VAULT $@

### tools/watch-inbox.sh

Watch raw/inbox/ (fswatch Mac / Python watchdog fallback)
On new file: sleep 3 → knowledge_graph_builder.py --vault --inbox-only --mark-processed
Also: enrich_tag.py --vault $VAULT --folder inbox
Log to tools/watch.log

### tools/schedule.sh

Subcommands: install | remove | status | run-now
Mac: launchd ~/Library/LaunchAgents/com.llm-wiki.build.plist
Linux: crontab
Frequencies: 30min / 1hr / 6hr / daily 9am / daily midnight

### tools/run-enrich.sh

enrich_tag.py --vault $VAULT $@
Flags: --folder inbox|notes|articles, --dry-run, --force, --file PATH

---

## SECTION 6: SKILL FILES

Each .claude/skills/*.md must be complete standalone instructions.

### process-inbox.md — CRITICAL

Triggers: process inbox / process notes / process all / enrich
MANDATORY FIRST STEP: run bash tools/check-notes.sh [--inbox|--all]
Process only [NEW]/[MODIFIED]/[FORCE] files from output.
If nothing to process: show guidance, never just say "nothing to process".
#llm enrichment BEFORE wikification.
Re-processing [MODIFIED]: update wiki pages, don't duplicate.
Force re-process: echo "#llm-reprocess" >> raw/notes/note.md

### enrich-tag.md

#llm detection, topic extraction, web search enrichment,
inline injection format, <!-- llm-enriched --> marker, --force flag.

### daily.md

Sources: Slack MCP first → Calendar MCP → raw/todos/ → inbox → gaps → carry-forward
Manual todos (raw/todos/YYYY-MM-DD.md) → ## Planned section, score 3, `Manual` badge.
Scoring table. Output with ## From Slack (omit if empty).
bash tools/run-daily.sh [--no-slack] [--no-calendar]

### All other skills (ingest-url / lint-wiki / build-graph / eod / weekly /
### smart-index / discover / mindmap / conflicts / review / onepager / slides /
### slack-ingest / slack-channels)

Complete step-by-step per CLAUDE.md specifications.

---

## SECTION 7: SUPPORTING FILES

### tools/.env

# LLM Wiki Vault — environment variables
# NOT committed to git.
ANTHROPIC_API_KEY=sk-ant-REPLACE_WITH_YOUR_KEY
SLACK_BOT_TOKEN=
SLACK_CHANNEL_IDS=REPLACE_WITH_CHANNEL_ID
SLACK_LOOKBACK_HOURS=24
SLACK_MY_USER_ID=REPLACE_WITH_YOUR_ID

### .gitignore

tools/.venv/
tools/__pycache__/
tools/scripts/__pycache__/
*.pyc *.pyo
tools/.env
tools/graph.json
tools/output/
tools/watch.log

### wiki/meta/index.md

Live dashboard. Sections: intro | Domains table | By type |
Recently updated | Open gaps | Navigation

### wiki/meta/graph-report.md, conflicts.md

Placeholders — instructions to run build-graph or conflicts.

### reports/README.md

Table: all report types with file patterns and generating commands.

### HELP.md

Sections: Setup | Daily habit table | ALL Claude Code commands |
Bash scripts + flags | File locations | Re-processing guide |
check-notes.sh usage | Cadence | Auth notes | BUILD_PROMPT.md usage

### BUILD_PROMPT.md

This file. Kept current by CLAUDE.md auto-update instructions.

---

## SECTION 8: PORTABILITY

- Packages → tools/.venv/ only
- Zip excludes: tools/.venv/ tools/output/ tools/graph.json __pycache__ *.pyc
- All secrets → dummy values in templates
- No hardcoded paths — VAULT= relative detection in all scripts
- Move to new machine: copy folder → bash tools/setup.sh → edit tools/.env

---

## SECTION 9: DELIVERABLE

Provide llm-wiki-vault.zip. Every file fully written — no stubs.

Confirm when done:
  Total files: N
  Python tools: N (fully functional)
  Skill files: 17
  Shell scripts: N
  Key features: knowledge graph, #llm inline enrichment, check-notes.sh
                change detection, Slack integration, daily planning,
                organised reports/ subdirs, auto-updated BUILD_PROMPT.md
  Setup: bash tools/setup.sh && edit tools/.env
