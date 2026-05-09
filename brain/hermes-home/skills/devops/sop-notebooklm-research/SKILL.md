---
name: sop-notebooklm-research
description: "SOP Stage B: 三阶段处理 YouTube 链接，调用 NotebookLM 生成深度研究报告和思维导图，push 到仓库触发 Stage C。"
version: 2.0.0
---

# SOP Stage B: NotebookLM Research

## 触发条件
webhook 收到 `stage=notebooklm-research`

---

## Phase 1: Pre-Execution（准备阶段）

**目标：确认环境就绪，找出需要处理的 YouTube URL**

1. 记录开始时间：`START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. `cd {wiki_local_path}`
3. 保护性同步：
   ```bash
   git stash push -u -m "sop-b-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   if ! git stash pop 2>/dev/null; then
       git reset --hard origin/main && git stash drop 2>/dev/null || true
   fi
   ```
4. 用 `-c core.quotepath=false` 计算变更文件（防止中文路径被引号包装）：
   ```bash
   git -c core.quotepath=false diff --name-only {before}..{sha} -- 'raw/youtube-links/'
   ```
   fallback（若 before 无效）：`git -c core.quotepath=false diff --name-only HEAD~1..HEAD -- 'raw/youtube-links/'`
5. 从变更文件中提取 YouTube URL（支持 `youtu.be/`、`www.youtube.com/watch?v=` 和 `youtube.com/watch?v=` 三种格式）：
   ```bash
   grep -oP 'https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-?=&]+' {file}
   ```
   ⚠️ **常见坑**：简单正则 `youtu\.?be(\.com)?/[\w\-?=&]+` 无法匹配 `www.youtube.com/watch?v=...` 格式（缺 `www.` 前缀）。
6. **若无 URL**：写跳过日志到 `logs/webhook-runs/{run_id}.md`（标题 `skipped:no_youtube_links`），git add + commit + push 日志，停止执行。

---

## Phase 2: Action（核心处理）

**目标：调用 NotebookLM 生成分析文件，重命名为中文语义文件名**

7. 确保目录存在，**清理旧文件**（防止前序失败运行遗留的旧文件被误提交）：
   ```bash
   mkdir -p {wiki_local_path}/raw/notebooklm-analysis {wiki_local_path}/raw/notebooklm-mindmaps logs/webhook-runs
   # 清理本次运行之前的旧文件，只保留本次新生成的文件
   rm -f {wiki_local_path}/raw/notebooklm-analysis/*.md {wiki_local_path}/raw/notebooklm-mindmaps/*.json 2>/dev/null || true
   ```
8. 调用 processor（**固定路径，不可更改**）：
   ```bash
   python3 /home/zhouhuijuan1987/.hermes/scripts/notebooklm_processor.py <url1> <url2> ...
   ```
   ⚡ **后台执行**：processor 处理 3 个视频通常耗时 5-30 分钟。在 Hermes 中，inline terminal 超时上限为 600s。若超时，使用后台模式：`background=true` + `notify_on_complete=true` + `timeout=7200`。processor 运行期间可通过 `process` 工具 poll 或 wait 获取进度。

   processor 返回 JSON，包含 `generated_files` 列表，每项有 `type`（report / mind-map）和 `path`。

   **退出码约定**：
   - 0：全部成功（`status: success`）
   - 1：部分成功（`status: partial_success`）— 继续执行 Phase 3
   - 2：全部失败（`status: failed`）— 仍然执行 Phase 3 记录失败日志
9. 对每个生成文件，按以下规则**重命名后**复制到仓库：
   - **读取标题前需跳过 YAML frontmatter**：report 文件以 YAML frontmatter（`---`）开头，`# 标题` 位于 frontmatter 之后的第 1 行。以下命令可正确提取标题：
     ```bash
     grep -m1 '^# ' /tmp/notebooklm_processor/xxxxx_report.md | sed 's/^# //'
     ```
     或跳过 frontmatter 后取首个 `#` 行：
     ```bash
     awk '/^---/ {skip=!skip; next} !skip && /^# / {print; exit}' /tmp/notebooklm_processor/xxxxx_report.md | sed 's/^# //'
     ```
     使用 `head -1` 会返回 `---`，**不是标题**。
   - 清理特殊字符生成 slug：
     - **保留：** 汉字（Unicode `\u4e00`-`\u9fff`）、英文字母（a-z A-Z）、数字（0-9）
     - **替换为 `-`：** 中文标点（`：` `，` `。` `！` `？` `“` `”` 等）、英文标点、空格、符号
     - 合并连续 `-`、去除首尾 `-`
     - 截取前 40 字符
   - **最终文件名：直接用中文标题 slug，不加 video_id 前缀**
     - report → `{wiki_local_path}/raw/notebooklm-analysis/{中文标题}.md`
     - mindmap → `{wiki_local_path}/raw/notebooklm-mindmaps/{中文标题}.json`
   - report 和 mindmap 使用**完全相同的标题 slug**（便于 Stage C 关联）
   ⚠️ **典型错误**：中文全角冒号 `：`（U+FF1A）不是汉字，必须替换为 `-`。例如 `Hermes Agent 与 OpenClaw：深度对比` → `Hermes-Agent-与-OpenClaw-深度对比`

10. **重命名完成后，更新报告 frontmatter 里的 `mindmap_file` 字段**为实际的中文文件名：
    - 用 Python 或 sed 替换报告文件开头 `---` 块里的 `mindmap_file: xxx` 为 `mindmap_file: {中文标题}.json`
    - 示例（Python）：
      ```python
      import re
      with open(report_dest, 'r') as f: content = f.read()
      content = re.sub(r'^mindmap_file:.*$', f'mindmap_file: {slug}.json', content, flags=re.MULTILINE)
      with open(report_dest, 'w') as f: f.write(content)
      ```
    - 这确保 Stage C 读取 `mindmap_file` 时得到的是实际磁盘文件名，而不是原始临时文件名

11. 记录处理结果（每个 URL 的状态、生成的文件路径、最终文件名）。

---

## Phase 3: Post-Execution（提交阶段）⚠️ 强制执行

**目标：无论 Phase 2 是否完整，必须 commit + push**

> **此阶段独立于 Phase 2，即使 Phase 2 部分失败，也必须执行 Phase 3。**

11. 记录结束时间：`END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
12. 用 write_file 工具写执行日志到 `{wiki_local_path}/logs/webhook-runs/{run_id}.md`，必须包含：
    - `start_time` / `end_time`
    - `videos_processed`：处理的 URL 数量
    - `files_generated`：生成的文件列表（中文名）
    - `status`：success / partial / skipped
13. **检查并提交所有变更**：
    ```bash
    cd {wiki_local_path}
    git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ logs/
    if [ -n "$(git status --porcelain)" ]; then
      git commit -m "chore: add notebooklm analysis [run:{run_id}]"
    fi
    ```
14. **push，最多重试 3 次**：
    ```bash
    for i in 1 2 3; do
      git push origin main && break
      git pull --ff-only origin main
    done
    ```
15. 验证 push 成功：`git log --oneline -1` 确认本地 HEAD 与 origin/main 一致。

## 注意
- Stage B **不发送 Telegram**，通知由 Stage C 负责。
- push 全部失败时：在日志记录 `status: push_failed`，返回失败。

## ⚠️ 常见陷阱

### 1. /tmp/notebooklm_processor/ 目录污染
processor 将文件输出到 `/tmp/notebooklm_processor/`，该目录会**累积所有历史运行的文件**。使用 glob 通配符（如 `Kh8tGD5liwo_*_report.md`）会匹配到之前运行的旧文件。

**正确做法**：必须从 processor 返回的 JSON 中提取 `generated_files[].path` 的确切路径来读写文件，**不要用 glob 通配符**。

### 2. 分析目录遗留旧文件
如果前序 Stage B 运行未正常提交（如 push 失败后中断），`raw/notebooklm-analysis/` 和 `raw/notebooklm-mindmaps/` 中会留下属于之前 run 的文件。`git add` 时会一并提交。

**解法**：Step 7 中已加入 `rm -f` 清理步骤。如果手动处理，务必先清理旧文件再复制新文件。

### 3. 中文路径引号转义
`git diff --name-only` 需要加 `-c core.quotepath=false`，否则包含中文字符的文件名会被引号包裹导致提取失败。**Step 4 已处理此问题**，如果在其他地方用 `git diff` 处理中文路径也需注意。

### 4. 分析内容不变导致无变更可提交
NotebookLM 对同一视频的生成结果通常是确定性的。如果同一组 URL 在前序 run 中已处理且内容不变，`git status` 会显示无变更（仅日志文件是新的）。

**正确处理**：正常执行 Phase 3，git commit 会跳过（`if [ -n "$(git status --porcelain)" ]` 不满足），但日志和 push 仍正常进行。这不是错误，Stage C 检测到无分析的 raw 变更时会自行跳过。

### 5. Stage C 触发条件
Stage C 由新 push 触发。如果只有日志变更而无分析内容变更，Stage C 会在 Diff 检测阶段发现 `raw/notebooklm-analysis/` 和 `raw/notebooklm-mindmaps/` 无变化，直接跳过 KG 编译。

### 6. YAML frontmatter 导致标题提取失败
NotebookLM 生成的 report 文件包含 YAML frontmatter（`---` ... `---`）在 `# 标题` 之前。若直接 `head -1` 读取文件得到的是 `---`，而非标题。

**正确处理**：使用 `grep -m1 '^# '` 或 `awk` 跳过 frontmatter 提取标题行。详见 Step 9。

### 7. 脑图生成可能失败，但报告仍有效
RPC `GENERATE_MIND_MAP` 有时会因 NotebookLM 侧限流或超时而失败（尤其是连续处理多个视频时）。processor 返回 `partial_success`（exit 1），报告仍成功生成。

**正确处理**：不要重试或终止。带着已有文件继续 Phase 3，日志记录 `partial`。Stage C 会处理缺失脑图的视频（仅对报告建 KG，跳过脑图解构）。
