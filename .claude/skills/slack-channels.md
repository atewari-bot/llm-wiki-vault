# Skill: Slack channel manager — slack channel commands

## Triggers
- "list slack channels" or "which channels am I monitoring"
- "add slack channel <x>"
- "remove slack channel <x>"
- "search slack channels <q>"

---

## list slack channels

Run: `python tools/slack_channels.py list`

Shows all currently monitored channel IDs (and names if SLACK_BOT_TOKEN is set).
Displays the config file path (tools/.env).

---

## add slack channel <x>

Run: `python tools/slack_channels.py add <x>`

- With bot token: accepts channel ID (C...) or channel name (e.g. "general")
- Without bot token: requires channel ID only (e.g. CXXXXXXXXXX)

Report result:
- "Added: #channel-name (C...)" — success
- "Already monitored" — already in list
- "Not found" — channel doesn't exist or no access

Then remind: "Run `refresh slack` or `daily` to pull messages from this channel."

**Finding a channel ID without a bot token:**
In Slack → right-click the channel → View channel details → Channel ID at the bottom of the modal.

---

## remove slack channel <x>

Run: `python tools/slack_channels.py remove <x>`

Accepts channel ID or name. Confirms removal and shows updated channel count.

---

## search slack channels <q>

Run: `python tools/slack_channels.py search <q>`

Requires SLACK_BOT_TOKEN in tools/.env.

Shows a results table:
```
ID             Name                      Members  Topic
CXXXXXXXXXX   general                           12  Team channel [monitored]
C1234567890   engineering                    45  Engineering discussions
```

After showing results:
"Say 'add slack channel <ID>' to start monitoring one."

**Without bot token:**
"Search requires SLACK_BOT_TOKEN. Find channel IDs in Slack: right-click channel → View channel details."

---

## Notes

- Changes to SLACK_CHANNEL_IDS take effect on the next `refresh slack` or `daily` run
- Channel list is stored in tools/.env under SLACK_CHANNEL_IDS (comma-separated)
- Run: `bash tools/run-slack-channels.sh <command>` as an alternative to Claude Code triggers
