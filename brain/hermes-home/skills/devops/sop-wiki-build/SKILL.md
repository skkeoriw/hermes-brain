---
name: sop-wiki-build
description: "SOP Stage C: 基于 NotebookLM 分析结果进行 llm-wiki 增量知识图谱构建，push 结果并发送 Telegram 通知。"
version: 1.0.0
---

# SOP Stage C: Wiki Incremental Build

## 触发条件
webhook 收到 `stage=wiki-build`

## 执行流程

### 准备
1. `cd {wiki_local_path}`
2. **首先读取 `TheSchema.md`**（最高优先级，知识图谱构建的核心规范）。
3. 保护性同步：
   ```bash
   git stash push -u -m "sop-stage-c-{run_id}" 2>/dev/null || true
   git fetch origin && git checkout main && git pull --ff-only origin main
   git stash pop 2>/dev/null || true
   ```
4. 计算 raw 变更：
   ```bash
   git diff --name-only {before}..{sha} -- 'raw/*.md' 'raw/**/*.md'
   ```
5. 过滤 `raw/notebooklm-analysis/` 和 `raw/notebooklm-mindmaps/` 下的变更。
6. 若无变更：写日志 `skipped:no_raw_changes`，**禁止发送 Telegram**，停止。

### 构建（严格遵循 TheSchema.md）
7. 读取 `index.md` 和 `log.md` 了解现有内容，避免重复创建。
8. 对每个新分析报告：
   a. **Source 页** (`wiki/sources/{video-id}-{slug}.md`)：
      - 视频信息（标题、URL、发布者）
      - 执行摘要（3-5句）
      - 核心要点（5-10条）
      - 关联实体/概念的 `[[wikilinks]]`
      - frontmatter: type/tags/summary/sources/layer=L1/confidence=high
   b. **Entity 页** (`wiki/entities/{slug}.md`)：
      - 人物、产品、组织、AI模型
      - 每页 ≥ 2 个出链 wikilinks
      - layer=L1 或 L2（跨视频推断时标注 reasoning）
   c. **Concept 页** (`wiki/concepts/{slug}.md`)：
      - 技术方法、框架、趋势
      - 每页 ≥ 2 个出链 wikilinks
      - 包含本库中具体例子

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

### Telegram 通知（push 成功后发送）
14. ```bash
    TOKEN=$(printenv {tg_token_env})
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
      -d "chat_id={tg_chat_id}" \
      -d "disable_web_page_preview=true" \
      --data-urlencode "text=[YOUTUBE-WIKI-RUN]
run_id={run_id}
新增 source: <n>个 - <名称列表>
新增 entity: <n>个 - <名称列表(≤5)>
新增 concept: <n>个 - <名称列表(≤5)>
commit: <hash>
log: logs/webhook-runs/{run_id}.md"
    ```

## 注意
- push 失败时重试一次，仍失败则记录错误，**禁止发送 Telegram**。
- TG 发送失败不影响整体成功状态，但须在 run-log 记录。
