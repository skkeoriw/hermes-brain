---
name: brain-sync-reporting
version: 1.2.0

description: Standardized workflow for generating Telegram reports from Hermes brain sync events, including GitHub link construction and message formatting.
category: devops
---

# Brain Sync Telegram Reporting

Overview
- This umbrella skill defines the standardized process for producing Telegram reports after Hermes brain syncs, including how to derive GitHub links from the repository URL, how to format Section A/B/C for Telegram delivery, and how to handle common failure modes and fallbacks.
- It also catalogs session-level references and templates that improve consistency across cron-driven and ad-hoc reporting.

Core workflow
1. Collect synctime metadata and commit info from the local brain repo (HEAD, HEAD~1, diff stats).
2. Parse origin URL to determine owner/repo and build:
   - Compare link: https://github.com/OWNER/REPO/compare/PREV_SHA...CURRENT_SHA
   - Commit link: https://github.com/OWNER/REPO/commit/CURRENT_SHA
3. Assemble Telegram report payload with three sections (核心摘要, 详细变更, 快速导航) and the timestamp/host header.
4. Persist and share the report payload via the dedicated Telegram bot.

Robustness and fallbacks
- If auto_sync.sh fails due to remote origin issues, the system will attempt a graceful fallback by using a configured environment variable HERMES_ORIGIN_URL or by falling back to the last known SHAs captured locally.
- If the origin URL cannot be resolved, the report will still be generated using the last known SHAs (HEAD and HEAD~1) when available, and the Quick Navigation will indicate that GitHub links could not be resolved due to origin access failure.
- When possible, re-run sync with a explicitly configured origin URL via environment or config file, and re-derive owner/repo to restore full GitHub link precision.

Implementation notes
- The sophistication level of the links depends on the availability of a valid origin URL. If origin is missing, the links will be shown as placeholders until a successful fetch occurs.
- A dedicated references/template set is kept under references/ and templates/ to support consistent messaging.

Pitfalls and remedies
- Pitfall: Remote origin URL is misconfigured or inaccessible in the hosting environment. Remedy: set HERMES_ORIGIN_URL or fix git remote origin before retry.
- Pitfall: Large state DB diffs cause long reporting times. Remedy: rely on diff_stat and partial diffs when necessary; consider using Git LFS for large binary state files.
- Pitfall: Diff tailing exceeds local limits. Remedy: cap --no-color diff output and use --stat for high-level deltas, then dump selected hunks if needed.

Usage notes
- Intended for cron-generated reports, but usable in ad-hoc runs.
- The references/brain-sync-reporting.md document holds a runnable template and examples.

References
- brain-sync-reporting content is complemented by a detailed file at references/brain-sync-reporting.md
- New: templates/telegram-report-template.md (for quick bootstrapping of Telegram reports)

New Additions
- references/brain-sync-reporting.md
- templates/telegram-report-template.md

Note: This umbrella skill now includes concrete reference materials and a structured robustness section to guide future cron-driven reporting. See the new support files for templates and session-level references.

"""End of SKILL"""
