# Fallback Script Runtime Observations

## Script: `hermes_brain_sync_fallback.sh`

### Observed Runtime (2026-05-09)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh (1st run) | ~4 min | Jitter sleep 242s + git operations + push (49 files changed) |
| AI model: owl-alpha | ~45s | Failed (timeout/error) |
| AI model: cobuddy:free | ~30s | Failed |
| AI model: poolside/laguna | — | Script timed out at 300s total before reaching this |
| **Total (1st attempt)** | **~5 min** | Killed by 300s cron timeout |

| Phase (2nd run) | Duration | Notes |
|---|---|---|
| auto_sync.sh (2nd run) | ~5 min | Jitter sleep 274s + git operations + push (5 files changed) |
| AI model: owl-alpha | ~30s | ✅ Succeeded |
| Telegram send | <5s | ✅ Success |
| **Total (2nd attempt)** | **~5 min 30s** | Completed successfully |

### Key Findings

1. **Jitter sleep dominates runtime**: `auto_sync.sh` sleeps a random 0–300s before doing anything. This is by design (thundering herd prevention).
2. **First AI model often fails**: `openrouter/owl-alpha` failed on first attempt but succeeded on second — transient failures are normal.
3. **Total pipeline budget**: Plan for 7–10 minutes worst case (300s jitter + 5 models × 45s timeout).
4. **Second run finds repo up-to-date**: After the first run pushes, the second run's auto_sync finds "Already up to date" but still goes through the full jitter + commit cycle for any new local changes.

### Model Fallback Chain (in order)

1. `openrouter/owl-alpha`
2. `baidu/cobuddy:free`
3. `poolside/laguna-m.1:free`
4. `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`
5. `~google/gemini-flash-latest`

Each model has a 45s timeout. If all fail, a simple diff-based report is sent instead.

### Recommendations

- Always invoke with `background: true` and `timeout: 600` or higher
- Do NOT run inline in a cron session with a 300s timeout
- The script is idempotent — safe to re-run if killed mid-flight
- Log file: `$HOME/.local/state/hermes-brain/sync-fallback.log`
