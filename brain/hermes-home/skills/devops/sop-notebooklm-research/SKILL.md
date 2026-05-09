---
name: sop-notebooklm-research
description: "SOP Stage B: 三阶段处理 YouTube 链接，调用 NotebookLM 生成深度研究报告和思维导图，push 到仓库触发 Stage C。"
version: 2.3.0
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
   # ⚠️ 使用 git fetch origin main（限制为 main 分支），防止 git fetch origin（取所有分支）
   # 导致后续 git pull --ff-only 报 "Cannot fast-forward to multiple branches"
   # 同时用 git reset --hard origin/main 替代 git pull，更稳定可靠
   git fetch origin main && git checkout main && git reset --hard origin/main
   if ! git stash pop 2>/dev/null; then
       git stash drop 2>/dev/null || true
   fi
   ```
   **坑**：`git fetch origin`（无分支限定）会 fetch 所有远程分支，当本地有多个远程跟踪分支时，后续的 `git pull --ff-only origin main` 可能因 refspec 模糊而报 `fatal: Cannot fast-forward to multiple branches`。修正：用 `git fetch origin main` 限定单个分支，并用 `git reset --hard origin/main` 而非 `git pull`。
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

7. 确保目录存在：
   ```bash
   mkdir -p {wiki_local_path}/raw/notebooklm-analysis {wiki_local_path}/raw/notebooklm-mindmaps logs/webhook-runs
   ```
   ⚠️ **不要删除现有分析文件**：Stage C 通过 `before-sha/sha` diff 过滤本次新增文件，旧文件不会被重复处理。并发场景下删除会导致另一个 Stage B 的输出被误删（竞态条件）。
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
9. 对每个生成文件，按以下规则**重命名后**复制到仓库（**推荐使用可复用脚本** `scripts/copy-and-rename-output.py`，也保留手动步骤供参考）：

   ### 🚀 推荐方式：使用可复用脚本（一步完成步骤 9-10）

   ```bash
   echo "$PROC_OUTPUT" | python3 /home/zhouhuijuan1987/.hermes/skills/devops/sop-notebooklm-research/scripts/copy-and-rename-output.py \
     - {wiki_local_path}
   ```

   脚本返回 JSON 摘要到 stdout，包含每个文件的状态、slug、路径和大小。若全部成功返回码 0，部分失败返回码 1。

   ⚠️ **脚本自动处理**：标题提取（跳过 frontmatter）、slug 生成、文件复制、.canvas/.json 后缀检查、JSON 合法性验证、frontmatter 中 mindmap_file 字段更新。

   ⚠️ **额外生成**：脚本会在 `raw/notebooklm-mindmaps/` 目录下自动生成一个**额外的 Mermaid 格式脑图 `.md` 文件**（供 Obsidian 原生渲染，无需插件）。此文件与 `.json` 脑图使用相同的 slug，内容为 ````mindmap` 代码块。`git add raw/notebooklm-mindmaps/` 会一并提交，Stage C 不会读取此 `.md` 文件（只读 `mindmap_file` 字段指向的 `.json`），所以无冲突。

   ### 📝 手动方式（当脚本不适用时）

   - ⚠️ **文件操作必须在 terminal 中执行，不得使用 execute_code 工具**：Hermes 的 `execute_code` 工具（Python execute_code）文件系统与真实终端隔离——通过 `shutil.copy2()`、`open().write()` 等操作创建的文件不会持久化到磁盘。所有文件读写、复制、重命名、frontmatter 修改必须通过 terminal 命令完成（如 `python3 << 'PYEOF'` 或多行 bash）。
   - **推荐做法**：用 heredoc 方式嵌入 Python 脚本到 terminal 执行：
     ```bash
     python3 << 'PYEOF'
     import shutil, re, json, os
     # 你的 Python 代码...
     PYEOF
     ```
   - ⚠️ **文件格式检查**：`generated_files[].path` 中的后缀可能不准确（实测 processor 返回 `.json` 但磁盘上实际文件为 `.canvas`）。复制前用 `ls` 验证文件是否存在，如果不存在则搜索实际文件：
     ```bash
     # 验证路径是否有效，无效则搜索实际文件（使用 video_id 前缀）
     if [ ! -f "/tmp/notebooklm_processor/${EXACT_FILENAME}" ]; then
       ls /tmp/notebooklm_processor/${VIDEO_ID}_*_mindmap.* 2>/dev/null
     fi
     ```
     找到实际文件后，无论原后缀是什么，目标名统一用 `.json`（因为 canvas 格式本身就是合法 JSON，适合 Stage C 解析）。
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

11b. **写入 pipeline-context.json**（供后续阶段读取）：
    - 路径：`{wiki_local_path}/raw/pipeline-context.json`
    - **关键决策：合并 vs 覆写取决于 pipeline_id 是否匹配**
      - 如果文件已存在且 `pipeline_id` **与当前 pipeline 相同**（同一 pipeline 的多 agent 并发场景）：读取已有内容，**追加**当前 stage_b 节点（保留其他 stage 的节点），用 `write_file` 写入合并后的完整 JSON
      - 如果文件不存在，或 `pipeline_id` **与当前不同**（新的 webhook trigger，不同 pipeline 运行）：**直接覆写**，用当前 pipeline 的信息创建全新的 pipeline-context.json
    - 简单判断方式：`read_file` 检查已有内容，解析 `pipeline_id`，对比当前 `pipe-{sha前7位}`。合并场景下保留旧 stage 节点；覆写场景下直接创建新文件
    - 注意：每次 webhook 触发都是新的 pipeline（不同 pipeline_id），所以**大多数情况下是覆写而非合并**。合并只在同一 pipeline 的多 agent 并发场景下发生
    - 模板：
    ```json
    {
      "pipeline_id": "pipe-{sha前7位}",
      "stage_b": {
        "run_id": "{run_id}",
        "start_time": "{START_TIME}",
        "end_time": "{END_TIME}",
        "duration_s": {DURATION},
api_calls: {从 hermes insights 查询本会话的 tool calls 数，若无法获取则写 unknown}
        "videos_processed": {处理的视频数量},
        "reports_generated": {生成的报告数},
        "mindmaps_generated": {生成的脑图数}
      }
    }
    ```
    - **必须用 write_file 工具写入**，不用 shell echo/heredoc
    - 在 `git add` 命令里加上 `raw/pipeline-context.json`

12. 用 write_file 工具写执行日志到 `{wiki_local_path}/logs/webhook-runs/{run_id}.md`，必须包含 frontmatter：
    ```yaml
    ---
    run_id: {run_id}
    stage: stage_b
    start_time: {START_TIME}
    end_time: {END_TIME}
    duration_s: {DURATION}
api_calls: {从 hermes insights 查询本会话的 tool calls 数，若无法获取则写 unknown}
    videos_processed: {处理的 URL 数量}
    status: success / partial / skipped
    ---
    ```
    以及正文内容：
    - `files_generated`：生成的文件列表（中文名）
13. **检查并提交所有变更**：
    ```bash
    cd {wiki_local_path}
    git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ raw/pipeline-context.json logs/
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
- **token 用量追踪**：webhook session 完成后，用 `hermes insights --days N` 查询本 session 的 input/output tokens。参见 youtube-wiki-processing skill 的 `references/pipeline-monitoring.md` 获取完整指南。

## ⚠️ 常见陷阱

### 1. /tmp/notebooklm_processor/ 目录污染
processor 将文件输出到 `/tmp/notebooklm_processor/`，该目录会**累积所有历史运行的文件**。使用 glob 通配符（如 `Kh8tGD5liwo_*_report.md`）会匹配到之前运行的旧文件。

**正确做法**：必须从 processor 返回的 JSON 中提取 `generated_files[].path` 的确切路径来读写文件，**不要用 glob 通配符**。

### 2. 分析目录遗留旧文件 + 捎带提交现象
如果前序 Stage B 运行未正常提交（如 push 失败后中断），`raw/notebooklm-analysis/` 和 `raw/notebooklm-mindmaps/` 中会留下属于之前 run 的未跟踪文件。当前 run 执行 `git add raw/notebooklm-analysis/` 时会**自然地将它们一并提交**（出现"8 files created"而非预期"3 files"的现象）。

**不要惊慌**——这是预期行为，Stage C 通过 `before-sha/sha` diff 准确过滤本次新增文件，旧文件不会被重复处理。提交中的额外文件是**装饰性 bloat，非功能性 bug**。

**正确做法（与 Step 7 一致）**：
- **不要**删除旧文件——并发场景下删除会导致另一个并发 Stage B 的输出被误删（竞态条件）
- 始终用 `git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ raw/pipeline-context.json logs/` 精确指定路径
- 不需要在 commit 前额外清理

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

### 8. 脑图文件后缀：`.json` vs `.canvas` 格式不匹配
processor 返回的 JSON 中 `generated_files[].path` 声明的后缀是 `.json`，但 NotebookLM 实际输出的脑图文件后缀是 `.canvas`（Obsidian Canvas 格式，本质是合法 JSON）。直接按 JSON 路径 `cp` 会因文件不存在而失败（exit code 1）。

**正确做法**：
- 用 `ls video_id_*_mindmap.*` 找到磁盘上的实际文件
- 用实际文件做源路径，目标名统一保存为 `.json`（Stage C 读取 `mindmap_file` 字段时得到的是 `.json`）
- 复制完成后用 `python3 -c "import json; json.load(open('dest'))"` 验证 JSON 合法性

**根本原因**：NotebookLM API 返回的 mindmap 格式随版本变化，processor 输出中的 `path` 后缀不一定反映磁盘真实内容。

### 9. pipeline-context.json 多 agent 并发覆写风险  
当 Hermes 在 multi-agent 模式下运行时（多个 subagent 同时执行同一 pipeline 的不同阶段），`pipeline-context.json` 可能被多个 agent 同时写入。`write_file` 工具的简单覆写会丢弃其他 agent 写入的数据。

**表现**：`write_file` 返回 warning `"pipeline-context.json was modified by sibling subagent ..."`。git diff 显示大量 deletions（如 `296 deletions`），说明旧 stage 的数据被覆盖了。

**正确做法**：
- 写入前先用 `read_file` 读取已有内容
- **检查 `pipeline_id` 是否与当前 pipeline 一致**：
  - **pipeline_id 匹配**（同一 pipeline 的多 agent）：用 Python 合并新旧数据（添加 stage_b 节点，保留其他 stage 的节点）
  - **pipeline_id 不匹配或文件不存在**（不同 pipeline 的 webhook 触发）：直接覆写，创建新文件
- 再用 `write_file` 写入合并后的完整 JSON（或新 JSON）
- 在 git add 时确认 `raw/pipeline-context.json` 出现在变更列表中且无意外删除

### 10. git stash push -u 无法捕获所有本地状态（残留变更污染提交）
`git stash push -u -m "sop-b-{run_id}"` 通常能 stash 工作区和暂存区变更，但以下组合会逃逸 stash，导致它们留在工作目录并在后续 commit 中被误提交：

- **index 中的删除（` D` 状态）** + **同名新未跟踪文件（`??` 状态）** — 这本质上是文件重命名操作（git 显示 rename），stash 无法正确将其归入"uncommitted changes"
- **仅 index 有记录的变更** — 如果文件已被 `git rm` 但尚未 commit，stash 的 `-u` 模式仅覆盖未跟踪文件目录，不覆盖 index-only 变更

**表现**：stash 输出 `No local changes to save`，但 `git status` 仍显示 ` D` 和 `??` 项。后续 commit 会将它们一并提交。

**解法**：
1. 在 stash 之前记录一份变更快照：`git status --porcelain > /tmp/sop-b-pre-stash-{run_id}.txt`
2. stash pop 后对比：区分预期变更与遗留变更
3. **关键做法**：始终用 `git add raw/notebooklm-analysis/ raw/notebooklm-mindmaps/ raw/pipeline-context.json logs/` 精确指定要提交的路径，**不要使用 `git add -A` 或 `git add .`**
4. 如果发现无关变更被意外 add 了，用 `git checkout -- <无关文件>` 丢弃工作区变更，用 `git reset HEAD <无关文件>` 取消暂存

### 11. pipeline-context.json 首次创建（文件不存在）
当首次执行 Stage B 时 `raw/pipeline-context.json` 尚不存在。`read_file` 可能返回空内容或 `File not found` 错误。

**正确做法**：
- `read_file` 返回空或文件不存在 → 直接创建新的 pipeline-context.json（`write_file` 创建新文件是安全的）
- 不要尝试解析空内容 → 避免 JSON 解析错误
- 不需要预先用 `read_file` 验证文件存在性；如 skill 所述，直接用 `write_file` 写入

### 12. execute_code 与 terminal 的文件系统行为差异
**⚠️ 环境差异警告**：不同 Hermes 部署环境下，`execute_code` 文件系统行为可能不同。以下指导基于已观察到的两种模式：

**模式 A（当前环境已验证）**：`execute_code` 的 Python 文件操作（`shutil.copy2()`、`open().write()`、`re.sub()` + write）**可以正常持久化到磁盘**，在 `git status` 和 `ls` 中可见。此环境下两种方式均可使用。

**模式 B（其他环境/历史版本）**：`execute_code` 使用沙盒文件系统，文件操作不落盘。必须通过 terminal 工具执行所有文件操作。

**避坑指南**：
1. **优先使用 terminal heredoc**：`python3 << 'PYEOF'` 方式在所有环境下都可靠，是推荐做法
2. **使用前验证**：如果不确定当前环境的行为模式，先做一个小测试——在 `execute_code` 中写一个临时文件，然后用 terminal 的 `ls` 检查是否存在
3. **始终可用的安全工具**：`write_file` 工具在所有环境下都能可靠持久化（如 pipeline-context.json 和日志文件）
