# NotebookLM Processor Output Format Example

The `notebooklm_processor.py` script outputs a JSON object with the following structure:

```json
{
  "status": "success",
  "language": "zh_Hans",
  "shared_notebook": {
    "title": "youtube-video-research-wiki",
    "id": "a1443ac1-71d3-4dfd-8eab-0b9fb2da56c7"
  },
  "processed_urls": [
    {
      "url": "https://www.youtube.com/watch?v=NbldZVdusKo",
      "success": true,
      "notebook_id": "a1443ac1-71d3-4dfd-8eab-0b9fb2da56c7",
      "source_id": "3901b545-87db-4ff8-bd0f-b171a5461196",
      "report_path": "/tmp/notebooklm_processor/NbldZVdusKo_3901b545-87db-4ff8-bd0f-b171a5461196_20260509T010438Z_report.md",
      "mindmap_path": "/tmp/notebooklm_processor/NbldZVdusKo_3901b545-87db-4ff8-bd0f-b171a5461196_20260509T010438Z_mindmap.json",
      "error": null
    }
  ],
  "generated_files": [
    {
      "type": "report",
      "path": "/tmp/notebooklm_processor/NbldZVdusKo_3901b545-87db-4ff8-bd0f-b171a5461196_20260509T010438Z_report.md",
      "source_id": "3901b545-87db-4ff8-bd0f-b171a5461196",
      "language": "zh_Hans"
    },
    {
      "type": "mind-map",
      "path": "/tmp/notebooklm_processor/NbldZVdusKo_3901b545-87db-4ff8-bd0f-b171a5461196_20260509T010438Z_mindmap.json",
      "source_id": "3901b545-87db-4ff8-bd0f-b171a5461196",
      "language": "zh_Hans"
    }
  ],
  "errors": [],
  "summary": {
    "total": 1,
    "successful": 1,
    "failed": 0
  }
}
```

## ⚠️ Known Quirk: `.canvas` vs `.json` Discrepancy

**Observation (2026-05-09)**: The `generated_files[].path` for mindmaps always says `.json`, but the actual file on disk may be a `.canvas` file instead. For example:

| Field | Value |
|-------|-------|
| `generated_files[].path` (reported) | `/tmp/.../Kh8tGD5liwo_..._mindmap.**json**` |
| On-disk file (actual) | `/tmp/.../Kh8tGD5liwo_..._mindmap.**canvas**` |

This causes `cp` to fail (exit 1) if you naively use the path from the JSON output.

**Root cause**: NotebookLM's API returns mindmaps as Obsidian Canvas (`.canvas`) format. The processor's `generated_files` metadata hardcodes the `.json` extension regardless of what the API returns.

**Workaround**: Before copying a mindmap file:
1. Try the path from `generated_files[].path` first
2. If it doesn't exist, use `ls /tmp/notebooklm_processor/${VIDEO_ID}_*_mindmap.*` to find the actual file
3. Copy to destination with `.json` extension (canvas files are valid JSON)

## Key Points for Stage B

- The `generated_files` array contains all output files for this run only.
- **⚠️ CRITICAL**: Always use the exact paths from `generated_files[].path` when reading files. Do NOT use glob patterns like `/tmp/notebooklm_processor/Kh8tGD5liwo_*_report.md` — the `/tmp/notebooklm_processor/` directory accumulates files from ALL historical runs, and a glob will match stale files from previous invocations.
- Each item has a `type` field: either `"report"` or `"mind-map"`.
- The `path` field gives the absolute path to the temporary file (but see quirk above — the actual file may have a different extension).
- Files should be copied to the repository, renaming based on the Chinese title (first line `# 标题` of the report).

## Usage in SOP

In step 8 of the SOP, we call the processor and capture the JSON output. In step 9, we iterate over `generated_files` using the **exact paths** and copy each file to the appropriate directory:
- `report` → `raw/notebooklm-analysis/{title-slug}.md`
- `mind-map` → `raw/notebooklm-mindmaps/{title-slug}.json`

The report and mindmap for the same video must use **exactly the same title slug** so Stage C can correlate them.
