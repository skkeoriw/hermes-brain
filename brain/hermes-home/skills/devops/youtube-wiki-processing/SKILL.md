---
name: youtube-wiki-processing
description: Automated workflow for processing YouTube video research wiki updates via webhook triggers. Handles detection of raw changes, NotebookLM analysis generation, and incremental wiki compilation.
---
# YouTube Wiki Processing Flow

Automated workflow for processing YouTube video research wiki updates via webhook triggers. Handles detection of raw changes, NotebookLM analysis generation, and incremental wiki compilation.

## Trigger Conditions

- Webhook receives push event with changes to `raw/` directory
- Skill activates when user provides `run_id`, `before`, and `sha` git references
- Or when manually executing the flow for a given commit range

## Workflow Overview

1. **Detect change type** – check for modifications in raw Markdown files
2. **Branch A – No raw changes** → skip processing
3. **Branch B – YouTube links added/changed** → Run NotebookLM analysis on new videos
4. **Branch C – NotebookLM artifacts added** → Incremental wiki compilation and push

## Detailed Steps

### Step 1: Detect Changes
```bash
cd /home/zhouhuijuan1987/wiki/youtube-video-research-wiki
git diff --name-only <before>..<sha> -- 'raw/*.md' 'raw/**/*.md' > /tmp/changed_files.txt
```
- If file is empty or contains no paths → **Branch A** (skip)
- If any paths match `raw/youtube-links/` → **Branch B**
- If any paths match `raw/notebooklm-*` but **no** `raw/youtube-links/` → **Branch C**

### Branch A: No Raw Changes
- Log: `skipped:no_raw_changes`
- Stop processing; do not modify wiki, commit, or push
- Exit successfully

### Branch B: Process YouTube Links
1. Scan `raw/youtube-links/` for new/changed files
2. Extract all YouTube URLs using regex: `https://youtu(\.)?be(\.com)?/`
3. Call Python processor with all URLs:
   ```bash
   /home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py <url1> <url2> ...
   ```
4. Script outputs JSON with generated report and mindmap file paths
5. Move output files:
   - Reports → `raw/notebooklm-analysis/`
   - Mindmaps → `raw/notebooklm-mindmaps/`
6. Git commit and push:
   ```bash
   git add -A
   git commit -m "chore: add notebooklm analysis from {{url_count}} videos"
   git push origin main
   ```
7. Log completion: `第一步成功，等待第二步自动触发`
8. Await automatic trigger for Branch C (via subsequent webhook or manual run)

### Branch C: Incremental Wiki Compilation
1. Execute standard llm-wiki incremental compilation process
2. Scan changes in:
   - `raw/notebooklm-analysis/`
   - `raw/notebooklm-mindmaps/`
3. Generate/update wiki pages:
   - `wiki/sources/`
   - `wiki/concepts/`
   - `wiki/entities/`
4. Update relationship links
5. Git commit and push:
   ```bash
   git add -A
   git commit -m "chore: update llm wiki graph"
   git push origin main
   ```
6. Send Telegram notification:
   ```
   [YOUTUBE-WIKI-RUN] run_id=gh-<run_id>-<attempt> stage=completed commit=<hash> entities_created=<n>
   ```
7. Log run to: `logs/webhook-runs/gh-<run_id>-<attempt>.md`

## Logging
- Append all operations to `logs/webhook-runs/<run_id>.md`
- Include timestamps, commands executed, and outcomes

## Error Handling
- If any step fails, log error and exit non-zero
- For git failures, attempt to resolve conflicts or notify user
- For NotebookLM processor failures, skip commit and log details

## Requirements
- bash, git, python3
- notebooklm-cli skill (for NotebookLM operations via referenced script)
- Access to YouTube Wiki repository at `/home/zhouhuijuan1987/wiki/youtube-video-research-wiki`
- Telegram webhook configured for notifications

## Notes
- The flow assumes linear history; merge commits may require adaptation
- Processor script must be present and executable
- Ensure sufficient permissions for git push and file moves