---
name: hermes-brain-sync
description: Use when bootstrapping, cloning, restoring, or synchronizing a user's Hermes Agent memory, skills, sessions, configuration, webhooks, and plaintext test credentials across machines from the hermes-brain repository.
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
- `state.db-wal`
- `state.db-shm`
- `.update_check`

## New Machine Bootstrap

From a fresh machine:

```bash
git clone https://github.com/ChangfengHU/hermes-brain.git
cd hermes-brain
bash scripts/bootstrap_new_machine.sh
```

The script checks dependencies, installs Hermes if missing, backs up any existing `~/.hermes`, restores `brain/hermes-home/`, fixes basic permissions, and runs `hermes doctor`.

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

For this first version, the repository is effectively last-writer-wins.

Recommended safe workflow:

1. On machine A: run `sync_from_local_to_repo.sh` and push.
2. On machine B: `git pull`, then run `sync_from_repo_to_local.sh`.
3. Avoid editing memories/skills on two machines simultaneously without pulling first.
4. If there is a conflict, inspect with `git diff`, choose the desired version, then commit.

SQLite files such as `state.db` are binary-ish and can conflict. Prefer one active writer at a time.

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
