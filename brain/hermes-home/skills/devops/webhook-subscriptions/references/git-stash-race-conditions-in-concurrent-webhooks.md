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
- errors: |
    <filename> already exists, no checkout
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

### Option 4: Use `.gitignore` to Prevent Log Stash

Add log files to `.gitignore` so they're never stashed:

```gitignore
# .gitignore
logs/webhook-runs/*.md
```

Then stashed content will never include log files:

```bash
git stash push -u -m "webhook-auto-stash-${RUN_ID}"
# logs/webhook-runs/*.md are ignored, not stashed

git fetch origin main
git checkout main
git pull --ff-only origin main

# Safe to write logs
cat > "logs/webhook-runs/${RUN_ID}.md" <<EOF
...
EOF

git stash pop  # Won't fail on log files
```

**Advantage:** Cleanest long-term; aligns with typical Git workflows (logs are usually not version-controlled).  
**Prerequisite:** Accept that log files won't be committed to Git (or use a separate logging service).

## Real-World Case: llm-wiki Webhook Build

The llm-wiki automation on GitHub runs incremental knowledge-graph builds via webhook. When multiple pushes arrive simultaneously (e.g., bulk test data, concurrent branches), several `gh-<run_id>` webhooks can start:

- `gh-25446144683-1.md` starts stash push
- `gh-25446153653-1.md` starts stash push
- `gh-25447022256-1.md` starts stash push
- `gh-25447048029-1.md` stash pushed, syncs, writes `logs/webhook-runs/gh-25447048029-1.md` ← **still untracked**
- Other webhooks' stash pop tries to restore, sees log file already exists, **aborts**

**Fix for llm-wiki:** Move log file write to after stash pop, or add `logs/webhook-runs/` to `.gitignore` and use a separate webhook-run registry (could be S3, Telegram archive, or database instead of Git).

## Prevention

1. **Webhook trigger rate:** If possible, batch pushes or add debouncing (wait N seconds before running webhook) to reduce concurrency.
2. **Unique paths:** Always use unique, collision-free run IDs (include timestamp or GitHub run attempt number).
3. **Test concurrency:** Manually trigger 3+ webhooks in rapid succession to verify stash behavior under load.
4. **Monitor stash:** Script a cleanup task that detects orphaned stash entries (`git stash list`) and alerts or auto-drops them after N hours.

## References

- Git stash docs: https://git-scm.com/docs/git-stash
- GitHub Actions concurrency: https://docs.github.com/en/actions/using-jobs/using-concurrency
- llm-wiki webhook automation: See `references/github-actions-webhook-relay-recursion-guard.md`
