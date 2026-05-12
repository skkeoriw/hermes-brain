# Brain Sync Telegram Reporting: Reference

This document provides session-level reference notes and concrete templates used during brain-sync Telegram reporting.

Session reference capture:
- When a sync runs, capture: HEAD, HEAD~1, and diff stats.
- Compute Compare link and Commit link using origin URL (OWNER/REPO).
- Build a final message payload with sections A/B/C as per SKILL.md.

Template notes:
- Template segments for Section A (核心摘要), Section B (详细变更), Section C (快速导航).
- Include precise diffs, added/removed file counts, and exact GitHub URLs.

Example links:
- Compare: https://github.com/OWNER/REPO/compare/PREV_SHA...CURRENT_SHA
- Commit: https://github.com/OWNER/REPO/commit/CURRENT_SHA
