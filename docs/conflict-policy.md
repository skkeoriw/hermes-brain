# Conflict Policy

This repository now uses a single-writer / multi-reader policy.

## Roles

There are two roles:

- `push`: the one machine allowed to write local Hermes state into the repo and push to GitHub.
- `pull`: machines that only pull GitHub state and restore it into local Hermes.

Local role is stored outside the synced brain data:

```text
~/.config/hermes-brain/sync-role
~/.config/hermes-brain/machine-id
```

The repo stores only the global push-owner declaration:

```text
brain/sync-owner.json
```

Do not put per-machine role files under `brain/hermes-home/`; that directory is restored into every machine and would copy one machine's role to all machines.

## Normal data flow

Push machine:

```text
~/.hermes -> ~/hermes-brain/brain/hermes-home -> git commit -> git push
```

Pull machines:

```text
git pull -> ~/hermes-brain/brain/hermes-home -> ~/.hermes
```

## Setting roles

Make this machine the single push owner:

```bash
cd ~/hermes-brain
./scripts/set_sync_role.sh push --git --push
```

Make this machine pull-only:

```bash
cd ~/hermes-brain
./scripts/set_sync_role.sh pull
```

Check role status:

```bash
cd ~/hermes-brain
python3 scripts/hermes_brain_role.py status
```

## Automatic downgrade

If machine A used to be `push`, then machine B is set to `push`, the repo's `brain/sync-owner.json` changes to B.

A is not modified remotely. Instead, when A's timer next runs, it sees:

```text
local_role=push
owner_machine_id=<B>
my_machine_id=<A>
```

Then A automatically writes local role `pull` and runs pull mode. This keeps the system decentralized and avoids needing SSH access to old machines.

## Push conflicts

Push conflicts should be rare because there is only one writer. The push machine still uses normal Git rules:

1. Pull latest repo first.
2. Copy local Hermes into `brain/hermes-home/`.
3. Commit if changed.
4. Push.

Do not use `git push --force`. If push fails, stop and inspect manually.

## Binary/state files

`state.db`, sessions, `.env`, and `auth.json` are still synced in this plaintext test mode. Because only one push machine writes them, Git does not need to merge concurrent versions.

If a pull machine has important local Hermes changes, promote it to push first:

```bash
cd ~/hermes-brain
./scripts/set_sync_role.sh push --git --push
./scripts/auto_sync.sh
```

After that, old push machines will downgrade on their next timer run.
