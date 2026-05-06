# GitHub Actions webhook relay: recursion guard + 401 triage

Use this when GitHub push events should call a Hermes webhook, and Hermes may commit back to the same repository.

## Recommended trigger guard

Only trigger on source-of-truth paths (example: `raw/**`) so webhook-generated wiki/index/log commits do not re-trigger the workflow.

```yaml
on:
  push:
    branches: ["main"]
    paths:
      - 'raw/**'
```

## Minimal relay step

```yaml
- name: Call Hermes webhook
  env:
    HERMES_WEBHOOK_URL: ${{ vars.HERMES_WEBHOOK_URL != '' && vars.HERMES_WEBHOOK_URL || secrets.HERMES_WEBHOOK_URL }}
    HERMES_WEBHOOK_TOKEN: ${{ vars.HERMES_WEBHOOK_TOKEN != '' && vars.HERMES_WEBHOOK_TOKEN || secrets.HERMES_WEBHOOK_TOKEN }}
  run: |
    test -n "$HERMES_WEBHOOK_URL"
    test -n "$HERMES_WEBHOOK_TOKEN"
    curl -sS -o response.json -w "%{http_code}" \
      -X POST "$HERMES_WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -H "X-Gitlab-Token: $HERMES_WEBHOOK_TOKEN" \
      -H "X-Request-ID: gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" \
      --data @payload.json
```

## 401 diagnosis split

1) Native GitHub Webhook path (Settings -> Webhooks):
- Check deliveries endpoint for the hook.
- `Invalid HTTP Response: 401` means secret mismatch.

2) GitHub Actions relay path:
- Check Actions run status/logs first.
- A successful run with webhook `202 accepted` proves relay path works even if native webhook deliveries still show 401 from an older/misconfigured hook.
