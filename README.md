# Hermes 大脑 / hermes-brain

Private portable "brain" repository for Hermes Agent.

This repo mirrors selected persistent Hermes data from `${HERMES_HOME:-~/.hermes}` into `brain/hermes-home/`, so a new machine can clone the repo and restore the same memories, skills, sessions, webhook/SOP automations, config, and test credentials.

WARNING: This private repository may contain plaintext credentials, API keys, OAuth tokens, webhook secrets, GitHub tokens, and gateway pairing data. It is for trusted machines/testing. Do not make it public. If it leaks, rotate/revoke every credential. Git history preserves deleted secrets.

## What is included

Synced from local Hermes home:

- `memories/` (`MEMORY.md`, `USER.md`)
- `skills/`
- `sessions/`
- `state.db`
- `config.yaml`
- `.env`
- `auth.json`
- `webhook_subscriptions.json`
- `channel_directory.json`
- `gateway_state.json`
- `pairing/`
- `profiles/`
- custom durable files under `~/.hermes`

Excluded as runtime/rebuildable data:

- Hermes source checkout / venv: `hermes-agent/`
- `logs/`
- caches: `cache/`, `audio_cache/`
- checkpoints
- lock/pid/log/temp files
- SQLite WAL/SHM sidecars

## Push this machine's Hermes brain into repo

From this repo:

```bash
./scripts/sync_from_local_to_repo.sh --git --push -m "sync: update Hermes brain"
```

Without committing/pushing:

```bash
./scripts/sync_from_local_to_repo.sh
git status --short
```

## Pull repo brain into this machine

```bash
./scripts/sync_from_repo_to_local.sh --pull
```

The script backs up existing local Hermes home to `~/.hermes-brain-backups/` before replacing it.

## New machine bootstrap from zero

```bash
git clone https://github.com/ChangfengHU/hermes-brain.git
cd hermes-brain
./scripts/bootstrap_new_machine.sh
```

If Hermes is already installed and you only want to restore the brain:

```bash
./scripts/bootstrap_new_machine.sh --skip-install
```

## Doctor

```bash
./scripts/doctor.sh
```

## Does Hermes have this built in?

Hermes has persistent memory, skills, sessions, profiles, webhooks, cron jobs, and profile export/import primitives. At the moment this repo implements a practical Git-backed "portable brain" workflow around those files. In other words: Hermes has the pieces, but this exact multi-machine Git sync workflow is provided here as scripts/runbook rather than a single built-in `hermes brain sync` command.
