# LLM Wiki Vault

An AI-powered personal knowledge base with Slack integration, daily planning, knowledge graph, discovery, and presentation features.

---

## Directory Structure

```
llm-wiki-vault/
├── raw/                    ← source material (input only)
│   ├── inbox/              ← drop zone for new content
│   ├── articles/YYYY-MM/   ← ingested web articles
│   ├── notes/YYYY-MM/      ← fleeting notes, EOD captures
│   └── slack/YYYY-MM-DD/   ← Slack channel digests + JSON sidecars
│       └── <channel>/
│           ├── digest.md   ← human-readable digest
│           └── data.json   ← structured todos for daily/weekly
│
├── wiki/                   ← compiled knowledge (Claude writes here)
│   ├── concepts/
│   ├── people/
│   ├── tools/
│   └── meta/
│       ├── index.md          ← live dashboard (auto-updated)
│       ├── graph-report.md   ← knowledge gaps
│       └── conflicts.md      ← contradiction tracker
│
├── reports/                ← documents Claude generates for you
│   ├── daily/              ← YYYY-MM-DD.md
│   ├── weekly/             ← YYYY-WNN.md
│   ├── onepager/           ← <slug>.md
│   ├── slides/             ← <slug>.md
│   ├── mindmap/            ← <slug>.md
│   ├── discoveries/        ← YYYY-MM-DD.md
│   └── review/             ← YYYY-MM-DD.md
│
└── tools/
    ├── .env                ← secrets (not committed to git)
    ├── setup.sh / setup.ps1
    ├── daily.py / weekly.py / discover.py / review.py
    ├── slack_ingest.py     ← Slack ingestion
    ├── slack_channels.py   ← channel manager
    ├── knowledge_graph_builder.py
    └── scripts/
```

---

## Setup (one time)

**Mac / Linux**
```bash
bash tools/setup.sh
```

**Windows**
```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

**Then edit tools/.env:**
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
SLACK_CHANNEL_IDS=CXXXXXXXXXX
SLACK_MY_USER_ID=U...
```

**Prerequisites:** Python 3.10+, Claude Code (`npm install -g @anthropic-ai/claude-code`)

---

## Daily Workflow

```bash
cd llm-wiki-vault && claude
```

Say `daily` each morning — Claude refreshes Slack, pulls your calendar, and generates a prioritised todo saved to `reports/daily/YYYY-MM-DD.md`.

See `HELP.md` for the full command reference.

---

## Slack Integration

**Without a bot token (corporate workspaces):**
1. Open Cowork → say `refresh slack`
2. Claude fetches via connected Slack MCP, writes raw/slack/ sidecars
3. Say `daily` — action items appear in your briefing automatically

**With a bot token:**
```bash
# Add to tools/.env: SLACK_BOT_TOKEN=xoxb-...
bash tools/run-slack-ingest.sh    # fetch now
bash tools/run-slack-channels.sh list   # manage channels
```

---

## Auth Notes

- **Claude Code** uses your claude.ai login — no API key export needed
- **Python tools** use ANTHROPIC_API_KEY from tools/.env — not from shell env
- **Do NOT** export ANTHROPIC_API_KEY in the same terminal you run `claude`

---

## Portability

Everything lives in this folder. To move to a new machine:
1. Copy/clone the folder
2. Run `bash tools/setup.sh`
3. Edit `tools/.env` with your keys
