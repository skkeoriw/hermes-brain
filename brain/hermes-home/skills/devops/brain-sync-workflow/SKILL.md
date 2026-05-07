---
name: brain-sync-workflow
category: devops
description: |
  Class-level skill for Hermes Brain synchronization workflows. Automates: (1) repo sync, (2) commit data extraction, (3) GitHub link generation, (4) generation of Telegram-style reports. Encodes procedural steps, pitfalls, and verification. Reusable across Hermes sessions.
prerequisites:
  - Hermes brain repository at ~/hermes-brain
  - git installed and configured
  - Network access to GitHub
  - Access to the workspace environment
version: 0.2
---

# Brain Sync Workflow (Class-Level Skill)

Overview
- This skill standardizes the end-to-end flow to synchronize the Hermes brain repository, extract commit metadata, generate GitHub navigation links, and render a Telegram-friendly report.
- It is designed to be invoked across sessions and to produce a stable, reusable report structure that mirrors the user's requested format.

When to use
- You need to perform a Hermes brain sync from any host and return a ready-to-publish Telegram-style report.
- You want consistent formatting for Section A (Semantic insights), Section B (Detailed changes), and Section C (GitHub links).

Procedure (canonical steps)
1) Sync the brain
   - cd ~/hermes-brain && ./scripts/auto_sync.sh
   - Validate the sync completed (non-zero exit code indicates a problem).
2) Capture commit information
   - CURRENT: git log -1 --format "%H %h %s"
   - PREV: git log -1 HEAD~1 --format "%H"
   - ORIGIN: git remote get-url origin
   - DIFF_STAT: git diff HEAD~1 HEAD --stat
   - DIFF_CONTENT: git diff HEAD~1 HEAD --no-color | head -1000
3) Build GitHub links
   - From ORIGIN, extract owner/repo (assume https://github.com/owner/repo.git)
   - CURRENT_SHA = full SHA from CURRENT
   - PREV_SHA = PREV
   - Compare link: https://github.com/owner/repo/compare/PREV_SHA...CURRENT_SHA
   - Commit link: https://github.com/owner/repo/commit/CURRENT_SHA
4) Generate Telegram report (三个部分)
   - Section A: 核心摘要 (2-3 bullets) — use DIFF_CONTENT/DIFF_STAT to craft precise, non-vague insights.
   - Section B: 详细变更（保留原有格式）
     - 文件变更: X 个，Y 行(+)，Z 行(-)
     - 新增文件: [count] 个
       - path/to/file1
       - path/to/file2
     - 修改文件: [count] 个
       - path/to/updated1
       - path/to/updated2
   - Section C: 快速导航
     - 查看本次详细变更: [COMPARE_LINK]
     - 查看提交详情: [COMMIT_LINK]
5) Output format
   - Render exactly the Telegram-friendly format as requested by the user and ensure all links are clickable.

Pitfalls & gotchas
- If HEAD~1 does not exist (fresh repo), guard against empty diffs.
- If origin URL parsing fails, skip GitHub links or fall back to a best-effort URL.
- If the auto_sync.sh takes long, consider running in background with notify-on-complete to return results.
- If brain-sync TG notifications should not interfere with wiki/webhook TG notifications, decouple delivery paths:
  - Keep wiki/webhook flow unchanged.
  - Set brain-sync cron delivery to local/non-Telegram at scheduler level.
  - Send brain-sync report via direct Telegram Bot API using a dedicated bot token + chat_id.
  - This preserves wiki behavior while isolating brain-sync sender identity.
- Telegram destination permissions still apply:
  - Private chat: user must have started the bot at least once.
  - Group/channel/topic: bot must be present and allowed to post.
- If bot token was exposed in chat/logs, rotate token before production use.

References
- `references/telegram-bot-separation.md` — dedicated bot strategy, prerequisites, and validation checklist.

Verification
- The output should include:
  - Non-empty Section A with concrete bullet points
  - Accurate counts for File changes, NEW files, and Modified files
  - Valid COMPARE_LINK and COMMIT_LINK
  - Hostname/time stamp in the final report (UTC)

Notes
- This is a class-level skill; it should not embed session-specific data by default. Session data should be captured in a dedicated references file.
- References: references/usage-example.md to aid reproducibility across sessions.\n- References: references/telegram-report-format.md to codify the Telegram report structure across sessions.

category: devops
description: |
  Class-level skill for Hermes Brain synchronization workflows. Automates: (1) repo sync, (2) commit data extraction, (3) GitHub link generation, (4) generation of Telegram-style reports. Encodes procedural steps, pitfalls, and verification. Reusable across Hermes sessions.
prerequisites:
  - Hermes brain repository at ~/hermes-brain
  - git installed and configured
  - Network access to GitHub
  - Access to the workspace environment
version: 0.2
---

# Brain Sync Workflow (Class-Level Skill)

Overview
- This skill standardizes the end-to-end flow to synchronize the Hermes brain repository, extract commit metadata, generate GitHub navigation links, and render a Telegram-friendly report.
- It is designed to be invoked across sessions and to produce a stable, reusable report structure that mirrors the user's requested format.

When to use
- You need to perform a Hermes brain sync from any host and return a ready-to-publish Telegram-style report.
- You want consistent formatting for Section A (Semantic insights), Section B (Detailed changes), and Section C (GitHub links).

Procedure (canonical steps)
1) Sync the brain
   - cd ~/hermes-brain && ./scripts/auto_sync.sh
   - Validate the sync completed (non-zero exit code indicates a problem).
2) Capture commit information
   - CURRENT: git log -1 --format "%H %h %s"
   - PREV: git log -1 HEAD~1 --format "%H"
   - ORIGIN: git remote get-url origin
   - DIFF_STAT: git diff HEAD~1 HEAD --stat
   - DIFF_CONTENT: git diff HEAD~1 HEAD --no-color | head -1000
3) Build GitHub links
   - From ORIGIN, extract owner/repo (assume https://github.com/owner/repo.git)
   - CURRENT_SHA = full SHA from CURRENT
   - PREV_SHA = PREV
   - Compare link: https://github.com/owner/repo/compare/PREV_SHA...CURRENT_SHA
   - Commit link: https://github.com/owner/repo/commit/CURRENT_SHA
4) Generate Telegram report (三个部分)
   - Section A: 核心摘要 (2-3 bullets) — use DIFF_CONTENT/DIFF_STAT to craft precise, non-vague insights.
   - Section B: 详细变更（保留原有格式）
     - 文件变更: X 个，Y 行(+)，Z 行(-)
     - 新增文件: [count] 个
       - path/to/file1
       - path/to/file2
     - 修改文件: [count] 个
       - path/to/updated1
       - path/to/updated2
   - Section C: 快速导航
     - 查看本次详细变更: [COMPARE_LINK]
     - 查看提交详情: [COMMIT_LINK]
5) Output format
   - Render exactly the Telegram-friendly format as requested by the user and ensure all links are clickable.

Pitfalls & gotchas
- If HEAD~1 does not exist (fresh repo), guard against empty diffs.
- If origin URL parsing fails, skip GitHub links or fall back to a best-effort URL.
- If the auto_sync.sh takes long, consider running in background with notify-on-complete to return results.
- If brain-sync TG notifications should not interfere with wiki/webhook TG notifications, decouple delivery paths:
  - Keep wiki/webhook flow unchanged.
  - Set brain-sync cron delivery to local/non-Telegram at scheduler level.
  - Send brain-sync report via direct Telegram Bot API using a dedicated bot token + chat_id.
  - This preserves wiki behavior while isolating brain-sync sender identity.
- Telegram destination permissions still apply:
  - Private chat: user must have started the bot at least once.
  - Group/channel/topic: bot must be present and allowed to post.
- If bot token was exposed in chat/logs, rotate token before production use.

References
- `references/telegram-bot-separation.md` — dedicated bot strategy, prerequisites, and validation checklist.

Verification
- The output should include:
  - Non-empty Section A with concrete bullet points
  - Accurate counts for File changes, NEW files, and Modified files
  - Valid COMPARE_LINK and COMMIT_LINK
  - Hostname/time stamp in the final report (UTC)

Notes
- This is a class-level skill; it should not embed session-specific data by default. Session data should be captured in a dedicated references file.
