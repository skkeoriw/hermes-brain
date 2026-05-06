# llm-wiki webhook pattern: business-focused summaries + Telegram gating

When a webhook route drives `llm-wiki` incremental builds, user value is typically business impact, not execution noise.

## What to include in final summary (priority order)

1. Changed source articles under `raw/**/*.md` (explicit path list)
2. New entities added this run (`name + file path`)
3. New relations added this run (`source -> relation -> target`)
4. Updated entities (`name + change type`, e.g. added alias/property/link)
5. Build artifact scope (`wiki/entities`, `wiki/concepts`, `wiki/index`, `wiki/log`, etc.)
6. Commit/push result (commit hash)

Avoid long tool-by-tool logs in the user-facing summary; keep logs in `logs/webhook-runs/<run_id>.md`.

## Telegram delivery rule to reduce noise

For incremental builds:
- If result is `skipped:no_raw_changes`, do **not** send Telegram.
- Only send Telegram when both are true:
  - `raw/**/*.md` changed in diff window
  - graph artifacts were actually updated (real build impact)

Implementation hint:
- Do **not** rely solely on route-level `deliver=telegram` for this workflow, because it forwards every run outcome.
- Let the agent decide via explicit `send_message` only on meaningful runs.

## Diff-window best practice

Use payload `before` and `sha` when present:
- `git diff --name-only <before>..<sha> -- '*.md'`
- then filter to `raw/**/*.md`

Fallback when `before` is missing:
- `git diff --name-only HEAD~1..HEAD -- '*.md'`

## Why this matters

This preserves observability while aligning notifications with business outcomes:
- users see exactly which source documents triggered work
- users see KG delta (entities/relations), not infrastructure chatter
- no-alert runs stay silent when nothing changed in raw
