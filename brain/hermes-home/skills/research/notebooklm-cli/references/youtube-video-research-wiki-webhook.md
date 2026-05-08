# YouTube Video Research Wiki Webhook Integration Pattern

This document describes the pattern for integrating NotebookLM CLI with the youtube-video-research-wiki webhook system.

## Overview

The webhook processes GitHub pushes to the youtube-video-research-wiki repository and automatically:
1. Adds YouTube URLs from raw/youtube-links/ to NotebookLM notebooks
2. Generates reports and mind maps using NotebookLM CLI
3. Commits the generated content back to the repository
4. Triggers a second pass to compile the wiki knowledge graph

## Environment Variables

When triggered by Hermes webhook system, the following environment variables are available:
- `HERMES_SESSION_KEY`: Contains run identification info (format: `agent:main:webhook:webhook:webhook:qa-wiki-ops:gh-<run_id>-<attempt>:webhook:qa-wiki-ops`)
- Standard git variables may not be reliably available; extract from HERMES_SESSION_KEY when needed

## Key Extraction Pattern

```bash
# Extract run ID from HERMES_SESSION_KEY
RUN_ID=$(echo "$HERMES_SESSION_KEY" | grep -o 'gh-[0-9]*-[0-9]*')

# For git operations, use current HEAD and previous commit
SHA=$(git rev-parse HEAD)
BEFORE=$(git rev-parse HEAD^)

# Delivery ID may need to be extracted from webhook payload if available
```

## Workflow Implementation

See the llm-wiki-multiwiki-e2e-gate skill for the complete webhook processing logic, which includes:
1. Automatic stashing of local changes
2. Branch synchronization with origin/main
3. Change detection for raw/*.md files
4. Conditional processing based on file paths:
   - Scenario A: No raw changes → skip processing
   - Scenario B: YouTube links added → NotebookLM processing
   - Scenario C: NotebookLM analysis updated → wiki compilation

## NotebookLM CLI Usage Pattern

For each YouTube URL in raw/youtube-links/:
```bash
# Create notebook for video
notebooklm create "${video_title}" --json
NOTEBOOK_ID=$(jq -r .notebook.id)

# Add YouTube source
notebooklm source add "${youtube_url}" --json --notebook "$NOTEBOOK_ID"
SOURCE_ID=$(jq -r .source.id)

# Wait for source processing
notebooklm source wait "$SOURCE_ID" -n "$NOTEBOOK_ID"

# Generate report and mind map
notebooklm generate report --format briefing-doc -n "$NOTEBOOK_ID" --json
REPORT_ARTIFACT_ID=$(jq -r .task_id)

notebooklm generate mind-map -n "$NOTEBOOK_ID" --json
MAP_ARTIFACT_ID=$(jq -r .task_id)

# Wait for generation completion
notebooklm artifact wait "$REPORT_ARTIFACT_ID" -n "$NOTEBOOK_ID"
notebooklm artifact wait "$MAP_ARTIFACT_ID" -n "$NOTEBOOK_ID"

# Download results
notebooklm download report "./tmp/${video_title}_report.md" -a "$REPORT_ARTIFACT_ID" -n "$NOTEBOOK_ID"
notebooklm download mind-map "./tmp/${video_title}_map.json" -a "$MAP_ARTIFACT_ID" -n "$NOTEBOOK_ID"
```

## Error Handling

- Use `notebooklm auth check` to verify authentication before operations
- Check `notebooklm source list --json -n "$NOTEBOOK_ID"` for source processing status
- Check `notebooklm artifact list --json -n "$NOTEBOOK_ID"` for generation status
- Implement timeout handling for long-running operations (generation can take 10-45 minutes)

## Telegram Reporting

After successful wiki compilation (Scenario C), send Telegram notification with:
- Run ID and stage
- Lists of created entities, concepts, relations
- Commit hash and push status
- Link to run log file

## References

- TheSchema.md: Defines the wiki layout and conventions
- llm-wiki skill: General wiki compilation logic
- youtube-video-research-wiki repository: https://github.com/divanoo65/youtube-video-research-wiki