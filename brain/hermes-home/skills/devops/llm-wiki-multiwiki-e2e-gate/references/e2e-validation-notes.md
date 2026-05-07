# E2E validation notes (prompt-qa-unified-wiki)

## Observed failure modes and fixes

1) Invalid workflow yaml (line around heredoc end)
- Symptom: `Invalid workflow file ... yaml syntax on line X`
- Cause: heredoc terminator `JSON` indentation mismatch under `run: |` block.
- Fix: align terminator indentation with script body.

2) Gate false-negative on raw changes
- Symptom: raw changed commit still logs `Skip webhook: no_raw_change`.
- Cause: diff ran in ad-hoc tmp repo with unreliable commit availability/path filtering.
- Fix: use `actions/checkout@v4` + `fetch-depth:0`, then diff in checked-out repo:
  `git diff --name-only "$BEFORE" "$AFTER" -- 'raw/**/*.md'`

3) Dispatch diagnostics
- `422 Workflow does not have 'workflow_dispatch' trigger` => trigger recognition/parsing problem, not token auth.
- `403 Resource not accessible by personal access token` => token lacks repo/action permission.

## Verified run pattern

- Raw-change push run shows:
  - `changed_count=1`
  - webhook returns `{"status":"accepted","route":"qa-wiki-ops",...}`
  - Hermes creates `logs/webhook-runs/<delivery>.md`
  - Hermes pushes incremental commit back to origin

- Follow-up non-raw commit run shows:
  - `changed_count=0`
  - `Skip webhook: no_raw_change`
  - no webhook call

## Evidence style to collect

- GitHub run IDs for both raw-changed and no-raw-change runs
- Action logs containing `changed_count` and webhook response body
- Hermes run log file path: `logs/webhook-runs/<run_id>.md`
- Resulting incremental commit hash for push-back commit
