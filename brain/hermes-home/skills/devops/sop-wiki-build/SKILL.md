---
name: sop-wiki-build
description: "SOP Stage C: 三阶段增量知识图谱构建，基于 NotebookLM 分析结果构建 wiki，push 结果并发送 Telegram 通知。"
version: 2.0.0
---

# SOP Stage C: Wiki Incremental Build

## 触发条件
webhook 收到 `stage=wiki-build`

---

## Phase 1: Pre-Execution（准备阶段）

**目标：读取配置，同步仓库，确认有分析文件需要处理**

1. 记录开始时间：`START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. `cd {wiki_local_path}`
3. **首先读取 `TheSchema.md`**（最高优先级，知识图谱构建的唯一规范）。
4. 保护性同步：
   ```bash
   git stash push -u -m "sop-c-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   if ! git stash pop 2>/dev/null; then
       git reset --hard origin/main && git stash drop 2>/dev/null || true
   fi
   ```
5. **扫描分析文件**（不依赖 git diff，直接扫目录）：
   ```bash
   ls {wiki_local_path}/raw/notebooklm-analysis/*.md 2>/dev/null | grep -v 'trigger'
   ```
6. **若无分析文件**：写跳过日志，git add + commit + push 日志，停止执行（禁止发 Telegram）。
7. 读取 `index.md` 和 `log.md`（最近 10 条）了解现有内容，避免重复创建。
8. 确保目录存在：`mkdir -p wiki/sources wiki/entities wiki/concepts wiki/comparisons wiki/overview wiki/queries logs/webhook-runs`

---

## Phase 2: Action（知识图谱构建）

**目标：将分析文件转化为结构化 wiki 页面，严格遵循 TheSchema.md**

### 文件写入约束（必须遵守）
- **必须用 write_file 工具写入所有 wiki 文件**，禁止 `echo`、`heredoc`、`cat <<EOF`。
- shell 方式导致 `\n` 变成字面字符串，破坏 frontmatter 格式。

### 命名陷阱（常见错误）

1. **Entity 文件名必须匹配 wikilink**：如果你在 source 页写 `[[Hermes Agent]]`，则 entity 文件必须命名为 `Hermes Agent.md`。不要用 slug 格式（`hermes-agent.md`），否则会死链。创建所有页面后立即运行链接健康检查（Step 14）即可发现此问题。

2. **检查 TheSchema.md 确认确切目录名**：TheSchema.md 第二节的目录结构中，`wiki/overview/` 是单数（不是 `wiki/overviews/`）、`wiki/comparisons/` 是复数。创建目录前先确认 schema 中的确切路径。

3. **重复分析文件处理**：若 `raw/notebooklm-analysis/` 中存在两个或多个内容完全相同的文件（如一份报告因命名差异出现了 dash 和 colon 两个版本），只创建一个 source 页，并在 `sources:` 字段中列出所有原始文件路径。

### 对每个分析报告执行：

### 对每个分析报告执行：
9. 创建 **Source 页**（`wiki/sources/{中文标题}.md`）：
   - frontmatter 必填：`title/type/tags/summary/sources/created/updated/layer/confidence`
   - 视频元数据（标题、URL）、执行摘要（3-5句）、核心要点（5-10条）
   - 关联实体 `[[实体名]]`，关联概念 `[[概念名]]`
   - `sources` 字段指向对应的 `raw/notebooklm-analysis/` 文件
   - 每个视频**唯一一个** source 页，若已存在则更新

10. 创建/更新 **Entity 页**（`wiki/entities/{实体名}.md`）：
    - 先查 index.md 确认是否已存在，已存在则更新不新建
    - 基本定位、核心特征、关系网络（≥2 个 `[[wikilink]]`）、出现的视频来源

11. 创建/更新 **Concept 页**（`wiki/concepts/{概念名}.md`）：
    - 先查 index.md 确认是否已存在
    - 定义、本库具体例子、关联概念（≥2 个）、关联实体（≥1 个）

12. **检查 Comparison 触发**：同一视频或不同视频中有直接对比的两个实体 → 创建 `wiki/comparisons/{A}-vs-{B}.md`（对比表格+分析+结论）

13. **检查 Overview 触发**：同主题 source 页 ≥2 个 → 创建或更新 `wiki/overview/{主题}.md`（跨视频综合，L2 推断）

### 链接健康检查：
14. 扫描所有新建/修改页面的 `[[wikilink]]`，确认目标文件存在。死链处理：立即创建缺失页面，或删除该链接。

### 更新索引：
15. 更新 `index.md`（按 type 分类，字母序，每条带 summary，更新 Last updated 和 Total pages）
16. 追加 `log.md`（run_id、日期、新增文件列表）

---

## Phase 3: Post-Execution（提交阶段）⚠️ 强制执行

**目标：无论 Phase 2 是否完整，必须 commit + push + 通知**

> **此阶段独立于 Phase 2，即使 Phase 2 部分失败，也必须执行 Phase 3。**

17. 记录结束时间：`END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
18. 用 write_file 工具写执行日志到 `{wiki_local_path}/logs/webhook-runs/{run_id}.md`，必须包含：
    - `start_time` / `end_time`
    - `new_sources` / `new_entities` / `new_concepts` / `new_comparisons` / `new_overviews`
    - `status`：success / partial / skipped
19. **检查并提交所有变更**：
    ```bash
    cd {wiki_local_path}
    git add wiki/ index.md log.md logs/
    if [ -n "$(git status --porcelain)" ]; then
      git commit -m "chore: update llm wiki graph [run:{run_id}]"
    fi
    ```
20. **push，最多重试 3 次**：
    ```bash
    for i in 1 2 3; do
      git push origin main && break
      git pull --ff-only origin main
    done
    ```
21. 验证 push 成功：`git log --oneline -1` 确认本地 HEAD 与 origin/main 一致。
22. **发送 Telegram（仅在 push 成功且有实际 wiki 更新时）**：
    ```bash
    TOKEN=$(printenv {tg_token_env})
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
      -d "chat_id={tg_chat_id}" \
      -d "disable_web_page_preview=true" \
      --data-urlencode "text=[YOUTUBE-WIKI-RUN]
run_id: {run_id}
新增 source: <n>个
新增 entity: <n>个
新增 concept: <n>个
新增 comparison: <n>个
commit: <hash>
耗时: <duration>s
log: logs/webhook-runs/{run_id}.md"
    ```

## 注意
- push 全部失败 → 记录 `status: push_failed`，**禁止发 Telegram**。
- TG 发送失败 → 在 run-log 记录，不影响整体成功状态。
