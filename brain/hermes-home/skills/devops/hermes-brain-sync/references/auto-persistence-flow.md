# Auto-Persistence: How Config Changes Flow to Brain Repo

## Session Context (2026-05-06)

User configured 19 custom LLM providers in `~/.hermes/config.yaml` and changed two jobs (wiki-ops webhook, hermes-brain-sync-tg cron) to use new models. Then asked: **"Are these changes automatically persisted to brain via the cron job?"**

## Answer: Partially Automatic, With a Caveat

### What DOES auto-persist:

The `hermes-brain-sync-tg` cron job (scheduled `0 * * * *`, i.e., every hour) runs:
```bash
cd ~/hermes-brain
./scripts/auto_sync.sh
```

This script:
1. Checks the machine's sync role (push/pull)
2. If push: syncs `~/.hermes` → `brain/hermes-home/`, commits, pushes to GitHub
3. If pull: syncs `brain/hermes-home/` (from git) → `~/.hermes`
4. Reports the result via Telegram

So any config/webhook/memory/skill changes made locally **will be persisted on the next cron run** (up to 1 hour later).

### The Gotcha: Timing

When the user modified `~/.hermes/config.yaml` and `webhook_subscriptions.json`:
- Changes were **immediate** in `~/.hermes`
- But **NOT** in the brain repo until the next hourly cron run
- If the machine crashed or the user switched to another machine (via pull) before the cron ran, **changes could be lost**

### Solution: Manual Immediate Sync

When you need changes persisted immediately (e.g., to test on another machine):

```bash
cd ~/hermes-brain
python3 scripts/hermes_brain_sync.py local-to-repo
git add -A
git commit -m "manual sync: describe changes here"
git push origin main
```

Or use the high-level wrapper:
```bash
cd ~/hermes-brain
bash scripts/sync_from_local_to_repo.sh
```

### What Happened in This Session

1. User made config + webhook changes: 19 providers, gpt-5-mini for wiki-ops, gpt-5-nano for hermes-brain-sync-tg
2. I ran cron job status check → it showed recent failures (HTTP 429 from old OpenAI key)
3. Changes were live in `~/.hermes` but not yet in the brain repo
4. I manually ran `python3 scripts/hermes_brain_sync.py local-to-repo` + git commit + push
5. Now changes are safe in GitHub for other machines to pull from
6. Next scheduled cron run (19:00 UTC) will also sync, but the manual push ensured no data loss

## Best Practice: When to Manual vs. Auto

| Scenario | Use Auto? | Use Manual? |
|----------|-----------|------------|
| Small tweak during development | ✓ Auto ok (can wait 1 hour) | Only if testing on another machine |
| Production config change | ✗ Don't wait | ✓ Manual NOW |
| New provider added for testing | ✓ Auto ok | ✓ If you switch machines before cron |
| Critical credential/webhook secret | ✗ Never wait | ✓ Manual NOW + verify push |
| Bulk update (many files changed) | ✓ Check manually first | ✓ Recommended (avoid cron race) |

## Monitoring & Debugging

**Check auto-sync status:**
```bash
cd ~/hermes-brain
python3 scripts/hermes_brain_role.py status
# Shows: effective_role (push or pull), machine_id, owner machine
```

**Check last cron result:**
```bash
systemctl --user status hermes-brain-auto-sync.timer
# or
ls -lah ~/.local/state/hermes-brain/auto-sync.log | tail -20
```

**Manually trigger a sync (for testing):**
```bash
cd ~/hermes-brain
bash scripts/auto_sync.sh
```

**See what git commits were made:**
```bash
cd ~/hermes-brain
git log --oneline -10 | grep "sync:"
```

## Related: Cron Job Failures Don't Block Manual Sync

In this session, the hermes-brain-sync-tg cron **failed** with HTTP 429 several times. But that didn't block manual sync:
- Cron failure = telegram message won't send, but git syncing can still work manually
- Manual sync is independent of cron scheduling
- So even if cron breaks, you can always `cd ~/hermes-brain && ./scripts/sync_from_local_to_repo.sh` to push changes

## Key Insight for Future Sessions

When user asks "will X auto-save?":
1. Check if a cron job is configured (likely yes for brain-sync)
2. Confirm the cron job's last status and role (push vs pull)
3. If changes are critical/urgent, don't wait for cron — manual sync now
4. If changes are exploratory/safe-to-lose, auto-sync is fine

The 1-hour lag is acceptable for most changes but not for production configs or credential updates.
