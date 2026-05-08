---
name: sop-notebooklm-research
description: "SOP Stage B: 处理 YouTube 链接，调用 NotebookLM 生成深度研究报告和思维导图，push 到仓库触发下一阶段。"
version: 1.0.0
---

# SOP Stage B: NotebookLM Research

## 触发条件
webhook 收到 `stage=notebooklm-research`

## 执行流程

### 准备
1. `cd {wiki_local_path}`
2. 保护性同步：
   ```bash
   git stash push -u -m "sop-stage-b-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   git stash pop 2>/dev/null || true
   ```
3. 计算 raw 变更（优先用 payload 的 before/sha，fallback 用 HEAD~1..HEAD）：
   ```bash
   git diff --name-only {before}..{sha} -- 'raw/*.md' 'raw/**/*.md'
   ```
4. 过滤出 `raw/youtube-links/` 下变更的文件。
5. 若无变更：写日志 `skipped:no_raw_changes`，停止执行。

### 处理
6. 从变更文件中提取 YouTube URL（正则：`https://youtu(\.)?be(\.com)?/[\w\-?=&]+`）。
7. 调用 NotebookLM processor（**必须用这个路径**）：
   ```bash
   python3 /home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py \
     <url1> <url2> ...
   ```
   processor 输出 JSON，包含 report_path 和 mindmap_path。
8. 将生成文件复制到仓库目录：
   - 报告 → `{wiki_local_path}/raw/notebooklm-analysis/{video_id}_report.md`
   - 脑图 → `{wiki_local_path}/raw/notebooklm-mindmaps/{video_id}_mindmap.json`

### 提交
9. 写执行日志到 `{wiki_local_path}/logs/webhook-runs/{run_id}.md`。
10. ```bash
    git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ logs/
    git commit -m "chore: add notebooklm analysis [run:{run_id}]"
    git push origin main
    ```
11. 验证 push 成功（`git status` 确认与 origin/main 一致）。

## 注意
- **不发送 Telegram**，Stage B 只负责处理和推送，由 Stage C 负责通知。
- git push 失败时重试一次，仍失败则记录错误停止。
