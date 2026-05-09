---
name: sop-wiki-build
description: "SOP Stage C: 三阶段增量知识图谱构建，基于 NotebookLM 分析结果构建 wiki，push 结果并发送 Telegram 通知。"
version: 2.5.0
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

## Phase 2: Action（方案A - 一次规划，批量执行）

**⚠️ 重要：先规划后执行，不要边想边写**

### 文件写入约束（必须遵守）
- **必须用 write_file 工具写入所有 wiki 文件**，禁止 `echo`、`heredoc`、`cat <<EOF`。
- shell 方式导致 `\n` 变成字面字符串，破坏 frontmatter 格式。

### 命名陷阱（常见错误）

1. **Entity 命名规范：遵循 TheSchema.md 小写 slug**：TheSchema.md §2 要求 entity 文件使用 `{实体名}.md（小写 slug）` 命名（如 `hermes-agent.md`），而非 readable 名称（如 `Hermes Agent.md`）。**这是最高优先级规范**，skill 的 slug-generation.md 参考文件已更新对齐。在所有页面中使用 `[[slug]]` 引用时，必须与 entity 文件名完全一致。

2. **特殊字符导致文件名损坏**：避免在文件名中使用以下字符：
   - `+`（加号）→ 文件系统显示为 `-+-`
   - `：`（全角冒号）、`/`、`\`、`?`、`*`、`<`、`>`
   - 推荐使用中文汉字、英文连字符 `-`、空格（空格在 Linux 文件系统中受支持但请注意 wikilink 一致性）
   
3. **Linux 文件系统大小写敏感**：`Token-自由.md` 与 `token-自由.md` 是不同的文件。wikilink 中的名称必须与文件名的大小写完全一致。创建所有页面后运行链接健康检查（Step A3）可发现此问题。

4. **检查 TheSchema.md 确认确切目录名**：TheSchema.md 第二节的目录结构中，`wiki/overview/` 是单数（不是 `wiki/overviews/`）、`wiki/comparisons/` 是复数。创建目录前先确认 schema 中的确切路径。

5. **重复分析文件处理**：若 `raw/notebooklm-analysis/` 中存在两个或多个内容完全相同的文件（如一份报告因命名差异出现了 dash 和 colon 两个版本），只创建一个 source 页，并在 `sources:` 字段中列出所有原始文件路径。

6. **⚠️ mindmap_file frontmatter 不可靠 — 必须通过 filesystem 验证**：分析文件的 `mindmap_file` 字段（如 `krEDel3aGGw_..._mindmap.json`）在实战中经常与实际磁盘文件名不匹配。实际文件名通常是中文标题格式（如 `GPT-5-5-Instant-模型发布与性能分析简报.canvas`），与同名的分析 `.md` 文件扩展名不同。**绝对不要直接使用 frontmatter 的 `mindmap_file` 值**。
   - **错误做法**：`ls raw/notebooklm-mindmaps/{mindmap_file}` → 文件不存在，构建卡死
   - **正确做法**：先 `ls raw/notebooklm-mindmaps/` 获取实际文件列表，通过分析文件的中文标题前缀匹配对应的 `.canvas` 文件
   - 验证命令：`ls raw/notebooklm-mindmaps/ | grep "$(basename '{analysis_md_file}' .md)"` 或直接肉眼匹配文件名前缀

7. **（已废弃 — 见陷阱 #9）** 此陷阱已被 #9 取代。不再使用 `[[wikilink]]` 引用脑图文件，改用纯文本。

8. **⚠️ `execute_code` 沙箱内 read_file 返回格式不可靠 — 质量检查需用终端工具**：在 `execute_code` Python 沙箱中调用 `from hermes_tools import read_file` 时，返回的 dict key 可能与预期不同（如 `KeyError: 'content'`）。**禁止依赖沙箱中的 read_file 做验证**。正确做法：使用 `terminal` 工具运行 shell 命令（`wc -m`、`grep`、`find`）进行质量核查，或运行 `scripts/verify-quality.sh` 脚本。

9. **⚠️ 非 wiki 文件的 wikilink 会导致死链 — 使用纯文本替代**：source 页正文中如果使用 `[[{文件名}|查看脑图]]` 引用 `raw/notebooklm-mindmaps/` 下的脑图文件，无论文件是 `.json` 还是 `.canvas`，都会触发链接健康检查的死链告警（因为目标不在 `wiki/` 目录下，且不是 `.md` 文件）。`verify-quality.sh` 的豁免逻辑仅覆盖特定硬编码文件名模式，不通用。

   **正确做法：永远使用纯文本或代码块引用非 wiki 文件**：
   ```markdown
   ✅ 脑图文件：`实际磁盘文件名.json`
   ✅ 脑图文件位于 `raw/notebooklm-mindmaps/实际磁盘文件名.json`
   ❌ [[实际磁盘文件名.json|查看脑图]]
   ```
   **原理**：`[[wikilink]]` 仅用于 wiki 页面间的交叉引用。指向 `raw/` 目录下的原始文件（分析报告 `.md`、脑图 `.json`/`.canvas`）不应使用 wikilink。

10. **⚠️ Source 页 wikilink 名称必须与磁盘文件名完全一致**：entity/concept/comparison/overview 页中引用 source 页时，使用 `[[source页磁盘文件名（去.md）]]`，**必须**与 `wiki/sources/` 中的实际 `.md` 文件名完全一致（包括连字符位置、大小写、特殊字符处理）。**不能**使用分析报告的可读标题。
    - **文件名生成规则**：source 页文件名派生自分析报告的中文文件名。常见的自动替换：`.` → `-`、`：` → `-`、空格保留、其余特殊字符 → `-`
    - **典型错误**：分析文件标题为 `GPT-5.5-Instant-深度解析简报`，可读版本含 `GPT-5.5` 和 `：` → 实际文件名是 `GPT-5-5-Instant-深度解析简报-性能升级-功能演进与实测评估.md`。entity 页中引用为 `[[GPT-5.5 Instant 深度解析简报：性能升级、功能演进与实测评估]]` → **死链**。正确引用为 `[[GPT-5-5-Instant-深度解析简报-性能升级-功能演进与实测评估]]`。
    - **最佳实践**：在 Step A1 规划时，直接记下 source 文件的实际磁盘名（`ls wiki/sources/`），并以此生成所有 `[[wikilink]]`。不要在规划时使用可读标题，等 A3 质量检查才发现不匹配。

11. **⚠️ 单视频实体页的 wikilink 计数陷阱 — 规划时就要预埋关系链接**：quality 检查要求每页 ≥2 个出链。如果某个 entity 只出现在一个视频中，`出现的视频来源` 小节仅贡献 1 个 wikilink。这意味着必须额外添加至少 1 个关系链接才能通过检查。**在 Step A1 规划时，不要等到写 entity 正文再想关系——先列出所有实体之间的关联图，再写入每个 entity 时自然带上关系小节。** 常见可用的关系对：`开发者 → [[产品]]`、`组织 → [[竞争对手]]`、`模型 → [[框架]]`。`new/openai + new/gpt-5-5-instant` 这种同 source 实体对是最简单的解法——互相引用即可同时满足两个页面的计数要求。

12. **⚠️ pipeline-context.json 可能在 git stash pop 冲突后从工作树消失 — 从 git 历史恢复**：当保护性同步（Step 4）的 stash pop 发生冲突时，执行 `git reset --hard origin/main` 会将 tracked 文件重置到 origin/main 的状态。如果 `raw/pipeline-context.json` 在上一个已推入的 commit 中存在（如 Stage B 写过），但被 stash pop 冲突删除了工作副本，**不要惊慌**——直接从 git 历史恢复：
    ```bash
    git show HEAD:raw/pipeline-context.json > raw/pipeline-context.json 2>/dev/null || \
      git show HEAD~1:raw/pipeline-context.json > raw/pipeline-context.json
    ```
    - 这条命令尝试从 HEAD 恢复，若 HEAD 没有则回退到前一个 commit。
    - 恢复后读取 JSON，追加 stage_c 数据，然后写入。
    - 在 git add 命令中包含 `raw/pipeline-context.json`（确保被跟踪）。

13. **⚠️ 工作树中可能存在未提交的 wiki/ 文件（前序未完成的 Stage C 产物）— 检视而非覆盖**：如果 wiki/ 目录在 `git status` 中显示为 `untracked` 或 `modified` 文件（来源于前一个未提交的 Stage C 运行），**不要直接删除或覆盖**。这 4 种情形需要不同处理：
    - **文件质量好**（有完整 frontmatter 和内容）→ 保留，作为"预先存在"的内容纳入本次构建
    - **文件缺少分析报告**（如同一视频有 2 份报告但只引用 1 份）→ 更新 `sources:` 字段追加缺失报告，不需要重写整个文件
    - **文件质量差**（缺 frontmatter 字段、内容空洞）→ 用 write_file 完全覆盖
    - **source 页命名冲突**：如果有两个视频的报告被分别命名为不同的 source 文件名，但实际属于同一视频 → 以第一个 source 页为主，更新其 sources 字段
    - 使用 `git ls-files -- wiki/` 判断哪些 wiki 文件已被 git 跟踪；用 `ls wiki/sources/` 检视实际存在的所有文件

14. **⚠️ verify-quality.sh 的 frontmatter 检查可能出现假阳性 — 重跑确认**：该脚本使用 `sed -n '1,/^---$/p'` 提取 frontmatter，在文件写入后立即运行时可能因文件系统延迟出现误报（如误报缺失 `type:` 或 `tags:` 字段）。**若 Check 1 报错但肉眼检查 frontmatter 完全正常**，直接重跑一次确认。若重跑通过则为假阳性；若仍失败才是真问题。

---

**Step A1 — 生成完整构建计划（1次LLM调用）**

读取所有输入后，在内存中生成一个完整的构建计划，包含所有需要创建的页面及其完整内容。规划时需遵循 TheSchema.md 的全部规范：

对每个分析报告，读取报告文件的元数据 frontmatter（`---` 块）：
   ```
   video_id, video_url, source_id, mindmap_file, processed_at
   ```
   - `video_url`：直接用于 source 页，比从内容推断更可靠
   - `mindmap_file`：**仅作参考，不可直接使用**（见陷阱 #6）。必须通过 filesystem 验证实际文件名：
     ```bash
     ls raw/notebooklm-mindmaps/ | grep "$(basename '{分析文件路径}' .md)"
     ```
     若 `grep` 无匹配，直接 `ls raw/notebooklm-mindmaps/` 肉眼匹配文件名前缀
   - 若无 frontmatter，退化到从报告正文推断

规划页面类型：
- Source 页（必须，每视频唯一）：含 video_url、mindmap 字段、执行摘要、核心要点、关联实体/概念
  - frontmatter 必填：`title/type/tags/summary/sources/created/updated/layer/confidence`
  - **新增 frontmatter 字段**（建立三方关联）：
    ```yaml
    video_url: {从报告 frontmatter 读取}
    mindmap: raw/notebooklm-mindmaps/{实际磁盘文件名}
    ```
  - `sources` 字段同时列出报告路径和脑图路径
  - 页面正文**必须包含**视频 URL 和脑图引用（`{实际磁盘文件名}` 来自 `ls` 输出，**不是** frontmatter `mindmap_file` 值）
  - 执行摘要（3-5句）、核心要点（5-10条）
  - 每个视频**唯一一个** source 页，若已存在则更新
- Entity 页（查 index.md 避免重复）：定位、特征、关系网络（≥2 个 wikilink）、来源；文件名小写 slug
- Concept 页（有本库具体例子，非泛泛）：定义、例子、对比、关联（≥2 个概念，≥1 个实体）

跨视频检查：
- Comparison 触发：有直接对比的两实体 → 创建 comparison 页（对比表格+分析+结论）
- Overview 触发：同主题 source ≥ 2 个 → 创建 overview 页（跨视频综合，L2 推断）

---

**Step A2 — 批量执行写入（机械执行，无需重新推理）**

按照 Step A1 的计划，依次调用 write_file 写入每个文件。每次 write_file 不需要重新思考内容，直接使用 Step A1 中规划好的内容。

---

**Step A3 — 链接健康检查**

扫描所有新建页面的 `[[wikilink]]`，确认目标文件存在，修复死链（立即创建缺失页面或删除该链接）。

质量核查（创建所有页面后执行），**推荐运行 `scripts/verify-quality.sh`**：
    ```bash
    bash /home/zhouhuijuan1987/.hermes/skills/devops/sop-wiki-build/scripts/verify-quality.sh {wiki_local_path}
    ```
    检查项：frontmatter 6 个必填字段、每页 ≥2 个有效出链、source 页 ≥400 字、entity/concept ≥200 字、sources 字段文件真实存在、无死链。

若为**首次构建**（index.md 显示 Total pages: 0 或仅模板内容），跳过"检查现有页面避免重复"的逻辑，直接为所有分析文件创建新页面。

---

**Step A4 — 更新索引**

更新 `index.md`（按 type 分类，字母序，每条带 summary，更新 Last updated 和 Total pages）。

追加 `log.md`（run_id、日期、新增文件列表）。

---

## Phase 3: Post-Execution（提交阶段）⚠️ 强制执行

**目标：无论 Phase 2 是否完整，必须 commit + push**

> **此阶段独立于 Phase 2，即使 Phase 2 部分失败，也必须执行 Phase 3。**

17. 记录结束时间：`END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
18. 用 write_file 工具写执行日志到 `{wiki_local_path}/logs/webhook-runs/{run_id}.md`，必须包含：
    - `start_time` / `end_time`
    - `new_sources` / `new_entities` / `new_concepts` / `new_comparisons` / `new_overviews`
    - `status`：success / partial / skipped

19b. 追加 stage_c 数据到 `raw/pipeline-context.json`：
    读取现有 pipeline-context.json，合并 stage_c 节点，再用 write_file 写回：
    ```json
    {
      "stage_c": {
        "run_id": "{run_id}",
        "start_time": "{START_TIME}",
        "end_time": "{END_TIME}",
        "duration_s": {DURATION},
        "api_calls": "从会话统计",
        "pages_created": {总页数},
        "sources": {source页数},
        "entities": {entity页数},
        "concepts": {concept页数},
        "comparisons": {comparison页数},
        "overviews": {overview页数}
      }
    }
    ```
    - 读取现有 pipeline-context.json，合并 stage_c 节点，再用 write_file 写回
    - 在 `git add` 命令里加上 `raw/pipeline-context.json`

19. **检查并提交所有变更**：
    ```bash
    cd {wiki_local_path}
    git add wiki/ index.md log.md logs/ raw/pipeline-context.json
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

## 注意
- Stage C **不发送 Telegram**，通知由 Stage D（sop-tg-notify）负责。
- push 全部失败 → 记录 `status: push_failed`。
