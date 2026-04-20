# Skill: Slack ingestion — refresh slack / ingest slack

## Triggers
- "refresh slack" or "ingest slack" or "pull slack" or "fetch slack" or "check slack"

---

## What This Does

Fetches messages from your monitored Slack channels and saves two files per channel:
- `raw/slack/YYYY-MM-DD/<channel>/digest.md` — human-readable digest (processed: false)
- `raw/slack/YYYY-MM-DD/<channel>/data.json` — structured data for daily.py/weekly.py

Action items are scored and surfaced. The `daily` command reads these sidecars automatically.

---

## Step 1 — Fetch via Cowork (no bot token needed)

Use the connected Slack MCP to read the configured channels (from SLACK_CHANNEL_IDS in tools/.env).
Look back 24 hours by default (SLACK_LOOKBACK_HOURS).

For each message, apply scoring:

| Signal | Score |
|--------|-------|
| Contains: please, follow up, action item, todo, deadline, need to, we should, can you, could you, by EOD/tomorrow | +2 |
| @mentions SLACK_MY_USER_ID | +2 |
| @mentions anyone | +1 |
| Ends with question | +1 |
| Under 4 words | -1 |

Score >= 2 → surfaced as action item.

Strip Slack markup: `<@U...>` → @user, `<#C...|name>` → #name, `:emoji:` → removed.

---

## Step 2 — Save to raw/slack/

Write two files per channel to `raw/slack/YYYY-MM-DD/<channel>/`:

**digest.md** (human-readable):
```markdown
---
title: "Slack Digest — #channel — YYYY-MM-DD"
date: YYYY-MM-DD
channel: channel-name
channel_id: C...
type: slack-digest
processed: false
---
# #channel — YYYY-MM-DD
*N messages scanned · N action items*
## Action items
- [ ] [message text] *(via Sender Name, score: N)*
## Message log
- **Sender** (HH:MM UTC): message text
```

**data.json** (structured):
```json
{
  "channel_id": "C...",
  "channel_name": "channel-name",
  "message_count": N,
  "action_items": [{"text":"...","sender":"Name","ts_human":"HH:MM UTC","score":3,"channel":"name"}],
  "raw_messages": [{"text":"...","sender":"Name","ts_human":"HH:MM UTC"}]
}
```

---

## Step 3 — Confirm

```
Slack #<channel> — N messages, N action items → raw/slack/YYYY-MM-DD/<channel>/digest.md
```

Then offer:
- Say `daily` to include in today's briefing
- Say `process inbox` to wikify the digest

---

## Step 4 — Bot token (optional, for scheduled runs without Cowork)

If the user has admin rights to install a Slack app, they can add `SLACK_BOT_TOKEN=xoxb-...` to tools/.env.

Required OAuth scopes: `channels:history`, `channels:read`, `users:read`, `groups:history`

Once set: `bash tools/run-slack-ingest.sh` runs standalone without Cowork.

**Note:** Corporate Slack workspaces often restrict app installs. Use the Cowork MCP approach (Steps 1-3) in that case — no token required.
