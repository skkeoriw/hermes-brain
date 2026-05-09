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
5. **Branch D – Pipeline complete** → Send Telegram notification

## Detailed Steps per Branch

每个分支由独立的 SOP skill 定义，下面的步骤是概要。完整细节（含陷阱、脚本示例、退出码约定）参见对应 SOP skill：

| 分支 | SOP Skill | 描述 |
|------|-----------|------|
| B | `sop-notebooklm-research` | NotebookLM 生成报告+脑图 |
| C | `sop-wiki-build` | 增量知识图谱编译 |
| D | `sop-tg-notify` | Telegram 通知 |

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
6. Git commit and push (⚠️ precision-add: use specific paths, NOT `git add -A`):
   ```bash
   git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ raw/pipeline-context.json logs/
   git commit -m "chore: add notebooklm analysis from {{url_count}} videos [run:{run_id}]"
   git push origin main
   ```
7. Log completion: `第一步成功，等待第二步自动触发`
8. Await automatic trigger for Branch C (via subsequent webhook or manual run)

### Branch C: Incremental Wiki Compilation (Triggered by changes in raw/notebooklm-analysis/ or raw/notebooklm-mindmaps/)
1. **Execute protective stash/sync workflow**:
   ```bash
   git stash push -u -m "youtube-wiki-stage-c-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   git stash pop 2>/dev/null || true
   ```
2. **Verify no conflicting YouTube link changes**: Run `git diff --name-only {before}..{sha} -- 'raw/youtube-links/' 'raw/youtube-links/**/*.md'`. If any YouTube links changed, this indicates the webhook should have triggered Branch B instead - log this discrepancy but continue with Branch C processing.
3. **Process NotebookLM analysis reports**:
   - For each new/changed report in `raw/notebooklm-analysis/`:
     * Update the corresponding source page in `wiki/sources/` to point to this report
     * Update the corresponding entity page in `wiki/entities/` to point to this report
4. **Process NotebookLM mindmaps**:
   - For each new/changed mindmap in `raw/notebooklm-mindmaps/`:
     * Parse the JSON mindmap to extract concept names
     * For each concept, create/update a concept page in `wiki/concepts/` with:
       - Proper frontmatter (type: concept, tags, summary, sources pointing to the mindmap, created/updated dates, layer: L1, confidence: high, reasoning: "直接从NotebookLM思维导图中提取的概念。")
       - Content including the concept description and links to related source/entity pages
       - Ensure minimum 2 outgoing [[wikilinks]]
       - Ensure content density (≥200 Chinese characters for concept pages)
5. **Language enforcement**: Ensure all generated content is in Chinese (zh_Hans). Set language explicitly before any NotebookLM operations if needed.
6. **Update navigation files**:
   - Update `index.md` (group by type, alphabetical order, with summaries, update "Last updated" and "Total pages")
   - Append to `log.md` with run_id, date, and list of new/updated files
7. **Quality checks** (must pass before commit):
   - Every wiki page must have complete frontmatter (type/tags/summary/sources/updated/layer)
   - L2/L3 pages must have confidence+reasoning fields
   - Every page must have minimum 2 outgoing [[wikilinks]]
   - Source pages: ≥300 Chinese characters
   - Entity/concept pages: ≥200 Chinese characters
   - All sources in frontmatter must point to existing raw/ files
8. **Git commit and push**:
   ```bash
   git add wiki/ index.md log.md logs/
   git commit -m "chore: update llm wiki graph from notebooklm analysis [run:{run_id}]"
   git push origin main
   ```
9. **Send Telegram notification** (only after successful push):
   ```
   [YOUTUBE-WIKI-RUN]
   action=wiki-build
   run_id={run_id}
   notebook=youtube-video-research-wiki
   language=zh_Hans
   raw_changed_count=<n>
   wiki_updates=<yes|no>
   commit=<hash>
   push=<success|failed>
   compile_check=<pass|fail>
   tg_send=<success|failed>
   run_log=<absolute_path>
   ```
10. **Log run** to: `logs/webhook-runs/{run_id}.md` with detailed execution record

## Pipeline Monitoring & Tracking

每个 pipeline 运行由三个独立 webhook session 组成（Stage B → C → D）。参见 `references/pipeline-monitoring.md` 获取完整的监控指南。

### 核心追踪手段

- **pipeline-context.json** (`raw/pipeline-context.json`)：记录每个阶段的 start_time/end_time/duration_s，由各阶段写入自己的节点
- **hermes insights**：各 webhook session 完成后可用 `hermes insights --days N` 查询每 session 的 input/output tokens
- **webhook run logs**：`logs/webhook-runs/{run_id}.md` 记录每个阶段的执行细节

### Webhook 路由架构

| 路由 | 阶段 | 状态 |
|------|------|------|
| `youtube-wiki-ops` | 主编排器 | 可能 disabled |
| `sop-notebooklm-research` | Stage B | 独立可触发 |
| `sop-wiki-build` | Stage C | 独立可触发 |
| `sop-tg-notify` | Stage D | 独立可触发 |

检查状态：`hermes webhook list`

### 按阶段手动触发（当编排器 disabled 时）

如果 `youtube-wiki-ops` 已禁用，可以手动触发每个 SOP webhook 来运行 pipeline：

1. 推送 YouTube link 文件 → 直接 git commit + push
2. 调用 `curl -X POST http://localhost:8644/webhooks/sop-notebooklm-research -H "Content-Type: application/json" -d '{...}'`
3. 等待 Stage B 完成并 push 后 → 调用 sop-wiki-build
4. 等待 Stage C 完成并 push 后 → 调用 sop-tg-notify

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