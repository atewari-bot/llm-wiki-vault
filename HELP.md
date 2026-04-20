# LLM Wiki Vault — Quick Reference

## Setup
```bash
bash tools/setup.sh          # one-time setup (Mac/Linux)
cd llm-wiki-vault && claude  # start Claude Code
```

## Daily habit
| Time | Command | What happens |
|------|---------|-------------|
| Morning | `daily` | Slack + Calendar + todos → reports/daily/YYYY-MM-DD.md |
| During day | `ingest https://...` | Article → wiki pages |
| During day | `process inbox` | Classify + wikify raw/inbox/ |
| During day | `process notes` | Wikify raw/notes/ |
| Evening | `eod` | Check completions, capture bullets |
| Friday | `weekly` | Week summary → reports/weekly/YYYY-WNN.md |

## All Claude Code commands
| Say | Action |
|-----|--------|
| `ingest <url>` | Fetch article → wiki |
| `process inbox` | Drain raw/inbox/ |
| `process notes` | Wikify raw/notes/ |
| `process all` | Both inbox + notes |
| `lint` | Wiki health check |
| `build graph` | Run bash tools/build-graph.sh |
| `refresh slack` | Fetch Slack → raw/slack/ sidecars |
| `list slack channels` | Show monitored channels |
| `add slack channel <x>` | Add channel by ID or name |
| `remove slack channel <x>` | Remove channel |
| `search slack channels <q>` | Find channels (needs bot token) |
| `daily` | Morning briefing with Slack + Calendar |
| `eod` | End-of-day capture |
| `weekly` | Weekly review |
| `discover` | Find hidden connections |
| `mindmap <topic>` | Mermaid mindmap → reports/mindmap/ |
| `conflicts` | Scan contradictions |
| `review` | Confidence decay audit |
| `onepager <topic>` | Shareable doc → reports/onepager/ |
| `slides <topic>` | Marp deck → reports/slides/ |
| `report on <topic>` | Write document → reports/ |

## Script commands
```bash
bash tools/build-graph.sh              # all of raw/ → wiki/
bash tools/build-graph.sh --inbox-only # inbox only
bash tools/build-graph.sh --dry-run    # preview
bash tools/run-daily.sh                # daily briefing (script mode)
bash tools/run-daily.sh --no-slack     # skip Slack
bash tools/run-daily.sh --no-calendar  # offline
bash tools/run-weekly.sh               # weekly review
bash tools/run-discover.sh             # serendipity engine
bash tools/run-review.sh               # confidence decay review
bash tools/run-review.sh --auto        # no prompts
bash tools/run-slack-ingest.sh         # fetch Slack (needs bot token)
bash tools/run-slack-ingest.sh --hours 48
bash tools/run-slack-channels.sh list  # list channels
bash tools/run-slack-channels.sh add CXXXXXXXXXX
bash tools/watch-inbox.sh              # auto-ingest on file drop
bash tools/schedule.sh install         # periodic background builds
bash tools/schedule.sh status          # check schedule + logs
```

## File locations
| What | Where |
|------|-------|
| Drop anything | raw/inbox/ |
| Web articles | raw/articles/YYYY-MM/ |
| Notes/transcripts | raw/notes/YYYY-MM/ |
| Slack digests | raw/slack/YYYY-MM-DD/<channel>/ |
| Wiki pages | wiki/concepts/ people/ tools/ |
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
| `refresh slack` | Daily (auto via `daily`) |

## Auth notes
- Claude Code → uses your claude.ai login (no API key needed)
- Python tools → use ANTHROPIC_API_KEY from tools/.env
- Do NOT export ANTHROPIC_API_KEY in same terminal as `claude`
- Slack → SLACK_BOT_TOKEN optional (use Cowork MCP if restricted)
