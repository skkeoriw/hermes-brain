---
name: sop-notebooklm-research
description: "SOP Stage B: 处理 YouTube 链接，调用 NotebookLM 生成深度研究报告和思维导图，push 到仓库触发下一阶段。"
version: 1.0.0
---

# SOP Stage B: NotebookLM Research

## 触发条件
- webhook 收到 `stage=notebooklm-research`

## 执行流程

### 准备阶段
1. 进入仓库：`cd {wiki_local_path}`
2. 保护性同步：
   ```bash
   git stash push -u -m "sop-stage-b-{run_id}"
   git fetch origin && git checkout main && git pull --ff-only origin main
   git stash pop
   ```
3. 计算 raw 变更：
   ```bash
   git diff --name-only {before}..{sha} -- 'raw/*.md' 'raw/**/*.md'
   ```
4. 过滤出 `raw/youtube-links/` 下的变更文件。
5. 若无变更：记录 `skipped:no_raw_changes`，停止。

### 处理阶段
6. 从变更文件中提取所有 YouTube URL（正则：`https://youtu(\.)?be(\.com)?/[\w\-?=&]+`）。
7. 调用 NotebookLM processor：
   ```bash
   python3 /home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py \
     <url1> <url2> ... \
     --language {notebooklm_language} \
     --notebook-title {notebooklm_notebook_title}
   ```
8. 获取输出的 report_path 和 mindmap_path。
9. 将文件复制到正确位置：
   - 报告 → `raw/notebooklm-analysis/{video_id}_report.md`
   - 脑图 → `raw/notebooklm-mindmaps/{video_id}_mindmap.json`

### 提交阶段
10. 写执行日志到 `logs/webhook-runs/{run_id}.md`（包含：开始时间、处理的 URL、生成的文件、git 操作结果）。
11. `git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ logs/`
12. `git commit -m "chore: add notebooklm analysis for {video_ids} [run:{run_id}]"`
13. `git push origin main`
14. 验证 push 成功（`git status` 确认 up to date）。

## 错误处理
- NotebookLM 失败：记录详细错误到 run-log，不 commit，返回失败。
- git push 失败：重试一次，仍失败则记录并返回失败。
- 不发送 Telegram（Stage B 不通知，Stage C 才通知）。

## 输出规范
执行完成后回复简要总结（中文）：
- 处理的 URL 列表
- 生成的文件列表
- git commit hash
- push 状态
