# Webhook Run Logging for Git-Backed LLM Wiki

Session-derived guidance for webhook/API automation runs that must create `logs/webhook-runs/<run_id>.md`, commit, push, and send Telegram summaries.

## Recommended sequence

1. Before syncing, verify repository and remote, then verify worktree is clean with `git status --porcelain=v1`. Stop if non-empty unless the payload explicitly authorizes committing/preserving local changes.
2. Run the required sync command, e.g. `git fetch origin main && git checkout main && git pull --ff-only origin main`.
3. Orient from `SCHEMA.md`, `index.md`, recent `log.md`, and any compatibility metadata such as `TheSchema.md` or `wiki/index.md`/`wiki/log.md`.
4. Perform the build/query/ingest writes.
5. Create/update `logs/webhook-runs/<run_id>.md` before staging. Include start time, payload, sync command/result, key files read, created/updated/deleted files, pre-commit `git status`, and errors so the log itself is part of the first commit.
6. Commit and push the wiki update.
7. Because the commit hash and push result are only known after step 6, finalize the run log by appending the build commit hash, push result, final status, and end time. Commit and push that one-file log finalization if the user required the log to contain commit/push details.
8. Telegram/final summary should mention both hashes when two commits occur: the build commit and the final log-metadata commit.

## Pitfalls

- If you generate the detailed log after capturing `git status`, the status block will omit the new log file. Write or touch the log before the pre-commit status snapshot.
- A single commit cannot truthfully contain its own final commit hash in the committed log content. Either record `pending` in the log and report the commit hash only in the final message, or do a second log-finalization commit when the prompt requires the log file itself to contain the hash and push result.
- For webhook payloads with placeholder fields (`question: "{question}"`, `save: "{save}"`, `delivery_id: "{delivery_id}"`), preserve the literal payload in the run log; do not invent missing values.
- When validating wikilinks, ignore examples inside schema/guide docs or classify them separately so placeholder examples like `[[wikilink]]` do not look like generated graph breakage.