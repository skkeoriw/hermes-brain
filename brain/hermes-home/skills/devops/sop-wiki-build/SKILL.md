---
name: sop-wiki-build
description: "SOP Stage C: 基于 NotebookLM 分析结果进行 llm-wiki 增量知识图谱构建，push 结果并发送 Telegram 通知。"
version: 1.0.0
---

# SOP Stage C: Wiki Incremental Build

See `references/run-log-format.md` for the standard webhook run log format.

## 触发条件
webhook 收到 `stage=wiki-build`

## 执行流程

### 准备
1. **记录开始时间**：`START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. `cd {wiki_local_path}`
3. **首先读取 `TheSchema.md`**（最高优先级，知识图谱构建的核心规范）。
4. 确保 wiki 目录结构存在：`mkdir -p wiki/sources wiki/entities wiki/concepts`
5. 保护性同步：
   ```bash
   git stash push -u -m "sop-stage-c-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   git stash pop 2>/dev/null || true
   ```
6. 检测需要处理的分析文件 — **使用目录扫描而非 git diff**（git diff 对中文文件名的引号处理会导致匹配失败）：
   ```bash
   # 扫描 raw/notebooklm-analysis/ 下所有 .md 文件
   ls raw/notebooklm-analysis/*.md 2>/dev/null | grep -v 'trigger'
   ```
   找出其中在 `wiki/sources/` 目录下**还没有对应 source 页**的文件，这些就是需要处理的新分析文件。
   
   判断逻辑：如果 `raw/notebooklm-analysis/*.md`（排除 trigger 文件）的数量 > 0，则继续执行；否则跳过。

7. 若 `raw/notebooklm-analysis/` 下没有任何 .md 分析文件：
   - 写 skip 日志到 `logs/webhook-runs/{run_id}.md`（标题标明 skipped: no_raw_changes）
   - **使用 `write_file` 工具写入**，禁止使用终端 heredoc
   - 提交并 push skip 日志：
     ```bash
     git add logs/webhook-runs/{run_id}.md
     git commit -m "chore: skip wiki build - no new notebooklm content [run:{run_id}]"
     git push origin main
     ```
   - **禁止发送 Telegram**
   - 停止执行（wiki 目录为空且无分析文件则停止）

### 文件写入约束（必须遵守）
- **必须用 write_file 工具写入文件**，禁止用 `echo`、`cat <<EOF`、`heredoc` 等 shell 方式。
- shell 方式会导致 `\n` 变成字面字符串而不是真实换行符，造成文件格式损坏。

### 构建（严格遵循 TheSchema.md）

9. 读取 `index.md` 和 `log.md` 了解现有内容，避免重复创建。
10. 确保 wiki 目录结构存在：`mkdir -p wiki/sources wiki/entities wiki/concepts wiki/comparisons wiki/overview wiki/queries`
11. 对每个新分析报告：
    a. **Source 页** (`wiki/sources/{中文标题}.md`)：
      - 必须创建（每个分析报告对应一个 source 页）
      - 使用 NotebookLM 分析文件的中文标题作为文件名（不含 `{video-id}-` 前缀，除非已有约定）
      - 视频信息（标题、URL、发布者）
      - 执行摘要（3-5句）
      - 核心要点（5-10条）
      - 关联实体/概念的 `[[wikilinks]]`
      - frontmatter: type/tags/summary/sources/layer=L1/confidence=high
    b. **Entity 页** (`wiki/entities/{实体名-slug}.md`)：
      - 仅当实体页面尚不存在时创建
      - 人物、产品、组织、AI模型
      - 每页 ≥ 2 个出链 wikilinks
      - layer=L1 或 L2（跨视频推断时标注 reasoning）
      - 英文实体名小写连字符 slug，中文实体名直接中文文件名
    c. **Concept 页** (`wiki/concepts/{概念名}.md`)：
      - 仅当概念页面尚不存在时创建
      - 技术方法、框架、趋势
      - 每页 ≥ 2 个出链 wikilinks
      - 包含本库中具体例子
      - 中文概念名直接使用中文文件名，不翻译

### 质量检查（必须通过）
9. 每个新页面：
   - frontmatter 完整（type/tags/summary/sources/layer 必填）
   - ≥ 2 个 wikilinks 出链
   - source 页 ≥ 300 字，entity/concept 页 ≥ 200 字
   - sources 指向存在的 raw/ 文件

### 更新索引
10. 更新 `index.md`（按 type 分类，字母序，带 summary，更新 Last updated 和 Total pages）
11. 追加 `log.md`（run_id、日期、新增文件列表）

### 提交
12. 写执行日志到 `logs/webhook-runs/{run_id}.md`
13. ```bash
    git add wiki/ index.md log.md logs/
    git commit -m "chore: update llm wiki graph from notebooklm analysis [run:{run_id}]"
    git push origin main
    ```
14. **记录结束时间**：`END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
15. **计算耗时**：`DURATION_SECONDS=$(($(date -u -d "$END_TIME" +%s) - $(date -u -d "$START_TIME" +%s)))`

### Telegram 通知（push 成功后发送）
16. ```bash
    TOKEN=$(printenv {tg_token_env})
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \\
      -d "chat_id={tg_chat_id}" \\
      -d "disable_web_page_preview=true" \\
      --data-urlencode "text=[YOUTUBE-WIKI-RUN]
run_id={run_id}
新增 source: <n>个 - <名称列表>
新增 entity: <n>个 - <名称列表(≤5)>
新增 concept: <n>个 - <名称列表(≤5)>
commit: <hash>
duration_stage_c: ${DURATION_SECONDS}s
log: logs/webhook-runs/{run_id}.md"
    ```

    run-log 中必须包含：
    - `start_time`: START_TIME 的值
    - `end_time`: END_TIME 的值（在 push 成功后记录）
    - `duration_seconds`: DURATION_SECONDS

## 注意
- push 失败时重试一次，仍失败则记录错误，**禁止发送 Telegram**。
- TG 发送失败不影响整体成功状态，但须在 run-log 记录。

## 常见问题与经验教训
- **文件写入换行问题**：使用 `write_file` 工具时，必须确保内容中使用实际的换行符（`\n`），而不是转义的字面字符串 `\\n`。如果发现生成的文件出现 YAML 解析错误（如 "expected a single document in the stream"），检查 frontmatter 是否包含字面的 `\\n` 字符，需要使用 `write_file` 重写文件并确保换行符正确。
- **前置文件检查**：在处理现有 wiki 文件时，如果发现 frontmatter 解析错误，可能是由于之前的写入方式导致的换行问题。此时应先读取文件内容，将所有 `\\n` 替换为实际换行符，然后重新写入。
- **日志文件冲突**：`log.md` 等频繁追加的文件可能出现合并冲突。在保护性同步阶段的 `git stash pop` 后，应检查并解决任何冲突，然后再继续执行。
- **索引更新**：更新 `index.md` 时，应保持现有格式和排序，避免重复条目。可以先读取现有内容，然后在适当位置插入新条目，最后更新页码统计。
