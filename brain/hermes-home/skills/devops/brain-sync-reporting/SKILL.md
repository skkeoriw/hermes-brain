---
name: brain-sync-reporting
description: Standardized workflow for generating Telegram reports from Hermes brain sync events, including GitHub link construction and message formatting.
version: 1.0.0
author: Hermes Agent
license: MIT
category: devops
---

# Brain Sync Telegram Reporting

Overview
- This umbrella skill defines the standardized process and templates used to generate Telegram reports after Hermes brain-sync runs.
- It covers how to derive GitHub links from the repository URL, and how to format Section A/B/C for Telegram delivery.

Core workflow
1. Collect synctime metadata and commit info from the local brain repo (HEAD, HEAD~1, diff stats).
2. Parse origin URL to determine owner/repo and build:
   - Compare link: https://github.com/OWNER/REPO/compare/PREV_SHA...CURRENT_SHA
   - Commit link: https://github.com/OWNER/REPO/commit/CURRENT_SHA
3. Assemble Telegram report payload with three sections (核心摘要, 详细变更, 快速导航) and the timestamp/host header.
4. Persist and share the report payload via the dedicated Telegram bot.

Usage notes
- Intended for cron-generated reports, but usable in ad-hoc runs.
- The references/brain-sync-reporting.md document holds a runnable template and examples.

References
- brain-sync-reporting content is complemented by a detailed file at references/brain-sync-reporting.md

Note: This umbrella skill now includes a concrete reference doc to guide future reporters and to standardize the message formatting across sessions.