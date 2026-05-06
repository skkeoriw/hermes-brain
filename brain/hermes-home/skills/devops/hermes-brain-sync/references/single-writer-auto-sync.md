# Single-writer Hermes Brain Auto Sync

Use this reference for the user's preferred multi-machine Hermes brain topology: one push machine and many pull machines.

## Model

The user clarified they do not want multiple machines pushing concurrently. The desired topology is:

```text
A / push machine:
  ~/.hermes -> ~/hermes-brain/brain/hermes-home -> GitHub hermes-brain

B/C / pull machines:
  GitHub hermes-brain -> ~/hermes-brain/brain/hermes-home -> ~/.hermes
```

This avoids Git conflicts for binary/state files such as `state.db`, `sessions/`, `.env`, and `auth.json` by design: only one machine writes to `main`.

## Role storage

Do not store per-machine role inside `brain/hermes-home/`; that directory is restored into every machine and would copy one machine's role to all others.

Local, non-synced role state:

```text
~/.config/hermes-brain/sync-role     # push or pull
~/.config/hermes-brain/machine-id    # stable local machine id
```

Repo global owner state:

```text
brain/sync-owner.json
```

The global owner file declares the current single push owner. Other machines compare their local `machine-id` against it.

## Commands

Check local/effective role:

```bash
cd ~/hermes-brain
python3 scripts/hermes_brain_role.py status
```

Make current machine the single push owner:

```bash
cd ~/hermes-brain
./scripts/set_sync_role.sh push --git --push
```

Make current machine pull-only:

```bash
cd ~/hermes-brain
./scripts/set_sync_role.sh pull
```

Install periodic auto sync:

```bash
cd ~/hermes-brain
./scripts/install_auto_sync.sh hourly
```

Manual auto-sync run:

```bash
cd ~/hermes-brain
./scripts/auto_sync.sh
```

## Automatic downgrade behavior

If machine A used to be local `push`, then machine B runs `set_sync_role.sh push --git --push`, A is not remotely modified. Instead, A's next timer run sees that `brain/sync-owner.json.push_machine_id` no longer equals A's local machine id. A writes local role `pull` and runs pull mode.

This implements “setting a new push machine automatically demotes the old push machine” without needing SSH or remote control.

## Bootstrap default

New machines should default to `pull`. Only explicitly promote a machine to push when the user says it should be the main/A machine.

## Pitfalls

- Never `git push --force` from auto sync.
- Do not let a pull machine auto-promote itself to push.
- Do not put `sync-role` or `machine-id` under `~/.hermes` or `brain/hermes-home/`.
- Auto pull should use a skip-if-same check to avoid creating a backup every timer tick when repo and local Hermes home already match.
- If systemd user services are unavailable, bootstrap should skip timer installation and tell the user they can run `scripts/auto_sync.sh` manually.
