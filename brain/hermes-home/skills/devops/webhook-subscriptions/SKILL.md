---
name: webhook-subscriptions
description: "Webhook subscriptions: event-driven agent runs."
version: 1.1.0
metadata:
  hermes:
    tags: [webhook, events, automation, integrations, notifications, push]
---

# Webhook Subscriptions

Create dynamic webhook subscriptions so external services (GitHub, GitLab, Stripe, CI/CD, IoT sensors, monitoring tools) can trigger Hermes agent runs by POSTing events to a URL.

## Setup (Required First)

The webhook platform must be enabled before subscriptions can be created. Check with:
```bash
hermes webhook list
```

If it says "Webhook platform is not enabled", set it up:

### Option 1: Setup wizard
```bash
hermes gateway setup
```
Follow the prompts to enable webhooks, set the port, and set a global HMAC secret.

### Option 2: Manual config
Add to `~/.hermes/config.yaml`:
```yaml
platforms:
  webhook:
    enabled: true
    extra:
      host: "0.0.0.0"
      port: 8644
      secret: "generate-a-strong-secret-here"
```

### Option 3: Environment variables
Add to `~/.hermes/.env`:
```bash
WEBHOOK_ENABLED=true
WEBHOOK_PORT=8644
WEBHOOK_SECRET=generate-a-strong-secret-here
```

After configuration, start (or restart) the gateway:
```bash
hermes gateway run
# Or if using systemd:
systemctl --user restart hermes-gateway
```

Verify it's running:
```bash
curl http://localhost:8644/health
```

## Commands

All management is via the `hermes webhook` CLI command:

### Create a subscription
```bash
hermes webhook subscribe <name> \
  --prompt "Prompt template with {payload.fields}" \
  --events "event1,event2" \
  --description "What this does" \
  --skills "skill1,skill2" \
  --deliver telegram \
  --deliver-chat-id "12345" \
  --secret "optional-custom-secret"
```

Returns the webhook URL and HMAC secret. The user configures their service to POST to that URL.

### List subscriptions
```bash
hermes webhook list
```

### Remove a subscription
```bash
hermes webhook remove <name>
```

### Test a subscription
```bash
hermes webhook test <name>
hermes webhook test <name> --payload '{"key": "value"}'
```

### Manual curl/Postman testing

Webhook routes accept three auth header styles when a route/global secret is configured:

- `X-Hub-Signature-256: sha256=<hmac>` — GitHub-style HMAC over the exact raw request body. Any body change, including whitespace, requires recomputing the signature.
- `X-Webhook-Signature: <hmac>` — generic HMAC over the exact raw request body.
- `X-Gitlab-Token: <secret>` — fixed token comparison. Prefer this for Postman or simple backend callers when the user wants to edit JSON bodies without recalculating signatures.

For fixed-token testing, use:
```bash
curl -i -X POST "http://127.0.0.1:8644/webhooks/<name>" \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: <route-secret>" \
  -H "X-Request-ID: test-run-001" \
  --data '{"action":"query","question":"test","save":false}'
```

Use `X-Request-ID` when you want a human-readable `delivery_id`; otherwise Hermes generates a millisecond timestamp. If the payload also has `run_id`, set both to the same value so gateway logs, session traces, and task-generated files correlate cleanly.

## Prompt Templates

Prompts support `{dot.notation}` for accessing nested payload fields:

- `{issue.title}` — GitHub issue title
- `{pull_request.user.login}` — PR author
- `{data.object.amount}` — Stripe payment amount
- `{sensor.temperature}` — IoT sensor reading

If no prompt is specified, the full JSON payload is dumped into the agent prompt.

## Common Patterns

### GitHub: new issues
```bash
hermes webhook subscribe github-issues \
  --events "issues" \
  --prompt "New GitHub issue #{issue.number}: {issue.title}\n\nAction: {action}\nAuthor: {issue.user.login}\nBody:\n{issue.body}\n\nPlease triage this issue." \
  --deliver telegram \
  --deliver-chat-id "-100123456789"
```

Then in GitHub repo Settings → Webhooks → Add webhook:
- Payload URL: the returned webhook_url
- Content type: application/json
- Secret: the returned secret
- Events: "Issues"

### GitHub: PR reviews
```bash
hermes webhook subscribe github-prs \
  --events "pull_request" \
  --prompt "PR #{pull_request.number} {action}: {pull_request.title}\nBy: {pull_request.user.login}\nBranch: {pull_request.head.ref}\n\n{pull_request.body}" \
  --skills "github-code-review" \
  --deliver github_comment
```

### Stripe: payment events
```bash
hermes webhook subscribe stripe-payments \
  --events "payment_intent.succeeded,payment_intent.payment_failed" \
  --prompt "Payment {data.object.status}: {data.object.amount} cents from {data.object.receipt_email}" \
  --deliver telegram \
  --deliver-chat-id "-100123456789"
```

### CI/CD: build notifications
```bash
hermes webhook subscribe ci-builds \
  --events "pipeline" \
  --prompt "Build {object_attributes.status} on {project.name} branch {object_attributes.ref}\nCommit: {commit.message}" \
  --deliver discord \
  --deliver-chat-id "1234567890"
```

For GitHub push -> Hermes relay workflows (including recursion guards like `paths: ['raw/**']` and 401 triage), see `references/github-actions-webhook-relay-recursion-guard.md`.

### Generic monitoring alert
```bash
hermes webhook subscribe alerts \
  --prompt "Alert: {alert.name}\nSeverity: {alert.severity}\nMessage: {alert.message}\n\nPlease investigate and suggest remediation." \
  --deliver origin
```

### Direct delivery (no agent, zero LLM cost)

For use cases where you just want to push a notification through to a user's chat — no reasoning, no agent loop — add `--deliver-only`. The rendered `--prompt` template becomes the literal message body and is dispatched directly to the target adapter.

Use this for:
- External service push notifications (Supabase/Firebase webhooks → Telegram)
- Monitoring alerts that should forward verbatim
- Inter-agent pings where one agent is telling another agent's user something
- Any webhook where an LLM round trip would be wasted effort

```bash
hermes webhook subscribe antenna-matches \
  --deliver telegram \
  --deliver-chat-id "123456789" \
  --deliver-only \
  --prompt "🎉 New match: {match.user_name} matched with you!" \
  --description "Antenna match notifications"
```

The POST returns `200 OK` on successful delivery, `502` on target failure — so upstream services can retry intelligently. HMAC auth, rate limits, and idempotency still apply.

Requires `--deliver` to be a real target (telegram, discord, slack, github_comment, etc.) — `--deliver log` is rejected because log-only direct delivery is pointless.

## Security

- Each subscription gets an auto-generated HMAC-SHA256 secret (or provide your own with `--secret`)
- The webhook adapter validates signatures on every incoming POST
- Supported auth headers:
  - `X-Hub-Signature-256: sha256=<hmac>` — GitHub-style HMAC over the exact raw request body. The signature changes whenever the body changes, so it is awkward for Postman/manual calls unless the body is fixed.
  - `X-Webhook-Signature: <hmac>` — generic HMAC over the exact raw request body.
  - `X-Gitlab-Token: <secret>` — fixed token comparison. Prefer this for Postman and backend callers that need to freely change JSON payloads without recomputing HMAC each time.
- For powerful routes that can edit files, push Git, or send messages, do not remove auth just for convenience. Use the fixed-token `X-Gitlab-Token` pattern instead.
- Static routes from config.yaml cannot be overwritten by dynamic subscriptions
- Subscriptions persist to `~/.hermes/webhook_subscriptions.json`

## How It Works

1. `hermes webhook subscribe` writes to `~/.hermes/webhook_subscriptions.json`
2. The webhook adapter hot-reloads this file on each incoming request (mtime-gated, negligible overhead)
3. When a POST arrives matching a route, the adapter formats the prompt and triggers an agent run
4. The agent's response is delivered to the configured target (Telegram, Discord, GitHub comment, etc.)

## Troubleshooting

If webhooks aren't working:

1. **Is the gateway running?** Check with `systemctl --user status hermes-gateway` or `ps aux | grep gateway`
2. **Is the webhook server listening?** `curl http://localhost:8644/health` should return `{"status": "ok"}`
3. **Check gateway logs:** `grep webhook ~/.hermes/logs/gateway.log | tail -20`
4. **Signature mismatch?** Verify the secret in your service matches the one from `hermes webhook list` or `~/.hermes/webhook_subscriptions.json`. GitHub sends `X-Hub-Signature-256`, GitLab-style fixed-token calls send `X-Gitlab-Token`.
5. **Accepted but no final answer?** `{"status":"accepted"}` is normal for async webhooks. Track progress with `grep '<delivery_id>\|response ready' ~/.hermes/logs/gateway.log`; final output is delivered via the route's `deliver` target.
6. **Need the active session trace?** Look for a new `~/.hermes/sessions/session_<timestamp>_*.json` whose platform is `webhook`; inspect recent messages/tool calls to see whether the agent is syncing, scanning, writing, committing, or still running.
7. **Dynamic route changed but gateway not restarted?** Dynamic subscriptions are hot-reloaded on incoming requests (mtime-gated), so changing `~/.hermes/webhook_subscriptions.json` can take effect on the next POST. Platform enablement/port changes still require gateway restart.
8. **Firewall/NAT?** The webhook URL must be reachable from the service. For local development, use a tunnel (ngrok, cloudflared).
9. **Wrong event type?** Check `--events` filter matches what the service sends. If a subscription has Events `(all)`, `event=unknown` is acceptable and still runs.
10. **Webhook ran but task aborted early (no build/commit)?** Inspect the webhook session JSON under `~/.hermes/sessions/session_<timestamp>_*.json` for that delivery. In Git workflows, a common precondition failure is a dirty working tree (for example `git status --porcelain` showing untracked files like `?? .github/`), which causes policy-driven prompts to stop before sync/build/push. Treat this as a repo-state issue, not a webhook transport failure.
11. **Telegram delivery uncertainty for webhook runs:** gateway logs can show webhook completion without a per-delivery `[Telegram] Sending response ...` line. Confirm delivery from the webhook session trace by checking for a successful `send_message` tool result (e.g. `{"success": true, "platform": "telegram", ...}`). This separates polling noise from actual per-run delivery success.

5. **Accepted but no final answer?** `{"status":"accepted"}` is normal for async webhooks. Track progress with `grep '<delivery_id>\|response ready' ~/.hermes/logs/gateway.log`; final output is delivered via the route's `deliver` target.
6. **Response is tiny / no build artifacts created?** Check for provider failures in request dumps:
   - Find latest dump: `ls -t ~/.hermes/sessions/request_dump_*.json | head -1`
   - Inspect `reason`, `error.code`, and model/provider fields (e.g., `max_retries_exhausted`, HTTP 524).
   - If present, this is usually a model/provider failure before tool execution (not a webhook route/auth problem). Switch webhook default model/provider to a more reliable option and restart gateway/session.
7. **Need the active session trace?** Look for a new `~/.hermes/sessions/session_<timestamp>_*.json` whose platform is `webhook`; inspect message count and tool calls. If it contains only the injected user prompt and no assistant/tool messages, the run likely failed before tool execution.
8. **Provider/model recently changed but webhook behavior still looks old?** Verify live config, then restart gateway so new defaults are actually used:
   - Check: `hermes config | sed -n '/^model:/,/^[^ ]/p'`
   - Set provider/model (example):
     - `hermes config set model.provider openai-codex`
     - `hermes config set model.default gpt-5.3-codex`
   - Restart: `hermes gateway restart` (or `systemctl --user restart hermes-gateway`)
   This is critical when request dumps show upstream model errors (e.g., `max_retries_exhausted`, HTTP `524`) before any tool calls.
9. **Telegram delivery flaky with `terminated by other getUpdates request`?** Another process/machine is polling the same bot token. Keep only one polling instance for that token (or migrate Telegram adapter mode to webhooks) before judging webhook-delivery reliability.
10. **Dynamic route changed but gateway not restarted?** Dynamic subscriptions are hot-reloaded on incoming requests (mtime-gated), so changing `~/.hermes/webhook_subscriptions.json` can take effect on the next POST. Platform enablement/port changes still require gateway restart.
10. **Firewall/NAT?** The webhook URL must be reachable from the service. For local development, use a tunnel (ngrok, cloudflared).
11. **Wrong event type?** Check `--events` filter matches what the service sends. If a subscription has Events `(all)`, `event=unknown` is acceptable and still runs.
12. **GitHub push says triggered, but Hermes sees nothing?** Distinguish source failures vs receiver failures:
   - Query GitHub webhook deliveries: `GET /repos/<owner>/<repo>/hooks/<hook_id>/deliveries`.
   - If statuses are `Invalid HTTP Response: 401`, the route secret is mismatched (GitHub webhook `secret` vs Hermes route secret). Fix by aligning both.
   - If using a GitHub Actions relay (`curl` to Hermes) instead of native repo webhooks, check the Actions run status and logs first; the repo webhook list/deliveries may show failures that are irrelevant to the active relay path.
13. **Prevent webhook recursion in Git-backed wiki builds:** If Hermes writes back to the same repo (commit/push), gate the trigger by path (for example, only trigger on `raw/**` changes). This prevents build-generated updates under `wiki/`, `log.md`, etc. from re-triggering the webhook endlessly.
