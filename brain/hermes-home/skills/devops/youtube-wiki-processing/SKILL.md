---
name: youtube-wiki-processing
description: Automated workflow for processing YouTube video research wiki updates via webhook triggers. Handles detection of raw changes, NotebookLM analysis generation, and incremental wiki compilation.
---
# YouTube Wiki Processing Flow

Automated workflow for processing YouTube video research wiki updates via webhook triggers. Handles detection of raw changes, NotebookLM analysis generation, and incremental wiki compilation.

## Pipeline Trigger Architecture

管道是完全自动触发的。以下是从 push 到所有阶段完成的完整流程：

```
GitHub push (raw/youtube-links/ 变更)
  │
  ▼
GitHub Actions (hermes-webhook-on-push.yml)
  │
  ├─ gate: git diff 检测 raw/ 是否有变更
  │  ├─ no raw change  → 跳过 (skipped:no_raw_changes)
  │  └─ raw changed    → 构建 payload 并调用 webhook
  │
  ▼
Hermes Webhook Server (localhost:8644)
  │
  ├─ youtube-wiki-ops 路由（主编排器，可能 disabled）
  │   └─ 如果 disabled → 不会处理，但 GitHub Actions 会失败
  │
  ├─ sop-notebooklm-research 路由（Stage B）
  │   └─ NotebookLM 生成报告+脑图 → push → 自动触发下一阶段
  │
  ├─ sop-wiki-build 路由（Stage C）
  │   └─ 增量知识图谱编译 → push → 自动触发下一阶段
  │
  └─ sop-tg-notify 路由（Stage D）
      └─ 发送 Telegram 通知
```

**关键要点**：
- 每个 push 都会触发 GitHub Actions workflow
- workflow 检测 `raw/` 目录变更后调用 webhook
- 每个 stage 完成后 push 自己的产物，**再次触发** workflow
- 所以 pipeline 是：push → Stage B → push → Stage C → push → Stage D

**如何验证管道在自动运行**：查看 git log 的提交链：
```bash
cd /home/zhouhuijuan1987/wiki/youtube-video-research-wiki
git log --oneline -20
# 寻找连续提交：Dify push → stage_b → stage_c → stage_d
```

### 关于 webhook disabled 的陷阱

`youtube-wiki-ops` 路由可能在 webhook_subscriptions.json 中被标记为 `"disabled": true`，但这**不代表 pipeline 不工作**。SOP 路由（`sop-notebooklm-research`、`sop-wiki-build`、`sop-tg-notify`）可能独立工作。

如果遇到 pipeline 不自动触发的问题，按以下顺序排查：
1. `hermes webhook list` — 检查各路由状态
2. 查看 GitHub Actions 日志 — 确认 workflow 是否正常执行
3. 手动触发 SOP webhook — 绕过编排器直接触发各阶段

### 从当前 session 手动触发 pipeline

当需要手动触发（例如编排器 disabled 或测试）：
1. push YouTube link → `git add raw/youtube-links/` → `git commit` → `git push`
2. **手动调用 SOP webhooks**：参见下方"按阶段手动触发"章节

## Pipeline Execution Tracking

### 从 git 历史追溯 pipeline 执行

```bash
cd /home/zhouhuijuan1987/wiki/youtube-video-research-wiki

# 查找最近 pipeline 的完整链（Dify push 的 commit）
git log --oneline -30

# 查找特定视频的 pipeline 链
git log --oneline -- 'raw/youtube-links/{video_id}.md'
git log --oneline --all --grep='{video_id}'

# 关联分析：找 Stage B → Stage C → Stage D 的连续提交
git log --oneline --grep='notebooklm analysis'
git log --oneline --grep='wiki graph'
git log --oneline --grep='tg notify'
```

### 通过 webhook run logs 查看执行细节

```bash
ls -lt /home/zhouhuijuan1987/wiki/youtube-video-research-wiki/logs/webhook-runs/
```

每个 run log 文件包含：start_time、end_time、duration_s、处理的 URL、生成的文件列表。

### 通过 pipeline-context.json 追踪跨阶段数据

`raw/pipeline-context.json` 由各阶段追加自己的节点：
- Stage B 写入: `stage_b.run_id`, `stage_b.start_time`, `stage_b.end_time`, `stage_b.duration_s`, `stage_b.api_calls`, `stage_b.videos_processed`
- Stage C 写入: `stage_c.run_id`, `stage_c.start_time`, `stage_c.end_time`, `stage_c.duration_s`, `stage_c.api_calls`, `stage_c.pages_created`
- Stage D 归档后删除

归档路径：`logs/pipeline-runs/pipe-{run_id}.json`

### Token 用量追踪

每个 webhook 触发的 Hermes session 会记录 token 消耗。完成后可用：

```bash
# 查看最近 1 天的所有 session（包括 webhook 触发的）
hermes insights --days 1

# 输出中会按平台分类：
# webhook: N sessions, X messages, Y tokens
# 各模型分类也可以查看
```

Token 追踪的限制：
- `hermes insights` 只给汇总（按平台/按模型），不给单个 session 的 token 明细
- pipeline-context.json 的 `api_calls` 字段在 stage_b 中通常记录为 `unknown`
- 精确追踪每个 session 的 token 需在 webhook session 内主动记录

参见 `references/pipeline-monitoring.md` 获取更详细的监控指南。

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