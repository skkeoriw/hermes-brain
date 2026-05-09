# Webhook Run Log Format (for logs/webhook-runs/{run_id}.md)

## 基本信息
- **Run ID**: {run_id}
- **触发时间**: {timestamp}
- **触发事件**: sop-wiki-build (webhook)
- **当前 SHA**: {current_sha}
- **之前 SHA**: {before_sha}
- **仓库路径**: {wiki_local_path}
- **GitHub 仓库**: {github_repo}

## 执行流程

### 1. 准备阶段
- ✅ 切换到 wiki 目录: `{wiki_local_path}`
- ✅ 读取 TheSchema.md (知识图谱构建核心规范)
- ✅ 保护性同步:
  - `git stash push -u -m "sop-stage-c-{run_id}"`
  - `git fetch origin && git checkout main && git pull --ff-only origin main`
  - `git stash pop`
- ✅ 计算 raw 变更:
  - `git diff --name-only {before_sha}..{current_sha} -- 'raw/*.md' 'raw/**/*.md'`
  - 结果: {raw_changes_list}
- ✅ 过滤 `raw/notebooklm-analysis/` 和 `raw/notebooklm-mindmaps/` 下的变更（本阶段仅处理 NotebookLM 结果）
- ✅ {has_changes_condition}

### 2. 构建阶段
- ✅ 读取 index.md 和 log.md 了解现有内容
- ✅ 处理新分析报告: {analysis_file_list}

#### 创建的页面:
{created_pages_list}

### 3. 质量检查
- ✅ 每个新页面 frontmatter 完整（type/tags/summary/sources/layer 必填）
- ✅ 每个页面 ≥ 2 个 wikilinks 出链
- ✅ source 页 ≥ 300 字，entity/concept 页 ≥ 200 字
- ✅ sources 指向存在的 raw/ 文件
- ✅ 所有内容使用中文，frontmatter 字段名用英文

### 4. 更新索引
- ✅ 更新 `index.md`（按 type 分类，字母序，带 summary）
- ✅ 更新 Last updated: {today} | Total pages: {total_pages}
- ✅ 追加 `log.md`（run_id、日期、新增文件列表）

### 5. 提交
- ✅ 写执行日志到 `logs/webhook-runs/{run_id}.md`
- ✅ `git add wiki/ index.md log.md logs/`
- ✅ `git commit -m "chore: update llm wiki graph from notebooklm analysis [run:{run_id}]"`
- ✅ `git push origin main`

## 结果摘mary
- 新增 source: {source_count}个
- 新增 entity: {entity_count}个
- 新增 concept: {concept_count}个
- 总计新增页面: {total_pages}个