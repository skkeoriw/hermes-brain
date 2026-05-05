# Conflict Policy

Initial policy: last writer wins, with Git history as rollback.

Recommended workflow:

1. Before using a machine for Hermes work:

```bash
cd hermes-brain
git pull
bash scripts/sync_from_repo_to_local.sh
```

2. After meaningful Hermes changes:

```bash
cd hermes-brain
bash scripts/sync_from_local_to_repo.sh
```

3. Avoid concurrent writes to `state.db` from multiple machines.

4. For memory conflicts, manually merge:

```text
brain/hermes-home/memories/MEMORY.md
brain/hermes-home/memories/USER.md
```

5. For skill conflicts, inspect the changed `SKILL.md` files and keep the more complete procedure.
