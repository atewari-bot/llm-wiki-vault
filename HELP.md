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

## Bash scripts
```bash
bash .tools/build-graph.sh              # all of raw/ → wiki/
bash .tools/build-graph.sh --dry-run    # preview
bash .tools/run-daily.sh                # daily briefing (headless)
bash .tools/run-daily.sh --no-calendar  # offline
bash .tools/run-weekly.sh               # weekly review
bash .tools/run-eod.sh                  # headless EOD capture
bash .tools/run-discover.sh             # serendipity engine
bash .tools/run-review.sh               # confidence decay review
bash .tools/run-review.sh --auto        # no prompts
bash .tools/run-gcal-auth.sh            # Google Calendar OAuth flow
bash .tools/schedule.sh install         # daily @ 8am
bash .tools/schedule.sh status          # check schedule + logs
bash .tools/schedule-discover.sh install   # 6am
bash .tools/schedule-mindmap.sh install    # 7am
bash .tools/schedule-eod.sh install        # 6pm
```

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
