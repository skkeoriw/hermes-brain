# Control-plane layering and anti-drift notes

## Layer map (from active multi-wiki deployment)
1. GitHub workflow (`.github/workflows/hermes-webhook-on-push.yml`)
   - Trigger policy: push(main) + optional workflow_dispatch
   - Raw-change gate using `before..sha` diff over `raw/*.md` and `raw/**/*.md`
   - If `no_raw_change`: stop before webhook call
2. Hermes route (`~/.hermes/webhook_subscriptions.json`)
   - Route-level orchestration (`youtube-wiki-ops`, `qa-wiki-ops`, ...)
   - Stage routing (e.g., links -> NotebookLM, notebook outputs -> llm-wiki)
   - Commit/push and notification policy
3. Repo contract (`TheSchema.md` / `SCHEMA.md`)
   - In-repo execution contract and output expectations
   - Log path and expected artifacts

## Failure pattern to prevent
Dual gate drift:
- Workflow gate and webhook prompt both decide raw-change independently with slightly different logic.
- Symptom: one layer runs while another records `skipped:no_raw_change`.

## Preferred policy
- Workflow owns primary gate decision.
- Webhook prompt validates and consumes gate decision; only fail-open when payload context is missing/invalid.
- Keep route prompt short; move deterministic stage logic into reusable scripts.

## Minimal hardening checklist
- Use consistent diff spec in all layers (`raw/*.md` + `raw/**/*.md`).
- Include `gate_reason` in payload and persist into run logs.
- Use one normalized run-log schema for all wikis.
- Keep no-op policy strict: no raw change => no Telegram notification.
