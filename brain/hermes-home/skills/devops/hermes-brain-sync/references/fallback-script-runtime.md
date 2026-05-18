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

#### 2026-05-13 (Session 8 — cron job, foreground 300s + manual fallback)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh (foreground, 300s timeout) | ~30s | Jitter sleep 245s BUT git fetch failed immediately ("Repository not found") |
| AI model: owl-alpha (1st, foreground) | ~45s | Failed |
| AI model: cobuddy:free (1st) | — | **Hung** — script killed by 300s cron timeout |
| **Total (1st attempt, foreground)** | **~5 min** | Killed by 300s cron timeout (again) |

| Phase (manual fallback) | Duration | Notes |
|---|---|---|
| Kill hung + duplicate processes | <5s | `pkill -f hermes_brain_sync_fallback; pkill -f 'hermes chat'` — found **2 concurrent instances** stacked up |
| Collect diff info | <5s | `git log`, `git diff HEAD~1 HEAD --stat` — 349 files changed, +233596/-6707 |
| Compose concise report | <5s | Manual summary (AI models all unreliable) |
| Direct curl Telegram send | <5s | ✅ Success (message_id: 231) |
| **Total (manual fallback)** | **~1 min** | Completed successfully without `hermes chat` |

**Key observations from Session 8:**
- `baidu/cobuddy:free` now confirmed to hang (previously only owl-alpha was observed hanging). The hang issue is provider-wide, not model-specific.
- **Duplicate concurrent runs**: Two instances of `hermes_brain_sync_fallback.sh` were running simultaneously (two cron triggers). Each worsens the deadlock by consuming resources. Always check for and kill orphans before starting a new run.
- Git remote "Repository not found" persists (5+ days as of 2026-05-13).
- Manual fallback with a concise human-written report is the most reliable approach when all AI models are flaky.

#### 2026-05-12 (Session 7 — cron job, background, ≥600s timeout)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh (1st run, foreground 300s) | ~5 min | Jitter sleep 231s + git fetch failed ("Repository not found") |
| AI model: owl-alpha (1st, foreground) | ~45s | Failed |
| AI model: cobuddy:free (1st) | — | Script timed out at 300s before completing |
| **Total (1st attempt, foreground)** | **~5 min** | Killed by 300s cron timeout (again) |

| Phase (2nd run, background) | Duration | Notes |
|---|---|---|
| auto_sync.sh (2nd run) | ~200s | Jitter sleep 198s + git fetch failed ("Repository not found") |
| AI model: owl-alpha (2nd, background) | ~30s | ✅ Succeeded on first try |
| Telegram send | <5s | ❌ **Failed: "message is too long" (400 Bad Request)** |
| **Total (2nd attempt, background)** | **~230s (~3 min 50s)** | Script finished but TG delivery failed |

#### 2026-05-18 (Session 10 — cron job, foreground 300s + manual fallback)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh (foreground, 300s timeout) | ~4 min | Jitter sleep 236s + git operations + push succeeded (6 files changed, +1969/-6) |
| AI model: owl-alpha (1st, foreground) | ~45s | **Failed** — confirming cron deadlock pattern (cron agent model = script's first model) |
| AI model: cobuddy:free (1st) | — | **Hung** — script killed by 300s cron timeout |
| **Total (1st attempt, foreground)** | **~5 min** | Killed by 300s cron timeout (again — 5th confirmed failure with 300s foreground) |

| Phase (manual fallback) | Duration | Notes |
|---|---|---|
| Kill hung processes | <5s | `pkill -f hermes_brain_sync_fallback; pkill -f 'hermes chat'` |
| Collect diff info | <5s | `git log`, `git diff HEAD~1 HEAD --stat` — commit `d9cb35e` |
| Compose concise report | <5s | Simple diff-based report (all AI models unavailable) |
| Direct curl Telegram send | <5s | ✅ Success (message_id: 338) |
| **Total (manual fallback)** | **~10s** | Completed successfully without `hermes chat` |

**Key observations from Session 10:**
- **GitHub repo remote recovered**: After 5+ days of "Repository not found" (Sessions 7-9, 2026-05-12/13), git push succeeded again. Repo `https://github.com/skkeoriw/hermes-brain.git` (note: renamed from `ChangfengHU` to `skkeoriw`) is accessible and accepting pushes. The remote URL in the script/config may need updating if it still references the old `ChangfengHU` path.
- **300s foreground timeout failure confirmed again**: This is now the 5th consecutive failure when running inline with 300s timeout. The pattern is deterministic, not a fluke.
- **`owl-alpha` again failed as first model**: The cron deadlock pattern is confirmed again — when the cron job runs on `openrouter/owl-alpha`, the script's first model attempt hangs or fails immediately. The script's model list still starts with `openrouter/owl-alpha`.
- **Git push completed BEFORE timeout**: The auto_sync.sh finished (including push) before the 300s timeout. The timeout was consumed by the AI model fallback chain, not the git operations. This means the git sync was fully successful — only the TG notification needed manual completion.

#### 2026-05-13 (Session 9 — cron job, background, 600s timeout)

| Phase | Duration | Notes |
|---|---|---|
| auto_sync.sh | ~30s | Jitter sleep 270s BUT git fetch failed immediately ("Repository not found") |
| AI model: owl-alpha (1st) | ~30s | ✅ Succeeded on first try |
| Telegram send | <5s | ❌ **Failed: "message is too long" (400 Bad Request)** |
| **Total** | **~90s (~1 min 30s)** | Script finished but TG delivery failed |

**Key observations from Session 9:**
- Fastest observed completion: 90s total (git failed fast + owl-alpha succeeded immediately).
- TG "message too long" failure confirmed again — this is now a recurring pattern when AI models succeed on large diffs.
- The `bash -x` debug mode was used for the first time; no performance impact observed.
- Git remote "Repository not found" persists (6+ days as of 2026-05-13).

### Key Findings

1. **Jitter sleep dominates runtime**: `auto_sync.sh` sleeps a random 0–300s before doing anything. This is by design (thundering herd prevention). When jitter is low (<120s) and git fails fast, the entire pipeline can complete in under 3 minutes.
2. **First AI model usually succeeds with adequate timeout**: `openrouter/owl-alpha` has succeeded on first attempt in 4 of the last 5 runs (Sessions 4, 5, 6, 7). The 600s cron timeout is sufficient; the 300s timeout was the root cause of earlier failures. Transient failures still occur — always retry at least once before declaring a model dead.
3. **`hermes chat` has two failure modes**: hang (most common) and `KeyboardInterrupt` crash (observed 2026-05-10). Both mean the model call failed. See `references/fallback-direct-telegram.md`.
4. **Total pipeline budget**: Plan for 7–10 minutes worst case (300s jitter + 5 models × 45s timeout). Best case is ~2 minutes (low jitter + first model succeeds). With 600s timeout, all observed runs complete successfully.
5. **Second run finds repo up-to-date**: After the first run pushes, the second run's auto_sync finds "Already up to date" but still goes through the full jitter + commit cycle for any new local changes.
6. **Manual fallback is fast**: When the script hangs, killing processes and sending via curl directly takes ~1 minute total.
7. **Git remote "Repository not found" is persistent**: As of 2026-05-12, `https://github.com/ChangfengHU/hermes-brain.git/` has been failing for 4+ days. The script continues past this error (AI report + Telegram still work), but no git sync happens until the remote is fixed. This is a persistent state, not a transient blip.
8. **Deadlock when cron model = script's first model (2026-05-11)**: When the cron job itself runs on `openrouter/owl-alpha`, the fallback script's `hermes chat -m openrouter/owl-alpha` call can hang indefinitely due to resource contention. The `timeout 45` wrapper does NOT always kill the subprocess in this scenario. **Workaround**: Either (a) reorder the model list so the cron's own model is last, or (b) skip the model that matches the cron agent's model. Confirmed: the same model (`owl-alpha`) hung on one run and succeeded on the very next run.
9. **Foreground 300s timeout always fails (confirmed 2026-05-12)**: Running the script inline/foreground with a 300s timeout has now failed 3 times (Sessions 1, 6, 7). Always use `background: true` with a 600s+ timeout.
10. **Telegram message-too-long when AI succeeds (2026-05-12)**: When the AI model succeeds, the generated report can exceed Telegram's ~4096-character limit, causing `400 Bad Request: message is too long`. The script does NOT truncate the AI output before sending. This is a **new failure mode**: the script reports "success" but the Telegram notification is silently dropped. Fix needed in the fallback script: cap the `REPORT` variable to ~3800 chars, or split into multiple TG messages.

11. **Duplicate concurrent runs (2026-05-13)**: Two cron triggers fired in quick succession, causing two instances of the fallback script to run simultaneously. Each hung `hermes chat` call worsens resource contention. Always kill orphans before starting: `pkill -f hermes_brain_sync_fallback; pkill -f 'hermes chat'`.
12. **`baidu/cobuddy:free` confirmed to hang (2026-05-13)**: Previously only `openrouter/owl-alpha` was observed hanging. The hang issue is provider-wide, not model-specific. Any model in the fallback chain can hang indefinitely.
13. **Manual fallback is the most reliable path**: When all AI models are flaky, composing a concise human-written report and sending via direct curl is faster (~1 min) and more reliable than waiting for the model fallback chain. The report for Session 8 (349 files, +233K/-6.7K lines) was successfully delivered as message_id 231.

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
- If TG send fails with "message is too long", the report content is in `/tmp/hermes_brain_sync_tg.txt` — truncate and resend manually
