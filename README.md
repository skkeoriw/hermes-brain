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

## Auto sync model: one push machine, many pull machines

This repo uses a single-writer model:

```text
Push machine: ~/.hermes -> ~/hermes-brain/brain/hermes-home -> GitHub
Pull machines: GitHub -> ~/hermes-brain/brain/hermes-home -> ~/.hermes
```

Each machine has a local role stored outside the synced brain data:

```text
~/.config/hermes-brain/sync-role     # push or pull
~/.config/hermes-brain/machine-id    # stable local machine id
```

The repo stores only the global push owner declaration:

```text
brain/sync-owner.json
```

New machines default to `pull`. To make the current machine the single push writer:

```bash
./scripts/set_sync_role.sh push --git --push
```

To make the current machine pull-only:

```bash
./scripts/set_sync_role.sh pull
```

Check the local role and effective role:

```bash
python3 scripts/hermes_brain_role.py status
```

Install the periodic auto-sync timer:

```bash
./scripts/install_auto_sync.sh hourly
```

All machines run the same timer. `scripts/auto_sync.sh` decides whether to push or pull based on the local role plus `brain/sync-owner.json`. If an old push machine sees that another machine became the global push owner, it automatically downgrades itself to pull.

## Manual push this machine's Hermes brain into repo

From this repo:
```bash
./scripts/sync_from_local_to_repo.sh --git --push -m "sync: update Hermes brain"
```

Without committing/pushing:

```bash
./scripts/sync_from_local_to_repo.sh
git status --short
```

## Manual pull repo brain into this machine

```bash
./scripts/sync_from_repo_to_local.sh --pull
```

The script backs up existing local Hermes home to `~/.hermes-brain-backups/` before replacing it. Auto-sync uses `--skip-if-same` to avoid unnecessary backups when local and repo content already match.

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
