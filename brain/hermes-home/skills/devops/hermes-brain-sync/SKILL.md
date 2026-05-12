---
name: hermes-brain-sync
description: Use when bootstrapping, cloning, restoring, synchronizing, auto-syncing, or setting push/pull roles for a user's Hermes Agent memory, skills, sessions, configuration, webhooks, and plaintext test credentials across machines from the hermes-brain repository.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, sync, backup, migration, memory, skills, plaintext-secrets]
    related_skills: [hermes-agent, github-repo-management]
---

# Hermes Brain Sync

## Overview

This repository is the user's portable "Hermes 大脑". It stores a copy of Hermes Agent persistent state so multiple machines can share the same memories, skills, sessions, webhooks, prompts, config, and test credentials.

This project intentionally uses plaintext full sync for testing. Do not silently remove or encrypt secrets unless the user asks. Treat the repository as private-only.

## When to Use

Use this skill when the user asks to:

- Set up Hermes on a new machine from this repository.
- Copy this machine's Hermes state to GitHub.
- Restore ~/.hermes from the repository.
- Synchronize memories, USER profile, skills, sessions, webhook subscriptions, config, or credentials across machines.
- Explain what data is synced and what is excluded.

Do not use this for production secret management unless the user explicitly accepts plaintext risk or requests an encrypted variant.

## Data Model

Canonical repo path:

```text
brain/hermes-home/
```

This maps to local:

```text
~/.hermes/
```

The sync scripts copy most persistent files directly. This includes plaintext test credentials such as `.env` and `auth.json`.

Default exclusions are runtime or rebuildable artifacts:

- `hermes-agent/`
- `logs/`
- `cache/`
- `audio_cache/`
- `__pycache__/`
- `*.pyc`
- `*.lock`
- `*.pid`
- `*.log`
- `*-wal`
- `*-shm`
- `.update_check`

## New Machine Bootstrap

From a fresh machine:

```bash
git clone https://github.com/ChangfengHU/hermes-brain.git
cd hermes-brain
bash scripts/bootstrap_new_machine.sh
```

The script checks dependencies, installs Hermes if missing, backs up any existing `~/.hermes`, restores `brain/hermes-home/`, sets the local sync role to `pull` if no role exists, installs the auto-sync timer when systemd user services are available, fixes basic permissions, and runs `hermes doctor`.

After bootstrap:

```bash
hermes doctor
hermes
```

If the machine should run gateway services:

```bash
hermes gateway install
hermes gateway start
```

## Auto Sync Roles

This repo intentionally uses one push machine and many pull machines.

Local, non-synced machine files:

```text
~/.config/hermes-brain/sync-role
~/.config/hermes-brain/machine-id
```

Global repo owner file:

```text
brain/sync-owner.json
```

Check status:

```bash
cd hermes-brain
python3 scripts/hermes_brain_role.py status
```

Make the current machine the single push owner:

```bash
cd hermes-brain
bash scripts/set_sync_role.sh push --git --push
```

Make the current machine pull-only:

```bash
cd hermes-brain
bash scripts/set_sync_role.sh pull
```

Install periodic auto-sync:

```bash
cd hermes-brain
bash scripts/install_auto_sync.sh hourly
```

All machines run `scripts/auto_sync.sh`. It pushes only when both conditions are true:

1. local role is `push`;
2. local machine id equals `brain/sync-owner.json.push_machine_id`.

Otherwise it pulls. If an old push machine sees a different global push owner, it automatically downgrades local role to `pull`.

This role-management procedure is the main way Hermes can "set itself to push": load/use this skill, then run `bash scripts/set_sync_role.sh push --git --push` inside the repo.

For session-specific implementation details and pitfalls, see `references/single-writer-auto-sync.md`.

## Push Local Hermes State to Repo

Use this on a machine whose Hermes state should become the shared state:

```bash
cd hermes-brain
bash scripts/sync_from_local_to_repo.sh
```

The script copies from `${HERMES_HOME:-$HOME/.hermes}` to `brain/hermes-home/`, writes `brain/manifest.json`, commits, and pushes if `origin` exists.

## Pull Repo State to Local Hermes

Use this when the repository is newer or on a new machine:

```bash
cd hermes-brain
bash scripts/sync_from_repo_to_local.sh
```

The script backs up current `~/.hermes` under `~/.hermes-brain-backups/` before restoring.

## Conflict Policy

This repo uses a single-writer / multi-reader model:

- one `push` machine writes `~/.hermes` into the repo and pushes to GitHub;
- all other machines are `pull` machines and restore from GitHub.

New machines default to pull. To make the current machine the single push owner:

```bash
cd hermes-brain
bash scripts/set_sync_role.sh push --git --push
```

To check role:

```bash
python3 scripts/hermes_brain_role.py status
```

See `docs/conflict-policy.md` for details.

SQLite files such as `state.db` are binary-ish and can conflict if multiple machines push. This project avoids that by allowing only the global push owner in `brain/sync-owner.json` to push. Old push machines auto-downgrade to pull when they see a different owner.

### Learnings and improvements from this session
- Update: Add explicit Pitfalls section to Hermes brain-sync to capture guidance for long-running commands and background execution in cron tasks.
- Correction: If a user expresses preferences for concise reports (verbosity/format), embed that preference within the skill so future runs honor it without extra prompts.
- New guidance: When auto_sync.sh runs, ensure we capture both HEAD and HEAD~1 diffs reliably; avoid assuming HEAD~1 exists in non-bare repos; consider using git rev-list --max-count 2 to fetch the latest two commits to compute diffs.

### Pitfalls
- Ambiguity in diff stats when the repo is in a detached HEAD state; always resolve to a known branch or tag before performing diffs.
- Large binary files in the repo can trigger LFS warnings; consider enabling Git LFS or excluding heavy artifacts from scheduled pushes.
- Background tasks in cron may complete after the main flow; always verify completion via exit codes and logs before reporting success.


## Plaintext Secret Warning

This repo can include plaintext keys by design:

- `.env`
- `auth.json`
- webhook secrets
- gateway state
- channel/pairing state
- provider credentials

Rules:

- Keep the GitHub repository private.
- Do not paste repo contents into public issues or logs.
- If the repo becomes public, rotate all credentials.

## Daily Sync Workflow (absorbed from brain-sync-workflow)

This section codifies the end-to-end procedure for synchronizing the Hermes brain repo, extracting commit metadata, building GitHub navigation links, and generating a Telegram-friendly report.

### Canonical Sync Steps

1) **Sync the brain**
   ```bash
   cd ~/hermes-brain && ./scripts/auto_sync.sh
   ```
   Validate the sync completed (non-zero exit code indicates a problem).

2) **Capture commit information**
   ```bash
   CURRENT=$(git log -1 --format "%H %h %s")
   PREV=$(git log -1 HEAD~1 --format "%H")
   ORIGIN=$(git remote get-url origin)
   DIFF_STAT=$(git diff HEAD~1 HEAD --stat)
   DIFF_CONTENT=$(git diff HEAD~1 HEAD --no-color | head -1000)
   ```

3) **Build GitHub links**
   From ORIGIN, extract owner/repo, then:
   - Compare: `https://github.com/OWNER/REPO/compare/PREV_SHA...CURRENT_SHA`
   - Commit: `https://github.com/OWNER/REPO/commit/CURRENT_SHA`

4) **Generate Telegram report (三个部分)**
   - Section A: 核心摘要 — 2-3 bullets from diff content
   - Section B: 详细变更 — file counts, new files, modified files
   - Section C: 快速导航 — compare/commit links

5) **Output** in Telegram-friendly format.

### Pitfalls specific to the sync workflow

- **Model deadlock (CRITICAL)**: If the cron job runs on the same model the fallback script tries first (currently `openrouter/owl-alpha`), the `hermes chat` call will hang indefinitely due to resource contention. The `timeout 45` wrapper may not kill the subprocess. Fix: reorder the model list in the script so the cron agent's own model is last, or add logic to skip `CRON_MODEL` in the fallback chain.
- **Duplicate concurrent runs**: Multiple instances of `hermes_brain_sync_fallback.sh` can stack up if the cron interval is shorter than the script runtime. Each hung instance worsens the deadlock. Before starting a new run, kill orphans: `pkill -f hermes_brain_sync_fallback; pkill -f 'hermes chat'`.
- **Fallback script runtime**: The full `hermes_brain_sync_fallback.sh` pipeline can take 4–10 minutes (jitter sleep 0-300s + AI model fallback chain with 45s timeout × up to 5 models). Always run in background (`background: true`) with a 600s+ timeout. Do NOT run inline in a cron job with a 300s timeout — this causes the script to be killed mid-flight. With 600s timeout, all observed runs (Sessions 2–5, 2026-05-10) completed successfully.
- **`hermes chat` hangs indefinitely**: When a model/provider is unreachable, `hermes chat -m <model>` can hang forever — the `timeout 45` wrapper does NOT always kill the subprocess. Kill manually: `pkill -f 'hermes chat'`; `pkill -f hermes_brain_sync_fallback`. The `openrouter/owl-alpha` model in particular has been observed to hang on one run and succeed on the very next run (2026-05-10), confirming transient connectivity issues rather than permanent failure.
- **GitHub repo may be deleted/renamed**: The remote can return "Repository not found". Check `git fetch origin 2>&1` first if sync fails repeatedly. As of 2026-05-11, `https://github.com/ChangfengHU/hermes-brain.git/` consistently returns this error — the repo may have been deleted, renamed, or made private for 3+ days. The sync script continues past this error (does not block the AI report or Telegram send), but no git push/pull happens until the remote is fixed. When git fails fast (no network timeout), the entire fallback pipeline can complete in ~2 minutes if the first AI model succeeds.
- **Script is safe to re-run**: The fallback script is idempotent. If the first run is killed by a 300s cron timeout, a second run (with a fresh jitter value) often completes successfully. The jitter is re-randomized each invocation, so a second run may get a much shorter sleep.
- **Always run in background with 600s+ timeout**: Running `hermes_brain_sync_fallback.sh` inline/foreground with a 300s timeout has failed consistently (Sessions 1 and 6, 2026-05-11). The jitter sleep alone can consume 279s+, leaving no time for the AI model chain. Use `background: true` with `timeout: 600` or higher. All 4 background runs (Sessions 2, 4, 5, 6) completed successfully.
- **Jitter sleep**: `auto_sync.sh` includes a random 0-300s jitter. Expect this delay.
- **Telegram bot separation**: Keep brain-sync TG notifications decoupled from wiki/webhook TG notifications by using a dedicated bot token + chat_id per flow. See `references/telegram-bot-separation.md`.

### Telegram Report Format (absorbed from brain-sync-reporting)

See `templates/telegram-report-template.md` for the full template.

**Section A — 核心摘要** (2-3 concrete bullet points from the diff):
```
• Updated N files with M lines added, K lines removed
• Major changes: [specific insight from diff content]
• [Additional meaningful observation]
```

**Section B — 详细变更:**
```
📂 文件变更: X 个，+Y / -Z

🆕 新增文件: N 个
  - path/to/file1
  - path/to/file2

✏️ 修改文件: M 个
  - path/to/updated1
  - path/to/updated2
```

**Section C — 快速导航:**
```
🔗 查看本次详细变更: [COMPARE_LINK]
🔍 查看提交详情: [COMMIT_LINK]
🏠 HOSTNAME ⏰ TIMESTAMP
```

### Fallback: Direct Telegram Send (no hermes dependency)

When `hermes_brain_sync_fallback.sh` hangs and you need to send a report NOW:

```bash
pkill -f hermes_brain_sync_fallback
pkill -f 'hermes chat'
cd ~/hermes-brain
SHORT_SHA=$(git log -1 --format="%h")
COMMIT_MSG=$(git log -1 --format="%s")
DIFF_STAT=$(git diff HEAD~1 HEAD --stat 2>/dev/null || echo "N/A")
HOSTNAME=$(hostname)
ISO_TIME=$(date -Is)

curl -sS -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "disable_web_page_preview=true" \
  --data-urlencode "text@/tmp/hermes_brain_sync_tg.txt"
```

See `references/fallback-direct-telegram.md` for the complete procedure, and `references/fallback-script-runtime.md` for observed runtime measurements.

## Verification Checklist

After bootstrap or restore:

- [ ] `~/.hermes/memories/MEMORY.md` exists if the source had memory.
- [ ] `~/.hermes/memories/USER.md` exists if the source had user profile.
- [ ] `~/.hermes/skills/` exists.
- [ ] `hermes doctor` runs.
- [ ] `hermes skills list` shows expected skills in a fresh session.
- [ ] Gateway is only started if this machine is intended to receive messages/webhooks.

## Checking sync status and logs

- To see current effective role: `cd ~/hermes-brain && ./scripts/hermes_brain_role.py status`
- To view recent auto-sync logs: `cat $HOME/.local/state/hermes-brain/auto-sync.log`
- To manually trigger a sync: `cd ~/hermes-brain && ./scripts/auto_sync.sh`
- To check git status of the brain repo: `cd ~/hermes-brain && git status --short`

## Hermes Cron Job Alternative

Instead of systemd timers, you can use Hermes' built-in cron scheduler for brain sync:
- See `references/hermes-cron-sync.md` for details on the hourly Telegram-reporting sync job
- Manage with `hermes cron list`, `hermes cron run <job_id>`, etc.

**Auto-persistence flow:** When a cron job runs, it executes `./scripts/auto_sync.sh` inside the brain repo. The output is captured and reported via Telegram. After the cron runs:

1. Local `~/.hermes` state is synced to `brain/hermes-home/`
2. Git commits are created (if changes detected)
3. Pushed to GitHub (if push role is enabled for this machine)
4. Cron job result (changes summary or "no changes") is sent to Telegram

**Key insight:** Hermes Agent config/webhook/memory changes made in one session do NOT automatically persist to the brain repo until the next cron run. For immediate persistence, run `python3 scripts/hermes_brain_sync.py local-to-repo` manually.
