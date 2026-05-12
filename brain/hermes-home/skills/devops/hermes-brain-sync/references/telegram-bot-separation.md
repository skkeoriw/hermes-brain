# Telegram separation for brain-sync vs wiki/webhook

Context
- Brain-sync cron notifications and wiki/webhook notifications can collide when both use the same Telegram bot + same delivery channel.

Recommended pattern (non-breaking)
1) Keep wiki/webhook route unchanged.
2) For brain-sync cron job, disable route-level Telegram delivery (`deliver=local`).
3) Send Telegram directly in the brain-sync workflow using a dedicated bot token + target chat_id.

Why this works
- Delivery paths are decoupled: wiki remains on existing bot/flow, brain-sync uses a separate sender identity.
- Avoids cross-flow message mixing and reduces operator confusion.
- Avoids dependence on Hermes gateway Telegram delivery for this cron.

Implementation notes
- Minimum required values: `BOT_TOKEN` + `chat_id`.
- Private chat: user must start chat with bot at least once.
- Group/channel: bot must be present and allowed to post.
- If token was exposed in logs/chat, rotate in BotFather before production use.

Validation
- Test with Telegram Bot API `sendMessage` and require `{"ok":true}`.
- Confirm bot identity in response (`from.username`) and destination (`chat.id`).

Example call pattern
- `curl -sS -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" -d "chat_id=<CHAT_ID>" --data-urlencode "text@/tmp/report.txt"`
