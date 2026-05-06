# Git Stash Race Conditions in Concurrent Webhook Sync

## Problem Summary

When multiple GitHub Actions webhooks run **concurrently** on the same repository, a `git stash pop` can fail with:

```
error: could not restore untracked files from stash
logs/webhook-runs/gh-25447048029-1.md already exists, no checkout
```

The task aborts, leaving the stash entry intact (so manual recovery is possible).

## Root Cause

Webhook sync flow typically follows this pattern:

1. `git stash push -u -m "webhook-auto-stash-<run_id>"` — save current untracked files
2. `git fetch origin main && git checkout main && git pull --ff-only origin main` — sync from remote
3. **Agent writes log file** — e.g. `logs/webhook-runs/gh-25448271621-1.md` (untracked)
4. `git stash pop` — restore stash ← **FAILS** if another concurrent webhook already created the same log file path

**Why it fails:**  
When webhook A stashes files, then writes log file `X`, it expects `git stash pop` to restore the stash cleanly. But if webhook B has *also* started and written its own log file (same path structure, different run_id), git cannot restore A's original stash because the path now exists as an untracked file created by a different task.

## Diagnosis

Check webhook logs in `logs/webhook-runs/<run_id>.md`:

Look for:
```yaml
- status: aborted
- error: git stash pop reported restore conflict on untracked files
- errors: |\n    <filename> already exists, no checkout
    error: could not restore untracked files from stash
```

Also check `git stash list`:
```bash
git stash list
```

If entries remain with names like `webhook-auto-stash-gh-25447048029-1`, stash pop failed on that run.

## Solutions

### Option 1: Write Log After Stash Pop (Recommended)

Restructure the webhook sync flow:

```bash
# Stash early
git stash push -u -m "webhook-auto-stash-${RUN_ID}"

# Sync
git fetch origin main
git checkout main
git pull --ff-only origin main

# Restore stash FIRST, BEFORE writing logs
git stash pop

# NOW write log file (it won't interfere with stash pop)
cat > "logs/webhook-runs/${RUN_ID}.md" <<EOF
...
EOF
```

**Advantage:** Eliminates the race because log files are written *after* stash pop succeeds.  
**Prerequisite:** The log file path must not conflict with any stashed content (use unique run_ids, not hardcoded paths).

### Option 2: Exclude Log Directory from Stash

Tell the webhook to skip stashing the log directory:

```bash
# Custom filter: don't stash logs/
git stash push -u -m "webhook-auto-stash-${RUN_ID}" -- ':(exclude)logs/'

git fetch origin main
git checkout main
git pull --ff-only origin main

# Now safe to write logs even if stash pop fails
cat > "logs/webhook-runs/${RUN_ID}.md" <<EOF
...
EOF

git stash pop
```

**Advantage:** Decouples log files from stash entirely.  
**Caveat:** If the webhook intentionally stashes local edits in `logs/`, this loses them.

### Option 3: Global Mutex (Lock File)

Serialize webhook execution with a lock:

```bash
LOCK_FILE="$REPO/.webhook_lock"

# Acquire lock
while [ -f "$LOCK_FILE" ]; do sleep 0.5; done
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Now safe: only one webhook runs at a time
git stash push -u -m "webhook-auto-stash-${RUN_ID}"
git fetch origin main
git checkout main
git pull --ff-only origin main
cat > "logs/webhook-runs/${RUN_ID}.md" <<EOF
...
EOF
git stash pop
```

**Advantage:** Guaranteed no concurrency.  
**Disadvantage:** Serializes all webhook runs (slower).

### Option 4: Use `.gitignore` + GitHub Actions Concurrency Control (PROVEN PRODUCTION)

**Best-practice solution combining two layers of protection:**

#### Layer 1: Add Log Files to `.gitignore`

```gitignore
# .gitignore
logs/webhook-runs/*.md
```

This ensures log files are never stashed, eliminating the race condition at its source.

#### Layer 2: Add GitHub Actions `concurrency` Control

In your `.github/workflows/hermes-webhook-on-push.yml`:

```yaml
name: Trigger Hermes Webhook on Push

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:
    inputs:
      action:
        description: "Webhook action: incremental_build or full_build"
        required: true
        default: "incremental_build"

# Prevent multiple webhooks from running concurrently on the same repo.
# This avoids git stash pop race conditions when untracked log files collide.
concurrency:
  group: hermes-webhook-${{ github.repository }}
  cancel-in-progress: false

jobs:
  notify-hermes:
    runs-on: ubuntu-latest
    steps:
      - name: Build webhook payload
        id: payload
        shell: bash
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            ACTION="${{ github.event.inputs.action }}"
          else
            ACTION="incremental_build"
          fi

          # Standardized run_id for end-to-end tracing
          RUN_ID="gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"

          cat > payload.json <<JSON
          {
            "event": "${GITHUB_EVENT_NAME}",
            "repo": "${GITHUB_REPOSITORY}",
            "ref": "${GITHUB_REF}",
            "sha": "${GITHUB_SHA}",
            "before": "${{ github.event.before }}",
            "action": "${ACTION}",
            "run_id": "${RUN_ID}",
            "delivery_id": "${RUN_ID}",
            "actor": "${GITHUB_ACTOR}"
          }
          JSON

      - name: Call Hermes webhook
        shell: bash
        env:
          HERMES_WEBHOOK_URL: ${{ vars.HERMES_WEBHOOK_URL != '' && vars.HERMES_WEBHOOK_URL || secrets.HERMES_WEBHOOK_URL }}
          HERMES_WEBHOOK_TOKEN: ${{ vars.HERMES_WEBHOOK_TOKEN != '' && vars.HERMES_WEBHOOK_TOKEN || secrets.HERMES_WEBHOOK_TOKEN }}
        run: |
          if [ -z "$HERMES_WEBHOOK_URL" ]; then
            echo "Missing config: HERMES_WEBHOOK_URL"
            exit 1
          fi

          HTTP_CODE=$(curl -sS -o response.json -w "%{http_code}" \
            -X POST "$HERMES_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -H "X-Gitlab-Token: $HERMES_WEBHOOK_TOKEN" \
            -H "X-Request-ID: gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" \
            --data @payload.json)

          if [ "$HTTP_CODE" -lt 200 ] || [ "$HTTP_CODE" -ge 300 ]; then
            echo "Webhook call failed with HTTP $HTTP_CODE"
            exit 1
          fi
```

**Key features:**

- **`concurrency.group`:** All webhooks targeting the same repo are serialized into a queue
- **`cancel-in-progress: false`:** Queued tasks are not cancelled; they execute in FIFO order
- **`RUN_ID` format:** `gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}` for end-to-end tracing with GitHub Actions
- **`X-Request-ID` header:** Pass the same run_id to Hermes so logs, sessions, and tasks correlate

**Advantages:**
- ✅ Root cause eliminated (`.gitignore` ensures logs never enter stash)
- ✅ Safety mechanism in place (concurrency control prevents simultaneous execution)
- ✅ End-to-end tracing (run_id correlates GitHub Actions → Hermes webhook → task logs)
- ✅ Zero breaking changes (fully backward compatible)
- ✅ Production-proven (deployed on llm-wiki-obsidian-blink, 2026-05-07)

**Verification:**

```bash
# Check .gitignore rule exists
grep "logs/webhook-runs" .gitignore

# Check concurrency control is in place
git show HEAD:.github/workflows/hermes-webhook-on-push.yml | grep -A2 "concurrency:"

# Monitor GitHub Actions runs
# Visit: https://github.com/<owner>/<repo>/actions
# Verify that multiple webhook runs are queued (status "Queued") rather than simultaneous
```

**Cleanup (if orphaned stash entries exist):**

```bash
# List stash entries
git stash list

# Drop orphaned webhook stash entries if any remain
# git stash drop stash@{N}  # Remove a specific entry
```

## Real-World Case: llm-wiki Webhook Build

The llm-wiki automation on GitHub runs incremental knowledge-graph builds via webhook. When multiple pushes arrive simultaneously (e.g., bulk test data, concurrent branches), several `gh-<run_id>` webhooks can start:

- `gh-25446144683-1.md` starts stash push
- `gh-25446153653-1.md` starts stash push  
- `gh-25447022256-1.md` starts stash push
- `gh-25447048029-1.md` stash pushed, syncs, writes `logs/webhook-runs/gh-25447048029-1.md` ← **still untracked**
- Other webhooks' stash pop tries to restore, sees log file already exists, **aborts**

**Fix applied (2026-05-07):**
1. Added `logs/webhook-runs/*.md` to `.gitignore` (commit 1474dc2)
2. Added `concurrency` control to `.github/workflows/hermes-webhook-on-push.yml`
3. Standardized `RUN_ID` as `gh-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`

Result: No more race conditions; webhook queues are stable and fully traced.

## Prevention & Monitoring

1. **Webhook trigger rate:** If possible, batch pushes or add debouncing (wait N seconds before running webhook) to reduce concurrency.
2. **Unique paths:** Always use unique, collision-free run IDs (include GitHub run ID or timestamp).
3. **Test concurrency:** Manually trigger 3+ webhooks in rapid succession to verify stash behavior under load.
4. **Monitor stash:** Script a cleanup task that detects orphaned stash entries (`git stash list`) and alerts or auto-drops them after N hours.
5. **Verify .gitignore:** Confirm that logs are ignored: `git status logs/webhook-runs/` should show nothing (or "nothing to commit").

## References

- Git stash docs: https://git-scm.com/docs/git-stash
- GitHub Actions concurrency: https://docs.github.com/en/actions/using-jobs/using-concurrency
- GitHub Actions workflow syntax: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions
- llm-wiki webhook automation: See `references/github-actions-webhook-relay-recursion-guard.md`
