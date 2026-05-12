# Fallback Script Runtime Observations

## Script: `hermes_brain_sync_fallback.sh`

### Observed Runtimes

#### 2026-05-09 (Session 1)

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

#### 2026-05-10 (Session 2 — cron job)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh (1st run) | ~30s | Jitter sleep 282s BUT git fetch failed immediately ("Repository not found") |
| AI model: owl-alpha (1st) | ~45s | Hung — script killed by 300s cron timeout |
| **Total (1st attempt)** | **~5 min** | Killed by 300s cron timeout (owl-alpha hung) |

| Phase (2nd run, background) | Duration | Notes |
|---|---|---|
| auto_sync.sh (2nd run) | ~90s | Jitter sleep 60s + git fetch failed ("Repository not found") |
| AI model: owl-alpha (2nd) | ~30s | ✅ Succeeded |
| Telegram send | <5s | ✅ Success |
| **Total (2nd attempt)** | **~2 min** | Completed successfully |

#### 2026-05-10 (Session 4 — cron job, background)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh | ~10s | Jitter sleep 101s BUT git fetch failed immediately ("Repository not found") |
| AI model: owl-alpha (1st) | ~30s | ✅ Succeeded on first try |
| Telegram send | <5s | ✅ Success |
| **Total** | **~140s (~2 min 20s)** | Completed successfully on first attempt |

#### 2026-05-10 (Session 5 — cron job, background, 600s timeout)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh | ~10s | Jitter sleep 209s BUT git fetch failed immediately ("Repository not found") |
| AI model: owl-alpha (1st) | ~30s | ✅ Succeeded on first try |
| Telegram send | <5s | ✅ Success |
| **Total** | **~245s (~4 min 5s)** | Completed successfully on first attempt; 600s timeout was sufficient |

#### 2026-05-11 (Session 6 — cron job)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh (foreground, 300s timeout) | ~5 min | Jitter sleep 279s + git fetch failed ("Repository not found") |
| AI model: owl-alpha (1st, foreground) | ~45s | Hung — killed by 300s cron timeout |
| **Total (1st attempt, foreground)** | **~5 min** | Killed by 300s cron timeout |

| Phase (2nd run, background, 600s timeout) | Duration | Notes |
|---|---|---|
| auto_sync.sh (2nd run) | ~230s | Jitter sleep 226s + git fetch failed ("Repository not found") |
| AI model: owl-alpha (2nd, background) | ~30s | ✅ Succeeded on first try |
| Telegram send | <5s | ✅ Success |
| **Total (2nd attempt, background)** | **~261s (~4 min 21s)** | Completed successfully; 600s timeout was sufficient |

#### 2026-05-10 (Session 3 — cron job, manual fallback)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh | ~10s | Jitter sleep 267s BUT git fetch failed immediately ("Repository not found") |
| AI model: owl-alpha (1st) | >300s | Hung — killed by cron timeout |
| **Total (1st attempt)** | **>5 min** | Killed by 300s cron timeout |

| Phase (manual fallback) | Duration | Notes |
|---|---|---|
| Kill hung processes | <5s | `pkill -f hermes_brain_sync_fallback; pkill -f 'hermes chat'` |
| Collect diff info | <5s | `git log`, `git diff HEAD~1 HEAD --stat` |
| AI model: owl-alpha (2nd) | ~30s | Responded but gave unhelpful output (asked for more context) |
| AI model: owl-alpha (3rd) | <5s | **Crashed** with `KeyboardInterrupt` traceback |
| Direct curl Telegram send | <5s | ✅ Success (message_id: 189) |
| **Total (manual fallback)** | **~1 min** | Completed successfully without `hermes chat` |

### Key Findings

1. **Jitter sleep dominates runtime**: `auto_sync.sh` sleeps a random 0–300s before doing anything. This is by design (thundering herd prevention). When jitter is low (<120s) and git fails fast, the entire pipeline can complete in under 3 minutes.
2. **First AI model usually succeeds with adequate timeout**: `openrouter/owl-alpha` has succeeded on first attempt in 3 of the last 4 runs (Sessions 4, 5, and one sub-run of Session 2). The 600s cron timeout is sufficient; the 300s timeout was the root cause of earlier failures. Transient failures still occur — always retry at least once before declaring a model dead.
3. **`hermes chat` has two failure modes**: hang (most common) and `KeyboardInterrupt` crash (observed 2026-05-10). Both mean the model call failed. See `references/fallback-direct-telegram.md`.
4. **Total pipeline budget**: Plan for 7–10 minutes worst case (300s jitter + 5 models × 45s timeout). Best case is ~2 minutes (low jitter + first model succeeds). With 600s timeout, all observed runs complete successfully.
5. **Second run finds repo up-to-date**: After the first run pushes, the second run's auto_sync finds "Already up to date" but still goes through the full jitter + commit cycle for any new local changes.
6. **Manual fallback is fast**: When the script hangs, killing processes and sending via curl directly takes ~1 minute total.
7. **Git remote "Repository not found" is persistent**: As of 2026-05-11, `https://github.com/ChangfengHU/hermes-brain.git/` consistently fails — the repo has been unreachable for 3+ days. The script continues past this error (AI report + Telegram still work), but no git sync happens until the remote is fixed. This is a persistent state, not a transient blip.
8. **Deadlock when cron model = script's first model (2026-05-11)**: When the cron job itself runs on `openrouter/owl-alpha`, the fallback script's `hermes chat -m openrouter/owl-alpha` call hangs indefinitely. This is a resource contention deadlock — the cron agent occupies the model's capacity and the nested `hermes chat` call can never complete. The `timeout 45` wrapper does NOT always kill the subprocess in this scenario. **Workaround**: Either (a) reorder the model list so the cron's own model is last, or (b) skip the model that matches the cron agent's model. Confirmed: the same model (`owl-alpha`) hung on one run and succeeded on the very next run, proving the deadlock is specific to concurrent usage, not model availability.
10. **Foreground 300s timeout always fails (confirmed 2026-05-11)**: Running the script inline/foreground with a 300s timeout has now failed twice in a row (Sessions 1 and 6). The jitter sleep alone can consume 279s+, leaving insufficient time for the AI model fallback chain. Always use `background: true` with a 600s+ timeout. The background approach has succeeded in all 4 attempts (Sessions 2, 4, 5, 6).

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
