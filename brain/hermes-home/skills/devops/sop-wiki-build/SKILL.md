---
name: sop-wiki-build
description: "SOP Stage C: 基于 NotebookLM 分析结果进行 llm-wiki 增量知识图谱构建，push 到仓库并发送 Telegram 通知。"
version: 1.0.0
---

# SOP Stage C: Wiki Incremental Build

## 触发条件
- webhook 收到 `stage=wiki-build`

## 执行流程

### 准备阶段
1. 进入仓库：`cd {wiki_local_path}`
2. 读取 `TheSchema.md` — 这是知识图谱构建的核心规范，**最高优先级**。
3. 保护性同步：
   ```bash
   git stash push -u -m "sop-stage-c-{run_id}"
   git fetch origin && git checkout main && git pull --ff-only origin main
   git stash pop
   ```
4. 计算 raw 变更：
   ```bash
   git diff --name-only {before}..{sha} -- 'raw/*.md' 'raw/**/*.md'
   ```
5. 过滤出 `raw/notebooklm-analysis/` 和 `raw/notebooklm-mindmaps/` 下的变更。
6. 若无变更：记录 `skipped:no_raw_changes`，停止，**禁止发送 Telegram**。

### 构建阶段（遵循 TheSchema.md 规范）
7. 阅读 `index.md` 和 `log.md` 了解现有内容，避免重复。
8. 对每个新的分析报告文件：
   a. **创建 Source 页** (`wiki/sources/{video-id}-{slug}.md`)：
      - frontmatter 完整（type/tags/summary/sources/layer/confidence）
      - 视频基本信息（标题、URL、发布者）
      - 执行摘要（3-5句）
      - 核心要点（5-10条）
      - 关键引言+背景分析
      - 关联实体和概念的 wikilinks
   b. **创建/更新 Entity 页** (`wiki/entities/`)：
      - 覆盖视频中出现的人物、产品、组织、AI模型
      - 每页至少 2 个出链 wikilinks
      - layer=L1（直接事实）或 L2（跨视频推断）
   c. **创建/更新 Concept 页** (`wiki/concepts/`)：
      - 覆盖核心技术方法、框架、趋势
      - 每页至少 2 个出链 wikilinks
      - 包含在本库中的具体例子
   d. **按需创建 Comparison 页**（当多个视频涉及相同对比维度）

9. 更新 `index.md`（按 type 分类，字母序，每条带 summary 摘要）：
   - Last updated 日期
   - Total pages 计数
10. 追加 `log.md`（run_id、日期、新增/更新文件列表）

### 质量检查
11. 验证每个新页面：
    - frontmatter 完整（type/tags/summary/sources/layer）
    - 至少 2 个 wikilinks 出链
    - 内容密度：source 页 ≥ 300 字，entity/concept 页 ≥ 200 字
    - sources 指向存在的 raw/ 文件

### 提交阶段
12. 写执行日志到 `logs/webhook-runs/{run_id}.md`
13. `git add wiki/ index.md log.md logs/`
14. `git commit -m "chore: update llm wiki graph from notebooklm analysis [run:{run_id}]"`
15. `git push origin main`

### Telegram 通知（仅在成功 push 后发送）
16. 使用 Bot API 直接发送（不走 Hermes deliver）：
    ```
    TOKEN=$(printenv {tg_token_env})
    curl -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
      -d "chat_id={tg_chat_id}" \
      -d "disable_web_page_preview=true" \
      -d "text=<摘要内容>"
    ```
17. 摘要内容必须包含（用中文）：
    - [YOUTUBE-WIKI-RUN] 标记
    - run_id
    - 新增 source 页数量和名称
    - 新增 entity 页数量和名称（≤5个）
    - 新增 concept 页数量和名称（≤5个）
    - commit hash
    - 日志路径

## 错误处理
- 质量检查失败：记录具体问题，修复后再 commit。
- git push 失败：重试一次，仍失败则记录并返回失败，**禁止发送 Telegram**。
- 若 push 成功但 TG 发送失败：在 run-log 记录，不影响整体成功状态。

## 输出规范
执行完成后回复中文总结：
- 新增/更新的 wiki 页面列表
- index.md 变更摘要
- git commit hash
- Telegram 发送状态
