---
name: sop-tg-notify-new
description: "SOP Stage D: 读取 pipeline-context.json，组装完整 pipeline 运行报告，发送富文本 Telegram 通知。"
version: 2.1.0
---

# SOP Stage D: Pipeline TG Notification

## 触发条件
webhook 收到 `stage=tg-notify`

---

## Phase -1: 基础设施 — 阶段开始（仅记日志，不发 TG）

```bash
set -a && source ~/.agent-brain-plugins.env 2>/dev/null; set +a
START_TS=$(date +%s)
python3 ~/.agents/infrastructure/stage_runner.py on_start \
  --stage tg-notify \
  --wiki {wiki_local_path} \
  --run-id {run_id} \
  --extra '{"note": "final summary stage"}'
```

---

## Phase 0: 优先用标准脚本生成消息（推荐路径）

```bash
set -a && source ~/.agent-brain-plugins.env 2>/dev/null; set +a

TG_MESSAGE=$(python3 __SKILL_DIR__/scripts/build_tg_message.py {wiki_local_path} 2>/dev/null)
```

若脚本输出非空且不含 `❌`，直接用 `$TG_MESSAGE` 作为 TG 内容，**跳到 Phase 2 发送**，不需要走 Phase 1 的手动组装逻辑。

---

## Phase 1: Pre-Execution

1. 记录开始时间：`START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. `cd {wiki_local_path}`
3. 保护性同步：
   ```bash
   cd {wiki_local_path} && git fetch origin main && git checkout main && git reset --hard origin/main
   ```
   ⚠️ **此操作会覆盖所有未提交的本地修改（包括 Step 7 中可能已添加的 `video_url` 字段），并可能恢复/删除 source 文件。** 同步后立刻检查 `wiki/sources/` 目录状态再做 Step 7。
4. 读取 `raw/pipeline-context.json`，获取 stage_b 和 stage_c 的完整数据。
5. **检查完整性：** 确认 `stage_b` 和 `stage_c` 两个 key 都存在且非空。
   - 若文件不存在或 key 缺失：从 `logs/webhook-runs/` 读取最近两个 run-log 推断数据。
   - **⚠️ 重要：检查 run_id 一致性。** 读取 `stage_c.run_id`，与 webhook 传入的 `run_id` 比较。若不一致（如 webhook 传入 `gh-25857738504-1` 而 stage_c 是 `gh-25857680835-1`），**不要直接使用 webhook run_id**。记录不一致性信息后保留 stage_c 原始数据——Step 9 会从 stage_c 提取 run_id 供脚本归档使用。此检查确保不会被 webhook 的临时 run_id 绕过归档一致性逻辑。
   - 缺失 stage_b 时：先判断 pipeline 类型：
     - **YouTube pipeline（默认）：** 搜索 run-log 中 `stage: B` 或 `stage: notebooklm-research` 的记录，提取 `start_time`、`end_time`、`videos_processed`、`processed_urls`、`status` 等信息。也可从 `raw/youtube-links/` 读取源链接。
     - **GitHub pipeline：** 检查 `raw/github-links/` 目录。Read 每个 `.md` 文件，从正文提取实际 URL（**不限定 `https://github.com/...` 格式**——用户可能在此目录放置 arXiv/Web 等非 GitHub 链接）。构造最小 stage_b：
       ```json
       "stage_b": {
         "run_id": "<stage_c.run_id>",
         "status": "success",
         "processed_urls": ["https://github.com/owner/repo", ...],
         "videos_processed": <计数>
       }
       ```
     - **Reddit pipeline：** 检查 `raw/reddit-links/`（或 `raw/reddit/`）目录。Read 每个 `.md` 文件，从正文提取 Reddit URL（格式 `https://www.reddit.com/...`）。Reddit pipeline 通常没有独立的 stage_b run-log（stage_b 仅通过 git commit 添加源文件完成），此时使用 `stage_c.run_id` 作为 `run_id`。构造最小 stage_b：
       ```json
       "stage_b": {
         "run_id": "<stage_c.run_id>",
         "status": "success",
         "processed_urls": ["https://www.reddit.com/r/...", ...],
         "videos_processed": <计数>
       }
       ```
     - **arXiv pipeline：** 检查 `raw/arxiv-links/` 目录。Read 每个 `.md` 文件，从正文提取 arXiv URL（格式 `https://arxiv.org/abs/...`）。arXiv pipeline 通常没有独立 stage_b run-log（stage_b 仅通过 git commit 添加源文件完成），使用 `stage_c.run_id` 作为 `run_id`。构造最小 stage_b：
       ```json
       "stage_b": {
         "run_id": "<stage_c.run_id>",
         "status": "success",
         "processed_urls": ["https://arxiv.org/abs/XXXX.XXXXX", ...],
         "videos_processed": <计数>
       }
       ```
     - **Web link pipeline：** 先读取 `raw/pipeline-context.json` 的 `source_dir` 字段。若值为 `raw/web-transformed`，直接跳转到 web-transformed 目录查找 URL，跳过 web-links 的试探（web-links 可能只含 AI 摘要、不含 URL）。否则按以下流程：
       1. 检查 `raw/web-links/` 目录。Read 每个 `.md` 文件，从正文提取网页 URL（格式 `https://...` 且非 YouTube/GitHub/arXiv/Reddit）。
       2. **⚠️ 注意：`raw/web-links/` 下的源文件可能仅含 AI 提取的内容摘要，不含原始 URL。** 若在 web-links 文件中找不到 URL，改为检查 `raw/web-transformed/` 下文件名相似（或映射标题）的 `.md` 文件，从其中的 `**来源**:` 行提取实际 URL。
       3. **⚠️ 关键：多文件场景下确定当前 run 的 URL。** `raw/web-transformed/` 可能包含多次 run 累积的多篇文章。不要简单地把所有 URL 都放入 `processed_urls`。正确做法是用 `stage_c.run_id` 追踪当前 run 的 source 文件：
          - 读取 `wiki/sources/*.md` 文件，检查每个文件 frontmatter 的 `run_id` 字段
          - 找到 `run_id` 与 `stage_c.run_id` 匹配的 source 文件，记录其 `title`
          - 在 `raw/web-transformed/` 中找标题（`# 标题` 或 YAML frontmatter `title:`）与 source title 匹配的文件
          - 从匹配文件的 `**来源**:` 行提取当前 run 的实际 URL
          - 详见 `references/web-link-url-tracing.md`
       4. 构造最小 stage_b：
       ```json
       "stage_b": {
         "run_id": "<stage_c.run_id>",
         "status": "success",
         "processed_urls": ["https://example.com/article", ...],
         "videos_processed": 1
       }
       ```
       必须提供 `tg_summary`（见 Step 6b/6c），因为 `build_youtube_wiki_msg()` 无法处理 web 链接格式。使用 📄 图标而非 📹。
     - **直接内容 pipeline（direct-links）：** 检查 `raw/direct-links/` 目录。Read 每个 `.md` 文件，提取标题（`# 标题` 行或 YAML frontmatter `title:`）。这类文件是直接写入的内联内容（如 QA 问答、知识整理），**不含外部 URL**，`processed_urls` 设为空数组。构造最小 stage_b：
       ```json
       "stage_b": {
         "run_id": "<stage_c.run_id>",
         "status": "success",
         "processed_urls": [],
         "processed_sources": ["raw/direct-links/<filename.md>", "raw/direct-links/<filename2.md>", ...],
         "videos_processed": 0,
         "source_title": "<从文件提取的标题> 或 多文件拼接标题"
       }
       ```
       **多文件场景：** 当 `raw/direct-links/` 下有多个 `.md` 文件时：
       - `processed_sources` 列出所有文件路径
       - `source_title` 用 ` + ` 拼接所有标题，如 `"Harness Agent 架构设计问答精粹 + Pipeline 可靠性设计问答精粹"`
       - ❌ 不要只取第一个文件的标题——这会导致 TG 消息遗漏后续源文件信息
       必须提供 `tg_summary`（见 Step 6b/6c），因为 `build_youtube_wiki_msg()` 无法处理直接内容格式。使用 📚 或 📝 图标，`[KNOWLEDGE-QA]` 前缀。
     - **其他 pipeline / 无法判断：** 扫描 `raw/` 下所有子目录，寻找包含 URL 引用的源文件，提取处理对象列表。此时优先考虑提供 `tg_summary` 覆盖。
   - **注意：** 某些 pipeline 类型（如 Reddit、自定义）可能根本没有 stage_b run-log（stage_b 仅作为 git commit 添加源文件，非独立 pipeline stage）。此时不要空等 run-log——直接根据 `raw/` 子目录中的源文件构造最小 stage_b，`run_id` 复用 `stage_c.run_id`。
   - 缺失 stage_c 时：搜索 run-log 中 `stage: stage_c` 或 `stage: C` 的记录，提取 `pages_created`、`entities`、`concepts` 等信息。
6. **补充后写回 pipeline-context.json**：将补充的数据写入文件，确保脚本读取到完整内容。
   - **⚠️ 编码陷阱：write_file 中文智能引号破坏 JSON。** 原始 pipeline-context.json 中的中文文本可能包含 Typographic/智能引号（`""` U+201C/U+201D，`''` U+2018/U+2019），它们在 JSON 字符串中是有效的。但当通过 LLM 输出 → write_file 回写时，这些字符可能被归一化为 ASCII 双引号（`"` U+0022），导致 JSON 解析失败（`Expecting ',' delimiter` 错误）。**修复方案：** 写回前，对含中文引号的 JSON 字符串值中的 `""`/`''` 替换为 Unicode 转义序列（`\u201c`/`\u201d`/`\u2018`/`\u2019`），或在回写后用 `patch` 验证 JSON 合法性。写入后务必用 `python3 -c "import json; json.load(open(...))"` 验证 JSON 可解析。

6b. **（关键）非 YouTube pipeline 使用 `tg_summary`：**
   - 脚本 `sop_tg_notify.py` 读取 pipeline-context.json 后，**优先检查 `tg_summary` 字段**。若存在，直接将其作为 Telegram 消息内容发送，跳过 `build_youtube_wiki_msg()` 的 YouTube 专用逻辑。
   - **在以下情况，必须提供 `tg_summary`：**
     - pipeline 处理的是 GitHub 仓库（而非 YouTube 视频）—— `build_youtube_wiki_msg` 生成的 🔗 行、📹 行均不适用
     - pipeline 处理的是 **arXiv 论文**（`raw/arxiv-links/`）—— 📹 图标和 video_url 匹配逻辑不适用，但 📄 图标更适合
     - pipeline 处理的是 Reddit 讨论—— `build_youtube_wiki_msg` 无法处理 Reddit 格式的 source
     - pipeline 输出自定义格式的 wiki（如 MCP server 文档、research blog 等）
     - 你想完全控制 TG 消息的措辞和布局
   - **tg_summary 编写要点：**
     - 使用纯文本 + emoji，无需 Markdown 格式（TG 使用 `disable_web_page_preview=true`）
     - 建议结构：`[PIPELINE-TYPE] #任务ID 状态标识` → 核心处理对象 → 时间/Token统计 → 知识图谱产出 → 仓库入口链接 → `run_id`
     - 参考下方「tg_summary 模板」及 `references/mixed-content-tg-summary-example.md`（混合内容场景实战示例）
   - **⚠️ Write-file 注意事项：** write_file 写入 pipeline-context.json 后，建议 `cat raw/pipeline-context.json` 确认写入成功（实测发现个别环境下 write_file 与 terminal 可能不同步）。确认后再调用脚本。

6c. **tg_summary 模板（GitHub 研究 pipeline）：**
   ```json
   "tg_summary": "[GITHUB-RESEARCH] #T-{run_id} ✅ 一遍过\n\n📦 {repo_name}\n🔗 https://github.com/{owner}/{repo}\n\n⏱️ 耗时：Stage C {duration_s}s\n🔢 Token：{total_tokens:,}（↑{prompt:,} / ↓{completion:,}）\n\n📊 知识图谱：\n  Source {sources} / Entity {entities} / Concept {concepts} / 总 {pages} 页\n\n🟢 Entities：\n{entity_list_bullets}\n\n🟡 Concepts：\n{concept_list_bullets}\n\n🔗 入口：\n  · {source_title}\n    {repo_url}/blob/main/wiki/sources/{source_filename}\n  · 知识图谱索引\n    {repo_url}\n\nrun_id: {run_id}"
   ```

   **tg_summary 模板（Web link 研究 pipeline）：**
   ```json
   "tg_summary": "[WEB-LINK] ✅ 一遍过\n\n📄 {article_title}\n🔗 {article_url}\n\n⏱️ 耗时：Stage C {duration_s}s\n🔢 Token：{total_tokens:,}（↑{prompt:,} / ↓{completion:,}）\n\n📊 知识图谱：\n  Source {sources} / Entity {entities} / Concept {concepts} / 总 {pages} 页\n\n🟢 Entities：\n{entity_list_bullets}\n\n🟡 Concepts：\n{concept_list_bullets}\n\n🔗 入口：\n  · {source_title}\n    {repo_url}/blob/main/wiki/sources/{source_filename}\n  · 知识图谱索引\n    {repo_url}\n\nrun_id: {run_id}"
   ```
   **注意：** `article_title` 从 web-link 源文件的 `# 标题` 行或 `title:` YAML frontmatter 提取。`article_url` 优先从 `raw/web-links/` 源文件正文提取；若找不到 URL，则从 `raw/web-transformed/` 同名文件的 `**来源**:` 行提取。
   **注意（累积 vs 增量计数）：** `tg_summary` 模板中的 `{sources}`、`{entities}`、`{concepts}`、`{pages}` 应使用**累积值**（当前 wiki 中该类型文件的总数），而非 stage_c 的增量值（`sources_new`、`entities_new`、`concepts_new`、`pages_created`）。查看上一轮归档 `logs/pipeline-runs/pipe-{prev_run_id}.json` 的 tg_summary 可确认累积值基线，再用 `find wiki/ -name '*.md' | wc -l` 获取总页数。entities 和 concepts 的列表（🟢/🟡 部分）也使用**全量列表**（所有累计 entity/concept 名称），而非仅当前新增的。

   **tg_summary 模板（arXiv 研究 pipeline）：**
   ```json
   "tg_summary": "[ARXIV-RESEARCH] ✅ 一遍过\n\n📄 {paper_title}\n🔗 https://arxiv.org/abs/{arxiv_id}\n\n⏱️ 耗时：Stage C {duration_s}s\n🔢 Token：{total_tokens:,}（↑{prompt:,} / ↓{completion:,}）\n\n📊 知识图谱：\n  Source {sources} / Entity {entities} / Concept {concepts} / 总 {pages} 页\n\n🟢 Entities：\n{entity_list_bullets}\n\n🟡 Concepts：\n{concept_list_bullets}\n\n🔗 入口：\n  · {source_title}\n    {repo_url}/blob/main/wiki/sources/{source_filename}\n  · 知识图谱索引\n    {repo_url}\n\nrun_id: {run_id}"
   ```

   **tg_summary 模板（Knowledge-QA / direct-links pipeline）：**
   ```json
   "tg_summary": "[KNOWLEDGE-QA] ✅ 一遍过\n\n📚 {source_title}\n\n⏱️ 耗时：Stage C {duration_s}s\n🔢 Token：{total_tokens:,}（↑{prompt:,} / ↓{completion:,}）\n\n📊 知识图谱：\n  Source {sources} / Entity {entities} / Concept {concepts} / 总 {pages} 页\n\n🟢 Entities：\n{entity_list_bullets}\n\n🟡 Concepts：\n{concept_list_bullets}\n\n🔗 入口：\n  · {source_title}\n    {repo_url}/blob/main/wiki/sources/{source_filename}\n  · 知识图谱索引\n    {repo_url}\n\nrun_id: {run_id}"
   ```
   **注意：** `direct-links` 文件无外部 URL，`processed_urls` 为空数组，`source_title` 从文件 `# 标题` 或 YAML frontmatter `title:` 提取。📚 图标比 📹/📄 更合适。
   **注意（多文件场景）：** 当有 2+ 个 direct-links 源文件时，🔗 入口 部分列出所有 source 的入口行，`source_title` 用 ` + ` 拼接。示例结构：
   ```
   📚 源A + 源B
   
   ...
   
   🔗 入口：
     · 源A 标题
       {repo_url}/blob/main/wiki/sources/{sourceA_filename}
     · 源B 标题
       {repo_url}/blob/main/wiki/sources/{sourceB_filename}
     · 知识图谱索引
       {repo_url}
   ```

7. **（推荐）补齐 source 文件 `video_url` 字段 + `processed_urls`：**
   - **如果使用了 `tg_summary`（Step 6b）：** 此步骤自动跳过——tg_summary 中的内容由你完全控制，不需要脚本去匹配 source frontmatter 中的 `video_url:` 字段。直接跳到 Step 8。
   - **先检查 sources 目录是否为空：** `ls wiki/sources/*.md 2>/dev/null | head -1`
     - 若无任何 `.md` 文件（仅剩 `.gitkeep`）：说明 sources 已被 benchmark 清理或前序 stage 清除。**跳过此步**，脚本会使用 fallback 逻辑（读 run-log 匹配分析文件）；TG 通知将无法显示 source 详情（只显示 stage_c 统计数字）。
     - 若有 source 文件：继续执行以下步骤
   - 从 stage_b 的 `processed_urls` 或 run-log 中获取本次处理的视频 URL
   - **确定目标 source：** 读取 stage_b run-log 的 "Files Generated" 表格，找到 report 文件路径（如 `raw/notebooklm-analysis/xxx.md`），取文件名（不含路径和扩展名）去 `wiki/sources/` 目录匹配同名的 `.md` 文件。注意：`wiki/sources/` 下可能有历史 source，只有文件名与本次报告匹配的才是目标。
   - 检查目标 source 的 frontmatter 是否有 `video_url:` 字段
   - 若缺失：手动添加 `video_url: <YouTube 干净 URL>` 到 frontmatter（确保 TG 通知 🔗 行显示完整链接）
     - **⚠️ URL 格式：** 使用无追踪参数的干净 URL（去掉 `?si=...`、`&feature=...` 等），例如 `https://youtu.be/4kgkYAGPuD0`。脚本匹配逻辑是 `any(video_url in u or u in video_url for u in processed_urls)`，干净 URL 是带参 URL 的子串，可确保匹配成功。
   - 若 stage_b 缺少 `processed_urls`：从 run-log 中提取后补写入 pipeline-context.json
   - **原因：** 脚本用 `video_url` 匹配 processed_urls。若 frontmatter 无 `video_url`，TG 消息中图标行 🔗 URL 为空；若 processed_urls 缺失，脚本 fallback 只显示最近 1 个 source

8. **（新增）清理 stale output-check-result.json：**
   - 检查 `raw/output-check-result.json` 是否存在
   - 若存在，读取其 `run_id` 字段，与当前 pipeline 的 stage_c `run_id` 比较
   - **若 run_id 不匹配**（说明是之前 pipeline 的遗留数据）：`rm raw/output-check-result.json`
   - **原因：** 脚本 `load_output_check()` 无 run_id 校验，只要文件存在就加载。旧 pipeline 的 QC 数据会导致 TG 通知中显示错误的 ✅/❌ 结果。

---

## Phase 2: Action（调用 Python 脚本发送通知，无需 LLM）

9. **确定 run_id：** 优先使用 `stage_c.run_id`（即 pipeline-context.json 中 stage_c 段的 run_id），而非 webhook 触发时传入的 run_id。TG notify 作为独立 GitHub Action 触发时自带新 run_id，但归档文件名（`pipe-{run_id}.json`）、run-log 文件名（`{run_id}.md`）和 commit message 应基于**实际数据处理**的 run_id，以确保跨阶段可追溯。
   ```bash
   RUN_ID=$(python3 -c "import json; print(json.load(open('raw/pipeline-context.json'))['stage_c']['run_id'])")
   ```

9. 调用 sop_tg_notify.py：
   ```bash
   python3 __SKILL_DIR__/scripts/sop_tg_notify.py \
     --wiki-path {wiki_local_path} \
     --run-id "${RUN_ID}" \
     --tg-token-env {tg_token_env} \
     --tg-chat-id {tg_chat_id} \
     --repo-url {repo_url}
   ```

   该脚本会：
   - 读取 raw/pipeline-context.json（B+C 完整数据）
   - 组装富文本 Telegram 消息
   - 发送通知
   - 归档 pipeline-context.json 到 logs/pipeline-runs/**（命名：`pipe-{run_id}.json`，而非 `pipe-{pipeline_id}.json`）**
   - 写 run-log 到 logs/webhook-runs/（命名：`{run_id}.md`）
   - git commit + push

10. 任务完成，无需其他操作。

---

## Phase 3: Post-Execution（强制执行）

11. 检查脚本输出确认 TG 发送状态（`TG sent: True/False`）。
12. **验证产出物：**
    - 确认 `logs/pipeline-runs/pipe-{run_id}.json` 已创建（归档文件）
    - 确认 `logs/webhook-runs/{run_id}.md` 已创建（run-log）
    - 确认 git log 中有新的 commit（如 `chore: tg notify done [run:{run_id}]`）
13. **git commit/push、归档、run-log 均由脚本处理，跳过手动执行。**

## 注意
- TG 发送失败：记录错误，不影响整体，仍然执行 git 归档。
- pipeline-context.json 不存在：退化到读 run-log 文件。
- **退化再退化（双重缺失）：** pipeline-context.json 和 run-logs 都为空/不存在时：
  - **YouTube pipeline：** 从 `raw/youtube-links/` 直接读取视频链接，通过 YouTube oembed API (`https://www.youtube.com/oembed?url=...&format=json`) 获取标题。此时编排"未完整执行"状态通知，标注 Stage B/C 未执行，发送 Telegram 告知当前进展。
  - **GitHub pipeline：** 从 `raw/github-links/` 读取仓库链接，取文件名作为仓库名（如 `anthropics-claude-code.md` → `anthropics/claude-code`）。此时编排"部分执行"通知（仅 Stage C 已完成）。
  - **arXiv pipeline：** 从 `raw/arxiv-links/` 读取论文链接，取文件名作为论文别名。编排"部分执行"通知（仅 Stage C 已完成），使用 `[ARXIV-RESEARCH]` 前缀。
  - **直接内容 pipeline（direct-links）：** 从 `raw/direct-links/` 读取内容文件，取文件名（去掉 `.md` 后缀）作为标题别名，通过 YAML frontmatter 或 `# 标题` 行提取实际标题。编排"部分执行"通知（仅 Stage C 已完成），使用 `[KNOWLEDGE-QA]` 前缀，提供 tg_summary 覆盖。
  - **其他 pipeline / 无法判断：** 扫描 `raw/` 下所有子目录的 `.md` 文件，尝试提取 URL 链接。编排"状态不明"通知，使用 `[PIPELINE-UNKNOWN]` 前缀。
  - **Web link pipeline：** 从 `raw/web-links/` 读取链接文件，取文件名作为文章别名（如 `managed-agents.md` → Managed Agents），通过 GitHub raw URL 或本地文件读取标题。编排"部分执行"通知（仅 Stage C 已完成），使用 `[WEB-LINK]` 前缀，提供 tg_summary 覆盖。
- 归档阶段：pipeline-context.json 不存在时，仍应创建最小归档文件 `logs/pipeline-runs/pipe-{run_id}.json`，记录 run_id、各 stage 状态和 tg 通知结果。

## Pitfalls
- **arXiv pipeline / 无 stage_b run-log 的场景：** 当 pipeline 处理的是 arXiv 论文（`raw/arxiv-links/`），且 stage_b 从未作为独立 pipeline stage 执行（仅通过 git commit 添加源文件），不会有 stage_b run-log。**修复：** 不要搜索 run-log——直接从 `raw/arxiv-links/` 读取源文件提取 arXiv ID 和标题，构造最小 stage_b。必须提供 `tg_summary`（见 Step 6b/6c），因为 `build_youtube_wiki_msg()` 无法处理 arXiv 格式。使用 📄 图标而非 📹。
- **Reddit pipeline / 无 stage_b run-log 的场景：** 当 pipeline 处理的是 Reddit 讨论（`raw/reddit-links/`），且 stage_b 从未作为独立 pipeline stage 执行（仅通过 git commit 添加源文件），不会有 stage_b run-log。**修复：** 不要搜索 run-log——直接从 `raw/reddit-links/` 读取源文件提取 URL，构造最小 stage_b。必须提供 `tg_summary`（见 Step 6b/6d），因为 `build_youtube_wiki_msg()` 无法处理 Reddit 格式。
- **pipeline-context.json 部分缺失：** 文件存在但只包含 stage_c（stage C 会覆盖重写），stage_b 数据丢失。必须从 run-logs 手动补充后再执行脚本。
- **source 文件缺少 video_url 字段：** `wiki/sources/*.md` 的 YAML frontmatter 通常没有 `video_url:` 字段（视频 URL 在正文中写为 `- **视频 URL**: ...`）。这会导致脚本中 `video_url` 匹配为空字符串，消息中 🔗 行的 URL 为空。**修复：** 在 Phase 1 Step 7 中主动添加 `video_url:` 到 frontmatter。
- **processed_urls 匹配逻辑：** 脚本用 `any(video_url in u or u in video_url for u in processed_urls)` 匹配，所以即使 `video_url=""`，`"" in u` 永远为 True，所有 source 都会被加入。这可能导致显示非本次处理的历史 source。**修复：** 在 Phase 1 Step 7 中确保 `processed_urls` 已写入 stage_b，且 source frontmatter 有正确的 `video_url`。
- **stale output-check-result.json：** `raw/output-check-result.json` 可能来自之前无关的 pipeline 运行，run_id 与当前 pipeline 不匹配。脚本 `load_output_check()` 无校验直接加载，导致 TG 通知显示错误的 QC verdict。**修复：** 在 Phase 1 Step 8 中检查并清理。
- **sources 目录被 benchmark 清空：** 当 `wiki/sources/` 仅剩 `.gitkeep`（或完全为空）时，脚本 `build_youtube_wiki_msg()` 的 sources-matching 逻辑匹配不到任何文件。即便 `processed_urls` 已设置，fallback 也只能从**一个** run-log（`stage_b.run_id` 指向的那个）提取分析文件列表。若 pipeline 处理了多个视频（如 benchmark 模式合并处理），只有该单次 run-log 的 source 信息会显示。**修复：** 在 Phase 1 Step 7 顶部做 sources 存在性检查，提前识别此情况并在 TG 通知中接受显示局限性。
- **git reset 抹掉 source 修改：** Step 3 的 `git reset --hard origin/main` 会丢弃所有未提交工作区改动。若之前已有 `video_url` 追加或其他准备，reset 后全部丢失。**修复：** 在 Step 7 前重新检查 `wiki/sources/` 文件状态，如有需要重新 patch。严重情况下（被 benchmark 清理），参考上一条 pitfall。
- **单 run-log fallback 局限：** 当 `stage_b` 聚合了多个独立 run-log 的数据（尤其是 `processed_urls` 包含多个视频），但 `stage_b.run_id` 只指向其中之一时，脚本的 run-log fallback（`processed_urls and not sources and sources_dir.exists()` 分支）只能通过这一个 run-log 匹配分析文件。其他视频的 source 不会显示。**考虑方案：** 若时间允许，手动从所有相关 run-log 提取 analysis stems 并建立占位 source 文件。否则接受显示局限性。
- **非 YouTube pipeline 使用 YouTube fallback：** `build_youtube_wiki_msg()` 是 YouTube 专用逻辑，会搜索 `wiki/sources/*.md` frontmatter 中的 `video_url:` 字段，并构造 📹/🔗 行。对于 GitHub 研究 pipeline、arXiv 论文 pipeline、Reddit pipeline 等，这些字段不存在，导致:
  - Source 匹配失败（无 `video_url`），只显示 fallback 1 个 source
  - 🔗 URL 行可能为空或不准确
  - 📊 统计数字是正确的（读自 stage_c），但整体消息格式不匹配
  **修复：** 在 Step 6b 中主动提供 `tg_summary` 字段，完全避开 YouTube 格式.
- **Web link pipeline / 无 stage_b run-log 的场景：** 当 pipeline 处理的是 web 文章（`raw/web-links/`），stage_b 通常仅通过 git commit 添加源文件完成（无独立 pipeline stage 执行），不会有 stage_b run-log。**修复：** 不要搜索 run-log——直接从 `raw/web-links/` 读取源文件，从 YAML frontmatter 或正文提取 URL 和标题。**⚠️ 但 `raw/web-links/` 下的源文件可能不含原始 URL（仅 AI 提取的摘要内容）。** 若 web-links 文件正文不含 `https://...` URL，需回退到 `raw/web-transformed/` 目录查文件名相似的文件，从 `**来源**:` 行提取 URL（标题从 `# 标题` 或 `title:` frontmatter 取）。构造最小 stage_b。必须提供 `tg_summary`（见 Step 6b/6c），因为 `build_youtube_wiki_msg()` 无法处理 web 文章格式。使用 📄 图标而非 📹，`[WEB-LINK]` 前缀。
- **webhook run_id 与 stage_c run_id 不一致：** TG notify webhook 作为独立 GitHub Action 触发时自带新的 run_id（如 `gh-25857736338-1`），与 stage_c 数据中的实际 run_id（如 `gh-25857678412-1`）不同。若直接使用 webhook run_id，归档文件 `pipe-{run_id}.json` 和 run-log `{run_id}.md` 会以 webhook run_id 命名，与 stage_c 数据不一致，导致后续查档困难。**修复：** 在 Step 9 顶部先提取 `stage_c.run_id` 作为脚本参数，确保跨阶段 run_id 一致.
- **源目录混合内容（mixed-content）：** `raw/github-links/`、`raw/youtube-links/` 等目录名暗示了期望的内容类型，但用户可能将 arXiv 论文、Web 链接、Reddit 讨论等非预期类型的 `.md` 文件放入其中。**修复：** 不要根据目录名过滤 URL 格式（如假设 `github-links/` 只含 `https://github.com/...`）。改为：Read 每个 `.md` 文件，从正文提取实际 URL（无论其格式），全部加入 `processed_urls`。然后根据 URL 类型列表决定 pipeline 标识前缀（如 `[GITHUB-RESEARCH+ARXIV]`），并在 `tg_summary` 中用相应图标（📦+📄）区分不同类型。
- **执行复杂 Python 脚本的陷阱（terminal/f-string 兼容性）：** 当尝试通过 `terminal` 命令直接执行包含多行代码或复杂字符串（如 f-string）的 Python 脚本时（例如使用 `python3 -c "..."` 或 `printf "..." | python3`），可能会因 shell 解释器对 Python 代码中引号和特殊字符的误判，导致 `SyntaxError` 或其他执行错误。
  **修复：** 避免直接在 shell 命令中内联复杂 Python 脚本。正确的做法是，先使用 `echo "..." > /tmp/script_name.py` 将 Python 脚本内容写入一个临时文件（例如 `/tmp/script_name.py`），然后再使用 `python3 /tmp/script_name.py` 命令执行该临时文件。这种方法能够有效规避 shell 解释器对 Python 代码的干扰，确保脚本的正确执行.