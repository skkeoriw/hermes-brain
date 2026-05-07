# False `no_raw_change` skip + TG proof checklist

Use when users report: "I changed raw but got no Telegram".

## Symptom pattern
- Git commit includes `raw/articles/*.md` changes.
- Webhook run returns `skipped:no_raw_changes`.
- No Telegram message arrives.

## Root cause class
Incremental detector incorrectly infers "no changes" from sync state (e.g., `git pull --ff-only` up-to-date) instead of diffing payload commit range.

## Required fix
1. Enforce diff source: `git diff --name-only <before> <sha> -- 'raw/**/*.md'`.
2. Fallback only when `<before>` invalid/missing: `HEAD~1..HEAD`.
3. Only empty diff can produce `skipped:no_raw_changes`.
4. If raw changed and update+push succeeded, Telegram must be sent per route contract.

## Verification recipe
1. Add one marker line to a raw file and push.
2. Confirm webhook accepted with `run_id`.
3. Check run-log fields:
   - `changed_raw_count > 0`
   - updated/created wiki files
   - commit hash + push success
4. Confirm Telegram delivery with concrete evidence (`chat_id`, `message_id`).

## Example evidence fields
- `run_id`: gh-... 
- `changed_raw_files`: [raw/articles/...]
- `result`: updated
- `commit_hash`: <hash>
- `push_result`: success
- Telegram send result: `success=true`, `message_id=<id>`
