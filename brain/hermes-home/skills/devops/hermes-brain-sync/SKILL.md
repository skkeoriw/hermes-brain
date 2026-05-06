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
