---
name: sop-wiki-build
description: "SOP Stage C: 三阶段增量知识图谱构建，基于 NotebookLM 分析结果构建 wiki，push 结果并发送 Telegram 通知。"
version: 2.6.0
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

6b. 读取 `raw/pipeline-context.json`（若存在），记录 stage_b 数据备用。

7. 读取 `index.md` 和 `log.md`（最近 10 条）了解现有内容，避免重复创建。
8. 确保目录存在：`mkdir -p wiki/sources wiki/entities wiki/concepts wiki/comparisons wiki/overview wiki/queries logs/webhook-runs`

---

## Phase 2: Action（调用 Python 脚本一次性生成所有页面）

**目标：用单次 LLM API 调用生成所有 wiki 页面，替代 Agent 的多次调用**

9. **⚠️ 环境准备：导出 API 密钥**
   脚本通过 `os.environ` 读取 API 密钥，密钥存储在 `~/.hermes/.env` 中但不会自动导出到 shell。执行脚本前必须手工导出：

   ```bash
   # 导出密钥环境变量（必须！否则脚本 401）
   source ~/.hermes/.env
   
   # DeepSeek 密钥可能已过期，若遇到 401 则改用 OpenRouter：
   # unset DEEPSEEK_API_KEY
   # export OPENROUTER_API_KEY
   ```

   > **坑**：脚本逻辑是 `DEEPSEEK_API_KEY` 优先（→ `api.deepseek.com`），回退 `OPENROUTER_API_KEY`（→ `openrouter.ai`）。DeepSeek 密钥过期时，必须 unset 它才能走 OpenRouter 路由。

10. 调用 sop_wiki_builder.py（固定路径）：
   ```bash
   python3 /home/zhouhuijuan1987/.hermes/scripts/sop_wiki_builder.py \
     --wiki-path {wiki_local_path} \
     --run-id {run_id} \
     --before-sha {before} \
     --sha {sha}
   ```

   该脚本会：
   - 读取所有分析报告和脑图
   - 一次 DeepSeek API 调用生成所有 wiki 页面（JSON 格式）
   - 写入所有文件（无额外 LLM 调用）
   - 更新 index.md 和 pipeline-context.json
   - 自动完成 git commit + push

   脚本输出最后一行是 JSON 状态：`{"status": "success", "pages": N, "duration_s": T}`

10. 检查脚本返回码：
    - 返回 0 = 成功，Phase 3 只需写 run-log（脚本已完成 commit/push）
    - 返回 非0 = 失败，Phase 3 需记录错误并报告

Phase 2 完成后跳过 Phase 3 的 git 操作（脚本已处理），只执行 Phase 3 的 Telegram 通知准备。

---

## Phase 3: Post-Execution（提交阶段）⚠️ 强制执行

**目标：记录执行日志（git commit/push 已由脚本处理）**

> **此阶段独立于 Phase 2，即使 Phase 2 部分失败，也必须执行 Phase 3。**

17. 记录结束时间（仅日志用途，脚本已记录精确时间）。
18. **git commit/push：脚本已处理，跳过。** 若脚本返回非0，手动检查并处理。
19. 验证脚本写入的 run-log 存在：`ls {wiki_local_path}/logs/webhook-runs/{run_id}.md`

## 注意
- Stage C **不发送 Telegram**，通知由 Stage D（sop-tg-notify）负责。
- push 全部失败 → 记录 `status: push_failed`。

---

## 已知坑点（Pitfalls）

### 1. API 密钥来源
- API 密钥存储在 `~/.hermes/.env`，不是 shell env vars。
- `sop_wiki_builder.py` 使用 `os.environ.get()` 读取，**不自动加载 `.env`**。
- 每次执行前必须：`source ~/.hermes/.env`
- **DeepSeek 密钥已过期**（2026-05-09 确认），返回 401。改用 OpenRouter：
  ```bash
  source ~/.hermes/.env
  unset DEEPSEEK_API_KEY
  export OPENROUTER_API_KEY
  ```
  脚本会回退到 `https://openrouter.ai/api/v1` + `deepseek/deepseek-v4-flash` 模型名。

### 2. LLM 生成的双 `.md.md` 扩展名
- LLM 有时生成的文件名已包含 `.md`（如 `soul.md`），脚本再加 `.md` 导致 `soul.md.md`。
- `sop_wiki_builder.py` 已修复（line 207: `rstrip(".md") + ".md"`），但应自查：
  ```bash
  find wiki/ -name '*.md.md'
  ```
  发现后手动 `mv` 修复并重新 push。

### 3. 语言一致性
- 脚本生成的 content 全部为中文，frontmatter 字段名用英文。
- 文件路径中的概念名可能中英文混杂 — 统一用小写 slug 或中文语义名。具体规则见 TheSchema.md §7。
