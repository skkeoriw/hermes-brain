# Telegram gating + polling conflict patterns for webhook automations

Use this when webhook runs may or may not produce meaningful business updates, and notifications go to Telegram.

## 1) Separate "should notify" from transport config

If a webhook route has static `deliver: telegram`, Hermes will deliver every run response (including skip/no-op runs).

For conditional notifications (e.g., only notify when incremental build had real `raw/**` changes and graph updates):
- Remove static route-level `deliver` / `deliver_extra` from `~/.hermes/webhook_subscriptions.json` for that route.
- Let the agent call `send_message(target="telegram")` only when business conditions are met.

This avoids noisy alerts on `skipped:no_raw_changes` runs.

## 2) Recommended gating rule for incremental wiki builds

Notify Telegram only when ALL are true:
1. `action == incremental_build`
2. `raw/**/*.md` changed in diff window
3. graph/wiki artifacts were actually updated
4. commit + push to remote succeeded

If result is `skipped:no_raw_changes`, do not send Telegram.

## 3) Business-first summary format (for useful notifications)

Prefer concise, decision-useful fields over tool logs:
- changed raw article paths
- newly added entities (name + file path)
- newly added relations (`source -> relation -> target`)
- updated entities/concepts and change type
- artifact summary (which wiki areas changed)
- commit/push hash + run log path

## 4) Diagnose Telegram "Conflict: terminated by other getUpdates request"

This conflict is caused by multiple polling clients using the same bot token, not by too many sends to one chat.

Meaning:
- Sending webhook + cron notifications to the same chat is fine.
- Running Telegram polling on multiple machines/processes with the same token is NOT fine.

Checks:
- list cron jobs (`cronjob action='list'`) to see which jobs deliver to Telegram
- inspect processes for duplicate gateway/bot pollers
- verify only one active polling instance per token across all machines

Once duplicate poller is stopped, delivery reliability recovers.