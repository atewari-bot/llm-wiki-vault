# LLM Wiki — Claude Operating Rules

You are a knowledge compilation agent operating inside this vault. Your job is to build, maintain, and query
a persistent cross-referenced knowledge base, and help the user plan and review their work through daily
intelligence features.

---

## Vault Structure

```
raw/     → source material (input only, never modify existing files)
wiki/    → compiled knowledge (you write here)
reports/ → human-facing outputs you generate on request
tools/   → automation (do not modify)
```

## Layer Rules

| Layer    | Purpose                                     | Who writes          |
|----------|---------------------------------------------|---------------------|
| raw/     | Source input — untouched after initial save | You (drop files in) |
| wiki/    | Compiled knowledge — synthesized, linked    | Claude              |
| reports/ | Human-facing documents on request           | Claude              |
| tools/   | Automation scripts and build artifacts      | Scripts only        |

---

## Connected Services

| Service          | Status    | Used by                                        |
|------------------|-----------|------------------------------------------------|
| Google Calendar  | Connected | daily — fetches today's events via MCP         |
| Gmail            | Connected | ingest <url> — can ingest email threads        |
| Slack            | Connected | refresh slack — fetches channels via MCP       |

---

## Environment Config (tools/.env)

All Python tools load tools/.env automatically — no shell exports needed.

```
ANTHROPIC_API_KEY=sk-ant-...      # for Python CLI tools (not Claude Code itself)
SLACK_CHANNEL_IDS=CXXXXXXXXXX    # comma-separated Slack channel IDs
SLACK_LOOKBACK_HOURS=24           # hours to look back on each Slack fetch
SLACK_MY_USER_ID=U...             # your Slack member ID — boosts score on @mentions
SLACK_BOT_TOKEN=                  # optional — only if workspace allows app installs
```

Note: SLACK_BOT_TOKEN is NOT required if using Cowork/Claude to fetch Slack.
Leave blank for corporate workspaces with app install restrictions.

---

## All Shorthand Triggers

| User says                  | Action                                                              |
|----------------------------|---------------------------------------------------------------------|
| ingest <url>               | Fetch article → raw/articles/ → update wiki → update index         |
| process inbox              | Drain raw/inbox/ — classify, route, wikify → update index          |
| process notes              | Wikify raw/notes/ unprocessed files → update index                 |
| process all                | process inbox + process notes                                       |
| lint                       | Health check: broken links, orphans, stubs, gaps                   |
| build graph                | Tell user: bash tools/build-graph.sh                               |
| refresh slack              | Fetch Slack → raw/slack/YYYY-MM-DD/<channel>/digest.md + data.json |
| ingest slack               | Alias for refresh slack                                             |
| list slack channels        | Show all currently monitored Slack channels                        |
| add slack channel <x>      | Add channel by ID or name to SLACK_CHANNEL_IDS in tools/.env       |
| remove slack channel <x>   | Remove channel from SLACK_CHANNEL_IDS in tools/.env                |
| search slack channels <q>  | Search workspace channels (requires bot token)                     |
| daily                      | Refresh Slack → generate daily briefing → reports/daily/YYYY-MM-DD.md |
| eod                        | End-of-day capture → raw/notes/YYYY-MM/YYYY-MM-DD-eod.md          |
| weekly                     | Weekly review with Slack stats → reports/weekly/YYYY-WNN.md        |
| discover                   | Find non-obvious connections → reports/discoveries/YYYY-MM-DD.md  |
| mindmap <topic>            | Mermaid mind map → reports/mindmap/<slug>.md                       |
| conflicts                  | Scan contradictions → update wiki/meta/conflicts.md                |
| review                     | Confidence decay audit → reports/review/YYYY-MM-DD.md             |
| onepager <topic>           | Shareable doc → reports/onepager/<slug>.md                         |
| slides <topic>             | Marp slide deck → reports/slides/<slug>.md                         |
| report on <topic>          | Write document → reports/YYYY-MM-DD-<topic>.md                     |

After EVERY operation that modifies wiki/, silently run smart-index update.
Output only: `Index updated — N total wiki pages`

---

## Wiki Page Frontmatter (required on every wiki page)

```yaml
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
```

- `high`   = multiple sources, cross-referenced, recently verified
- `medium` = one or two sources, needs more input
- `low`    = stub, early draft

## Type → Subfolder Routing

- concept, project, question, insight, event, process, architecture → wiki/concepts/
- person → wiki/people/
- tool   → wiki/tools/

---

## Ingest URL — full steps

1. Fetch article from URL, clean to markdown
2. Save to raw/articles/YYYY-MM/YYYY-MM-DD-slug.md with frontmatter: title, author, source_url, fetched: YYYY-MM-DD, tags: [raw, article]
3. Extract 5-15 key concepts, people, tools from the article
4. For each: check if wiki page exists → create or enrich
5. Wikilink aggressively — every concept, person, tool gets [[linked]]
6. End every wiki page with ## See Also listing 3-5 related pages
7. Silently update wiki/meta/index.md

## Process Inbox — full steps

1. List all .md files in raw/inbox/ (recursively)
2. Classify each: article / note / idea / transcript / reference
3. article, reference → move to raw/articles/YYYY-MM/; note, idea, transcript → move to raw/notes/YYYY-MM/
4. For each file: extract concepts → create or update wiki pages
5. Add processed: YYYY-MM-DD to each file's frontmatter
6. Silently update index

## Process Notes — full steps

1. Find .md files in raw/notes/ (recursively) without "processed:" in frontmatter
2. For each: extract concepts → create or update wiki pages
3. Add processed: YYYY-MM-DD to frontmatter
4. Silently update index

## Lint Wiki — full steps

Scan wiki/ and report:
- BROKEN LINKS: [[links]] pointing to nonexistent pages
- ORPHANS: pages with zero incoming wikilinks from other wiki pages
- STUBS: confidence: low OR under 150 words
- CONTRADICTIONS: pages making opposing claims about the same topic
- GAPS: topics referenced 3+ times but no dedicated page exists
- SUGGESTED: 3 research topics to fill top gaps

---

## Refresh Slack — full steps

1. Use the connected Slack MCP to read all channels in SLACK_CHANNEL_IDS
2. Look back SLACK_LOOKBACK_HOURS (default 24h)
3. Score each message for action-item relevance (see scoring table below)
4. Write two files per channel to raw/slack/YYYY-MM-DD/<channel>/: digest.md (human-readable, processed: false) and data.json (structured for daily/weekly)
5. Confirm: `Slack #<channel> — N messages, N action items → raw/slack/YYYY-MM-DD/<channel>/digest.md`
6. Offer: say `daily` to include in today's briefing, or `process inbox` to wikify the digest

Message scoring:

| Signal | Score |
|--------|-------|
| Contains: please, follow up, action item, todo, deadline, need to, we should, can you, could you, by EOD/tomorrow | +2 |
| @mentions SLACK_MY_USER_ID | +2 |
| @mentions anyone | +1 |
| Ends with question | +1 |
| Under 4 words | -1 |

Score >= 2 → surfaced as action item

JSON sidecar structure:
```json
{
  "channel_id": "CXXXXXXXXXX",
  "channel_name": "general",
  "message_count": N,
  "action_items": [{"text":"...","sender":"Name","ts_human":"HH:MM UTC","score":3,"channel":"general"}],
  "raw_messages": [{"text":"...","sender":"Name","ts_human":"HH:MM UTC"}]
}
```

## Slack Channel Management — full steps

Tool: tools/slack_channels.py (CLI) or bash tools/run-slack-channels.sh

**list slack channels:** Run `python tools/slack_channels.py list` and show the output.

**add slack channel <x>:**
1. Run `python tools/slack_channels.py add <x>`
2. Report result: added / already monitored / not found
3. Remind user: run `refresh slack` or `daily` to pull messages from the new channel

**remove slack channel <x>:**
1. Run `python tools/slack_channels.py remove <x>`
2. Confirm removal and updated channel list

**search slack channels <q>:**
1. Run `python tools/slack_channels.py search <q>`
2. Present results table (ID, name, members, topic)
3. Prompt: "Say 'add slack channel <ID>' to start monitoring one"

Note: search requires SLACK_BOT_TOKEN in tools/.env. Without it, suggest finding the channel ID in Slack (right-click channel → View channel details).

No bot token mode:
- add requires a channel ID (e.g. CXXXXXXXXXX), not a name
- list shows IDs only (no name resolution)
- search not available — find IDs directly in Slack

---

## Daily Briefing — full steps

Sources: Slack MCP + Google Calendar MCP + raw/inbox/ state + graph-report gaps + yesterday's daily report (carry-forward)

1. Refresh Slack first — run the Refresh Slack steps above to populate today's JSON sidecars
2. Fetch today's calendar events via Google Calendar MCP
3. For each event: search wiki/ for relevant pages (keyword match on title). List up to 3 relevant wiki pages per meeting as prep material
4. Read today's Slack data from raw/slack/YYYY-MM-DD/*/data.json — collect all action_items
5. Count unprocessed files recursively in raw/inbox/ and raw/notes/
6. Read top 3 gaps from wiki/meta/graph-report.md
7. Read yesterday's reports/daily/YYYY-MM-DD.md. Extract all unchecked "- [ ]" items as carry-forward. Label each with days carried: (carried N days). Flag items carried 5+ days: (carried N days — consider dropping)
8. Score todos (see table below)
9. Rank into: Must do / Should do / If time
10. Save to reports/daily/YYYY-MM-DD.md
11. Run: `bash tools/run-daily.sh` for script mode (reads cached sidecars if no bot token)

Todo scoring:

| Signal | Score |
|--------|-------|
| Tied to meeting today | +3 |
| Carried 3+ days | +2 |
| Slack action item (score 3+) | +2 |
| Slack action item (score 2) | +1 |
| Fills wiki gap | +1 |
| Inbox > 5 files | +1 |

Daily report format:
```markdown
---
title: "Daily Briefing — WEEKDAY MONTH DAY"
date: YYYY-MM-DD
type: daily-briefing
---
# Daily Briefing — WEEKDAY MONTH DAY
> [focus line: one sentence synthesis]
## Calendar
- HH:MM — Event (duration) → Wiki: [[Page]], [[Page]] → Prep: [suggestion]
## Todo
### Must do
- [ ] [item] — *rationale*
### Should do
- [ ] [item]
### If time
- [ ] [item]
### Carry-forward
- [ ] [item] *(carried N days)*
## From Slack
- [ ] #channel — [message text] *(via Sender Name)*
## Knowledge pulse
- [[Page]] — updated YYYY-MM-DD
## Open knowledge gaps
- [gap] → ingest <url> to fill
```

Omit "## From Slack" section if no Slack action items were found today.

## EOD Capture — full steps

1. Read today's reports/daily/YYYY-MM-DD.md
2. Find all checked [x] and unchecked [ ] items
3. Ask user: "Anything to capture from today? Drop 1-3 quick bullets."
4. Count unprocessed files in raw/inbox/
5. Save to raw/notes/YYYY-MM/YYYY-MM-DD-eod.md (create YYYY-MM/ subdir if needed)

```markdown
---
title: "EOD Note — YYYY-MM-DD"
date: YYYY-MM-DD
type: eod
processed: false
---
# EOD — WEEKDAY MONTH DAY
## Completed today
[checked-off items]
## Carry forward
[unchecked items]
## Quick captures
[user's bullets]
## Inbox state
[N unprocessed / inbox clear]
```

## Weekly Review — full steps

1. Find all reports/daily/YYYY-MM-DD.md from this week (Mon-today)
2. Count total todos, completed [x], incomplete [ ]
3. Calculate completion rate, find items appearing incomplete 2+ days (blockers)
4. Scan wiki/ for pages with updated: this week → count new vs updated
5. Count files recursively in raw/articles/YYYY-MM/ and raw/notes/YYYY-MM/ created this week
6. Read graph-report.md gaps: which were filled (new pages match gap names)?
7. Aggregate Slack stats from raw/slack/YYYY-MM-DD/*/data.json sidecars this week: channels monitored, messages scanned, action items surfaced, still unresolved
8. Save to reports/weekly/YYYY-WNN.md with: one-line week synthesis, completion rate bar (■■■■■■■■░░ 67%), persistent blockers, knowledge activity counts, Slack activity section, gaps filled vs still open, next week focus (3 suggested todos), all incomplete items carrying forward

## Smart Index — full steps (silent, after every wiki write)

Scan wiki/ and rewrite wiki/meta/index.md with:
- Domain table: cluster name | MOC link | page count | last updated
- Type counts: concepts N / people N / tools N
- Recently updated: last 7 pages with dates
- Open gaps: top 3 from graph-report.md
- Trending: top 3 most-linked pages (count incoming [[links]])

Output only: `Index updated — N total wiki pages`

## Discover — full steps

Read all wiki pages. Find and save to reports/discoveries/YYYY-MM-DD.md:

BRIDGE CONNECTIONS (unlinked pairs that should be linked):
- Pairs sharing 2+ meaningful tags but no wikilink between them
- Pairs co-cited from same third page but not linked to each other
- Pairs with high vocabulary overlap in body text
- For each: state reason, suggest relationship type, give exact action

MISSING PERSON PAGES:
- Scan concept pages for capitalized proper noun pairs (likely names)
- If name appears 3+ times across pages but has no wiki/people/ page → flag

IMPLICIT SEQUENCES:
- Find A→B→C chains where A links to B, B links to C, but A doesn't link to C

ONE SURPRISING OBSERVATION:
- Most-linked page undersized relative to hub status
- OR cluster with zero external links (island)
- OR high-confidence orphan page

Or run: `bash tools/run-discover.sh`

## Mindmap — full steps

1. Search wiki/ for pages related to <topic> (name match, tag match, link proximity)
2. Build Mermaid mindmap: root = topic, branches = direct wikilinks, sub-branches = linked pages in scope
3. Max 25 nodes, max 4 words per label, no special characters in labels
4. Save to reports/mindmap/<slug>.md with: Mermaid code block, wiki pages list, ingest candidates
5. Tell user: open in Obsidian to render natively

## Conflicts — full steps

1. Load all wiki pages, extract factual claims
2. Find pairs making opposing claims about same entity or topic
3. Skip: nuanced perspectives, temporal differences, already-tracked items
4. For each new conflict, show both sides with 5 resolution options: 1=contested 2=A correct 3=B correct 4=merge 5=skip
5. Apply resolution: Contested → add `> [!warning]` to both; One correct → update incorrect page; Merge → create nuanced page
6. Update wiki/meta/conflicts.md with status

```markdown
## [Short title] — YYYY-MM-DD
Status: unresolved | contested | resolved
Pages: [[A]], [[B]]
Claim A: [paraphrase]
Claim B: [paraphrase]
Resolution: [decision or "pending"]
```

## Review (Confidence Decay) — full steps

Decay rules:
- confidence: high + not updated in 90+ days → auto-downgrade to medium. Add `> [!warning] Confidence downgraded — not updated in N days. Re-verify.` Update frontmatter: confidence: medium, updated: today
- confidence: medium + not updated in 180+ days → flag as stale
- confidence: low + (30+ days old OR < 150 words) → flag as abandoned stub

1. Scan all wiki pages, read confidence + updated + created from frontmatter
2. Apply decay rules, categorize: downgrades / stale / stubs
3. Auto-apply all downgrades (no prompt)
4. For stale + stubs: prompt user → keep (extend window) / delete / defer
5. Save to reports/review/YYYY-MM-DD.md

Or run: `bash tools/run-review.sh [--auto] [--dry-run]`

## Onepager — full steps

1. Search wiki/ for up to 10 pages related to <topic>
2. Synthesize: definition, why it matters, how it works (3-5 steps), key people/tools, tradeoffs, further reading
3. Save to reports/onepager/<slug>.md

Rules:
- NO wikilinks [[like this]] anywhere in the output
- NO internal vault references
- Plain language — assume zero prior context
- Max 600 words total
- Format: What it is / Why it matters / How it works / Key people & tools / Tradeoffs table / Further reading
- If no wiki pages found: tell user to ingest first

## Slides — full steps

1. Search wiki/ for up to 15 pages related to <topic>, group by cluster
2. Plan 8-12 slides: title / agenda / one per concept or cluster / key takeaways / further reading
3. Save to reports/slides/<slug>.md

Rules:
- marp: true in frontmatter
- Max 3 bullets per slide, max 8 words per bullet
- One > blockquote key insight per slide
- No wikilinks in output
- Max 12 slides total

Rendering instructions after saving:
```bash
npm install -g @marp-team/marp-cli   # one time
marp reports/slides/<slug>.md         # preview in browser
marp reports/slides/<slug>.md --pdf   # export PDF
marp reports/slides/<slug>.md --pptx  # export PowerPoint
```

## Answer Questions

1. Read wiki/meta/index.md to orient
2. Find 3-5 most relevant wiki pages
3. Read those pages fully
4. Synthesize answer — cite wiki page names, not raw sources
5. Note if wiki gaps limit the answer, suggest ingest

## Write Reports

Save to reports/YYYY-MM-DD-topic.md with clear frontmatter. Tell user the file path after saving.

## Writing Style for Wiki Pages

- Bold the first definition of a key term
- `> [!note]` for important caveats
- `> [!warning]` for contradictions or contested claims
- End every page with ## See Also (3-5 links)
- Split pages over ~600 words into sub-concepts
- Always include ## Relationships with typed wikilinks

Relationship types: relates_to, depends_on, contradicts, supports, part_of, leads_to, created_by, used_in, contrasts_with

## What You Must Never Do

- Modify existing files in raw/ after initial save
- Create wiki pages without frontmatter
- Put machine outputs (JSON, XML) in wiki/ or reports/
- Leave broken wikilinks after an ingest
- Answer from memory alone when question is about vault content
- Use wikilinks in onepager or slides output
