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

## Key Points for Stage B

- The `generated_files` array contains all output files.
- Each item has a `type` field: either `"report"` or `"mind-map"`.
- The `path` field gives the absolute path to the temporary file.
- Files should be copied to the repository preserving their original filenames (which already include a unique identifier).
- The processor ensures filename uniqueness via UUID and timestamp.

## Usage in SOP

In step 8 of the SOP, we iterate over `generated_files` and copy each file to the appropriate directory based on its `type`:
- `report` → `raw/notebooklm-analysis/`
- `mind-map` → `raw/notebooklm-mindmaps/`

No renaming is needed; the processor already generates unique, descriptive filenames.