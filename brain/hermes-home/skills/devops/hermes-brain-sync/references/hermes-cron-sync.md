# Hermes Brain Sync via Hermes Cron Job

This document describes how to schedule Hermes Brain synchronization using Hermes' built-in cronjob tool instead of systemd timers.

## Created Cron Job

During the session on 2026-05-06, a Hermes cron job was created to:

- Run the brain sync script hourly
- Determine push/pull role automatically
- Send a concise sync report via Telegram (to the user's home channel)

Job ID: `7e876733aba5`  
Name: `hermes-brain-sync-tg`  
Schedule: `0 * * * *` (every hour at minute 0)  
Delivery: `telegram` (home channel)

## Cron Job Prompt

The job runs the following prompt each hour:

```
You are a Hermes agent tasked to synchronize Hermes brain and report the result via Telegram. 
First, determine the sync role by reading the file ~/.config/hermes-brain/sync-role (use terminal tool to cat it). 
If the role is "push", run: 
  cd ~/hermes-brain && ./scripts/sync_from_local_to_repo.sh --git --push -m "auto sync $(hostname)"
Else if role is "pull", run: 
  cd ~/hermes-brain && ./scripts/sync_from_repo_to_local.sh --pull --skip-if-same
After the sync command finishes, capture its output. 
Then produce a concise summary containing: 
- The role used (push/pull) 
- The hostname (use hostname command) 
- Whether any files were synced (you can infer from the sync output: look for lines like "synced local -> repo: X files, Y dirs" or similar) 
- The timestamp of completion (use date -Is)
Output only this summary as your final response. Do not include any extra explanation.
```

## Managing the Job

- List jobs: `hermes cron list`
- View job details: `hermes cron show <job_id>` or inspect `~/.hermes/cron/jobs.json`
- View last run output: `ls -lt ~/.hermes/cron/output/<job_id>/` and read the latest `.md` file
- Manually trigger: `hermes cron run <job_id>`
- Pause/Resume: `hermes cron pause <job_id>` / `hermes cron resume <job_id>`
- Remove: `hermes cron remove <job_id>`

## Advantages over systemd timer

- Runs within Hermes context, so skills and memory are automatically loaded
- Output is captured as a session and can be searched via `session_search`
- Delivery is built-in (no need to parse logs)
- Easy to modify prompt or schedule via `hermes cron edit`
- No need to manage external timer units

## Migration from systemd timer

If you were previously using `hermes-brain-auto-sync.timer`, you can disable it:

```bash
systemctl --user stop hermes-brain-auto-sync.timer
systemctl --user disable hermes-brain-auto-sync.timer
```

Then ensure the Hermes cron job is active and running as desired.
