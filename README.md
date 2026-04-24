# LLM Wiki Vault

An AI-powered personal knowledge base with daily planning, knowledge graph, discovery, and presentation features.

---

## Directory Structure

```
llm-wiki-vault/
├── raw/                        ← source material (input only)
│   ├── notes/YYYY-MM/          ← fleeting notes, EOD captures, ingested articles
│   └── todos/YYYY-MM-DD.md     ← manually planned tasks per day
│
├── wiki/                       ← compiled knowledge (Claude writes here)
│   ├── concepts/
│   ├── tools/                  ← wiki pages about software/frameworks
│   └── meta/
│       ├── index.md            ← live dashboard (auto-updated)
│       ├── graph-report.md     ← knowledge gaps
│       └── conflicts.md        ← contradiction tracker
│
├── reports/                    ← documents Claude generates for you
│   ├── daily/                  ← YYYY-MM-DD.md
│   ├── weekly/                 ← YYYY-WNN.md
│   ├── onepager/               ← <slug>.md
│   ├── slides/                 ← <slug>.md
│   ├── mindmap/                ← <slug>.md
│   ├── discoveries/            ← YYYY-MM-DD.md
│   └── review/                 ← YYYY-MM-DD.md
│
└── .tools/                     ← automation (do not modify by hand)
    ├── .env                    ← secrets (not committed to git)
    ├── setup.sh
    ├── daily.py / weekly.py / discover.py / review.py / eod.py
    ├── gcal.py / gcal_auth.py  ← Google Calendar headless integration
    ├── knowledge_graph_builder.py
    └── scripts/
```

---

## Setup (one time)

**Mac / Linux**
```bash
bash .tools/setup.sh
```

**Then edit .tools/.env:**
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Prerequisites:** Python 3.10+, Claude Code (`npm install -g @anthropic-ai/claude-code`)

**Optional headless integrations:**
```bash
bash .tools/run-gcal-auth.sh             # Google Calendar OAuth
bash .tools/schedule.sh install          # daily briefing at 8am
bash .tools/schedule-discover.sh install # discovery at 6am
bash .tools/schedule-mindmap.sh install  # mindmap at 7am
bash .tools/schedule-eod.sh install      # EOD capture at 6pm
```

---

## Daily Workflow

```bash
cd llm-wiki-vault && claude
```

Say `daily` each morning — Claude pulls your calendar and generates a prioritised todo saved to `reports/daily/YYYY-MM-DD.md`.

See `HELP.md` for the full command reference.

---

## Auth Notes

- **Claude Code** uses your claude.ai login — no API key export needed
- **Python tools** use ANTHROPIC_API_KEY from `.tools/.env` — not from shell env
- **Do NOT** export ANTHROPIC_API_KEY in the same terminal you run `claude`

---

## Portability

Everything lives in this folder. To move to a new machine:
1. Copy/clone the folder
2. Run `bash .tools/setup.sh`
3. Edit `.tools/.env` with your keys
