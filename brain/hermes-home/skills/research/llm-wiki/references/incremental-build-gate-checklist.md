# Incremental Build Gate Checklist (Webhook Contract)

Use this when repo-level subscription prompt adds strict incremental gates.

## Required order
1. `git stash push -u -m "webhook-auto-stash-<run_id>-<utc>"`
2. `git fetch origin`
3. `git checkout <branch>`
4. `git pull --ff-only origin <branch>`
5. `git stash pop`

## Raw-diff truth source
- Never use `git pull` result (`Already up to date`) as no-change proof.
- First choice:
  - `git diff --name-only <before> <sha> -- 'raw/**/*.md'`
- Fallback (only if before/sha missing/invalid/degenerate):
  - `git diff --name-only HEAD~1 HEAD -- 'raw/**/*.md'`

Only when both valid strategy result is empty after `raw/**/*.md` filter, classify:
- `skipped:no_raw_changes`

## Skip behavior
- No wiki writes/commit/push.
- If contract says “write run log every run”, still append/create run log and include:
  - diff commands tried,
  - changed_raw_count=0,
  - skip classification.
- Telegram gate: when contract forbids notify on no-raw-change, do not send.

## Notify behavior on success
When raw changed + wiki updated + push success, send Telegram summary containing at least:
- `action`
- `run_id`
- changed file count
- build commit hash
- run-log path

If run log is finalized in second commit, include both hashes (build + finalize-log).
