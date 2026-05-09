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
1. **记录开始时间**：`START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. `cd {wiki_local_path}`
2. 保护性同步：
   ```bash
   git stash push -u -m "sop-stage-b-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   # 尝试恢复存储的更改，如果有冲突则重置到 origin/main 并丢弃存储的更改
   if ! git stash pop 2>/dev/null; then
       echo "Warning: stash pop resulted in conflicts. Resetting to origin/main and dropping stash changes."
       git reset --hard origin/main
       git stash drop 2>/dev/null || true
   fi
   ```
3. 计算 raw 变更（优先用 payload 的 before/sha，fallback 用 HEAD~1..HEAD）：
   ```bash
   git diff --name-only {before}..{sha} -- 'raw/*.md' 'raw/**/*.md'
   ```
4. 过滤出 `raw/youtube-links/` 下变更的文件。
5. 若无变更：写日志 `skipped:no_raw_changes`，停止执行。

### 处理
6. 从变更文件中提取 YouTube URL（正则：`https://youtu(\\\\\\\\.)?be(\\\\\\\\.com)?/[\\\\\\\\w\\\\\\\\-?=&]+`）。
7. 确保目标目录存在：`mkdir -p {wiki_local_path}/raw/notebooklm-analysis {wiki_local_path}/raw/notebooklm-mindmaps`
8. 调用 NotebookLM processor（**必须用这个路径**）：
   ```bash
   python3 /home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py \\
     <url1> <url2> ...
   ```
   processor 输出 JSON，包含 `generated_files` 列表，每项包含 `type`（report 或 mind-map）和 `path`（绝对路径）。
9. 将生成文件复制到仓库，**并按以下规则重命名为中文语义文件名**：

   **重命名规则（必须执行）：**
   - 读取 report 文件第一行的 `# 标题`，提取中文标题
   - 清理标题中的特殊字符（保留中文、英文、数字、连字符），空格和标点替换为 `-`
   - 最终文件名格式：`{video_id}-{中文标题slug}.md`（report）或 `{video_id}-{中文标题slug}.json`（mindmap）
   - 示例：`Kh8tGD5liwo-零成本本地AI-Agent部署指南.md`

   **执行步骤：**
   - report 文件：读取第一行 `# 标题` → 生成 slug → 复制并重命名到 `{wiki_local_path}/raw/notebooklm-analysis/{video_id}-{slug}.md`
   - mindmap 文件：使用相同 slug → 复制并重命名到 `{wiki_local_path}/raw/notebooklm-mindmaps/{video_id}-{slug}.json`
   - 两个文件的 slug 必须完全一致（便于 Stage C 关联）

### 提交
10. **记录结束时间并计算耗时**：
    ```bash
    END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    DURATION=$(( $(date -d "$END_TIME" +%s 2>/dev/null || python3 -c "from datetime import datetime; print(int(datetime.strptime('$END_TIME','%Y-%m-%dT%H:%M:%SZ').timestamp()))") - $(date -d "$START_TIME" +%s 2>/dev/null || python3 -c "from datetime import datetime; print(int(datetime.strptime('$START_TIME','%Y-%m-%dT%H:%M:%SZ').timestamp()))") ))
    ```
11. 确保日志目录存在：`mkdir -p {wiki_local_path}/logs/webhook-runs`
12. 写执行日志到 `{wiki_local_path}/logs/webhook-runs/{run_id}.md`，**必须包含**：
    - `start_time`: START_TIME 的值
    - `end_time`: END_TIME 的值
    - `duration_seconds`: DURATION 的值（秒）
    - `videos_processed`: 本次处理的视频数量
12. ```bash
    git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ logs/
    git commit -m "chore: add notebooklm analysis [run:{run_id}]"
    git push origin main
    ```
13. 验证 push 成功（`git status` 确认与 origin/main 一致）。
    注意：git status 可能会显示来自以前运行的未跟踪文件，这是正常的，不影响本次提交。

## 注意
- **不发送 Telegram**，Stage B 只负责处理和推送，由 Stage C 负责通知。
- git push 失败时重试一次，仍失败则记录错误停止。
- 参考：references/notebooklm-processor-output.md 了解处理器输出格式。
