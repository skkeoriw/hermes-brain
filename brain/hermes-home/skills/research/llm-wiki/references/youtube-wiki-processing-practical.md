# YouTube Wiki Processing - Practical Session Notes

This document captures practical techniques and lessons learned from processing YouTube videos in the youtube-video-research-wiki repository (session: 2026-05-09).

## Stage Identification

In this wiki's webhook workflow:
- **Stage B**: Triggered by changes in `raw/youtube-links/` (YouTube links added/changed)
- **Stage C**: Triggered by changes in `raw/notebooklm-analysis/` or `raw/notebooklm-mindmaps/` (NotebookLM outputs generated)

**Important**: Only Stage C should send Telegram notifications, and only when raw changes resulted in actual wiki updates.

## File Naming Conventions

Observed in this repository:
- YouTube links: `raw/youtube-links/<video-id>.md` (contains just the URL)
- NotebookLM reports: `raw/notebooklm-analysis/<video-id>_<source-id>_<timestamp>_report.md`
- NotebookLM mindmaps: `raw/notebooklm-mindmaps/<video-id>_<source-id>_<timestamp>_mindmap.json`
- Timestamp format: `YYYYMMDDTHHMMSSZ` (UTC)

## Entity/Concept Extraction Techniques

When extracting insights from NotebookLM reports:

1. **Bold text in key points section**: Look for lines starting with `- **` 
   - Example: `- **幻觉率显著下降与逻辑修复**：模型能够发现并修正用户问题中的逻辑错误...`
   - Extract the entire line as a potential statement to add to wiki pages

2. **Section titles**: Lines starting with `## `
   - Filter for meaningful concept names like "幻觉率显著下降与自我修正能力", "对话自然度提升（“去机械化”）"

3. **Key quotes**: Lines starting with `> `
   - Often contain memorable phrases that can be converted to concepts

4. **Avoid noise**: Filter out:
   - Time-sensitive phrases (e.g., "精准建议：", "背景：")
   - Very generic terms
   - Colon-terminated labels that aren't substantive concepts

## Updating Existing Wiki Pages

When updating existing source/entity/concept pages:

1. **Preserve existing frontmatter**: Parse frontmatter carefully, only update:
   - `sources`: Append new report source if not already present
   - `updated`: Set to current date
   - Leave other fields (title, type, tags, summary, created, layer, confidence, reasoning) unchanged unless specifically needed

2. **Append new information**: Add a new section rather than overwriting
   - Section header: `## 来自最新视频的补充信息`
   - Content: Bulleted statements extracted from the report (see extraction techniques above)
   - Check if section already exists to avoid duplication

3. **Body preservation**: Keep all existing content, only append new insights

## Quality Control Checks (per TheSchema.md §6)

Before considering a run successful:

1. **Traceability**: Verify every wiki page's `sources` field points to existing `raw/` files
2. **Layer consistency**: L1 pages have no confidence/reasoning; L2/L3 pages have both
3. **Internal links**: Every wiki page must have ≥2 outgoing `[[wikilink]]`
4. **Frontmatter completeness**: All required fields present (type/tags/summary/sources/updated/layer, with confidence+reasoning for L2/L3)
5. **Content density**: 
   - Source pages: ≥300 Chinese characters
   - Entity/Concept pages: ≥200 Chinese characters
6. **Log completeness**: Run log written to `logs/webhook-runs/<run_id>-<attempt>.md`

## Telegram Message Requirements (Stage C only)

When sending Telegram notifications after successful Stage C:

```
[YOUTUBE-WIKI-RUN]
action=<action>
run_id=<run_id>
notebook=<notebook-name>
language=zh_Hans
raw_changed_count=<n>
wiki_updates=<yes|no>
commit=<hash>
push=<success|failed>
compile_check=<pass|fail>
tg_send=<success|failed>
run_log=<absolute_path>
```

Must include:
- Quantitative metrics: new entity names (≤5), changed raw source list
- Relation changes grouped by type (with ≥3 sample edges)
- Affected concept-page list (≤5 listed)
- Build commit hash and run-log file path

## Automation Considerations

1. **Source-scoped generation**: When generating reports/mindmaps from NotebookLM, use ONLY the newly added source(s) via `-s` or `--source` flags
2. **Language enforcement**: Always set `notebooklm language set zh_Hans` and use `--language zh_Hans` on generate commands
3. **Parallel safety**: Use explicit notebook IDs (`-n` flag) in automation contexts
4. **Error handling**: If extraction fails, log error but continue with available data