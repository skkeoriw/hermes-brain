---
name: sop-wiki-build
description: "SOP Stage C: 三阶段增量知识图谱构建，基于 NotebookLM 分析结果构建 wiki，push 结果并发送 Telegram 通知。"
version: 2.9.0
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

6b. **检查重复分析文件（同 video_id 防撞）**：扫描分析文件后，用以下方式检测重复内容：
    ```bash
    cd {wiki_local_path}
    for f in raw/notebooklm-analysis/*.md; do
      vid=$(grep -m1 '^video_id:' "$f" | sed 's/video_id: *//')
      if [ -n "$vid" ]; then
        echo "  $(basename "$f") → video_id=$vid"
      fi
    done
    ```
    若多个文件有相同 `video_id`，说明它们是同一视频的不同版本/重复输出。此时：
    - 对比文件内容（`diff` 或 `md5sum`）
    - **内容完全一致**（等同重复）：只处理第一个，跳过其余，写日志说明
    - **内容不同但 video_id 相同**：以最新/最完整版本为准，写日志说明版本选择

6c. **检查已有 source 页覆盖情况**：若所有扫描文件的 video_id 都已有对应 source 页（通过 `index.md` 或直接检查 `wiki/sources/`），且没有新的 concepts/entities 可提取，视为"无新内容"，走 Step 6 跳过流程。

6d. 读取 `raw/pipeline-context.json`（若存在），记录 stage_b 数据备用。

7. 读取 `index.md` 和 `log.md`（最近 10 条）了解现有内容，避免重复创建。
8. 确保目录存在：`mkdir -p wiki/sources wiki/entities wiki/concepts wiki/comparisons wiki/overview wiki/queries logs/webhook-runs`

---

## Phase 2: Action（生成 wiki 页面）

**目标：调用 LLM API 生成所有 wiki 页面并写入文件。**

9. **⚠️ 环境准备：导出 API 密钥**
   脚本通过 `os.environ` 读取 API 密钥，密钥存储在 `~/.hermes/.env` 中但不会自动导出到 shell。执行脚本前必须手工导出：

   ```bash
   # 推荐：只用 DeepSeek（输出上限更高），避免 DashScope 的 qwen-turbo 8K token 限制
   source ~/.hermes/.env && export DEEPSEEK_API_KEY && unset DASHSCOPE_API_KEY
   ```

10. **策略选择**

    根据报告数量选择脚本（注意：两个脚本都按报告逐份调用 API，但实现不同）：

    | 报告数 | 脚本 | 策略 | 模型 | max_tokens |
    |--------|------|------|------|------------|
    | 1-2 份 | `sop_wiki_builder.py`（并行调用） | ThreadPoolExecutor 并发处理，git diff 查找新增文件 | deepseek-v4-flash | 16,000 |
    | 3+ 份 | `sop-wiki-builder-v2.py`（串行调用） | 逐份处理，glob 扫描磁盘文件（无 git diff 依赖） | deepseek-chat | 12,000 |

    **⚠️ 模型质量差异**：`sop_wiki_builder.py` 使用 `deepseek-v4-flash`（输出容量约 128K），`sop-wiki-builder-v2.py` 使用 `deepseek-chat`（仅 8K max_tokens 上限、12K 脚本设定）——对大输出任务反而不利。报告数≥3 时优先考虑改用 `sop_wiki_builder.py` 的并行模式，或切换其模型配置。

    **路径 10a — 并行调用（推荐，1-2 份报告首选）：**
    ```bash
    python3 /home/zhouhuijuan1987/.hermes/scripts/sop_wiki_builder.py \
      --wiki-path {wiki_local_path} \
      --run-id {run_id} \
      --before-sha {before} \
      --sha {sha}
    ```

    **路径 10b — 串行调用（仅当 10a 因 git diff 找不到文件时使用）：**
    ```bash
    python3 /home/zhouhuijuan1987/.hermes/scripts/sop-wiki-builder-v2.py \
      --wiki-path {wiki_local_path} \
      --run-id {run_id} \
      --before-sha {before} \
      --sha {sha}
    ```

    两个脚本都会：
    - 读取所有分析报告和脑图
    - 生成、写入所有 wiki 页面
    - 更新 index.md 和 pipeline-context.json
    - 自动完成 git commit + push

    脚本输出最后一行是 JSON 状态：`{"status": "success", "pages": N, "duration_s": T}`

11. 检查脚本返回码：
    - 返回 0 = 成功，继续 Phase 3
    - 返回 非0 = 失败，参见 Pitfall #7（失败恢复策略）

---

## Phase 3: Post-Execution（验证与提交）

**目标：验证构建质量，必要时修复并推送到 GitHub。**

> **此阶段独立于 Phase 2，即使 Phase 2 部分失败，也必须执行 Phase 3。**

12. 记录结束时间（仅日志用途，脚本已记录精确时间）。

13. **验证 run-log 存在**：
    ```bash
    ls {wiki_local_path}/logs/webhook-runs/{run_id}.md
    ```

14. **⚠️ 质量验证（git commit/push 后强制执行）**：
    
    **首选方式 — 运行自动验证脚本（推荐）：**
    ```bash
    cd {wiki_local_path}
    bash /home/zhouhuijuan1987/.hermes/skills/devops/sop-wiki-build/scripts/verify-quality.sh {wiki_local_path}
    ```
    脚本执行 7 项检查：frontmatter 完整性、wikilink 数量、内容长度、sources 字段验证、死链检测、双扩展名、文件名截断。

    **或手工执行以下检查：**

    ```bash
    cd {wiki_local_path}
    
    # 14a — 检查双扩展名
    DOUBLE=$(find wiki/ -name '*.md.md' 2>/dev/null | head -5)
    if [ -n "$DOUBLE" ]; then
      echo "FOUND .md.md files:"
      echo "$DOUBLE"
    fi

    # 14b — 检查死链（注意：wikilink 可能带路径前缀如 [[sources/xxx]]）
    for link in $(grep -rho '\[\[[^]]*\]\]' wiki/ --include='*.md' | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u); do
      found=$(find wiki/ -path "*/${link}.md" 2>/dev/null | head -1)
      if [ -z "$found" ]; then
        echo "DEAD LINK: [[${link}]]"
      fi
    done

    # 14c — 检查文件名截断（LLM 有时输出 openclou.md 而非 opencloud.md）
    ALL_WIKILINKS=$(grep -rho '\[\[[^]]*\]\]' wiki/ --include='*.md' | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u)
    ALL_FILES=$(find wiki/ -name '*.md' -exec basename {} .md \; | sort -u)
    for link in $ALL_WIKILINKS; do
      if ! echo "$ALL_FILES" | grep -q "^${link}$"; then
        SIMILAR=$(echo "$ALL_FILES" | grep -i "${link:0:$((${#link}-1))}" | head -1)
        if [ -n "$SIMILAR" ]; then
          echo "POSSIBLE TRUNCATION: wikilink [[${link}]] → on-disk file '${SIMILAR}.md'"
        fi
      fi
    done
    ```

15. **若发现死链或截断，修复并重新提交**：
    ```bash
    # 示例：修复截断的文件名
    mv wiki/entities/openclou.md wiki/entities/opencloud.md
    echo "Fixed: openclou.md → opencloud.md"
    # 修复 wikilink
    sed -i 's/\[\[openclou\]\]/[[opencloud]]/g' wiki/**/*.md
    echo "Fixed: [[openclou]] → [[opencloud]]"
    # 缺失实体页则创建
    cat > wiki/entities/xxx.md << 'EOF'
    ---
    title: 实体名
    type: entity
    ...
    ---
    EOF
    # 重新提交
    git add -A && git commit -m "fix: rename truncated filenames and fix dead links [run:{run_id}]" && git push origin main
    ```

## 注意
- Stage C **不发送 Telegram**，通知由 Stage D（sop-tg-notify）负责。
- push 全部失败 → 记录 `status: push_failed`。

---

## 已知坑点（Pitfalls）

### 1. API 密钥来源
- API 密钥存储在 `~/.hermes/.env`，不是 shell env vars。
- 脚本都使用 `os.environ.get()` 读取，**不自动加载 `.env`**。
- 每次执行前必须：`source ~/.hermes/.env && export DEEPSEEK_API_KEY && unset DASHSCOPE_API_KEY`
- ⚠️ 若同时导出两个 key，脚本 auto-pick DashScope qwen-turbo（max_tokens 仅 8K），导致 400 错误。

### 2. LLM 生成的双 `.md.md` 扩展名
- LLM 有时生成的文件名已包含 `.md`，脚本再加 `.md` 导致 `soul.md.md`。
- 两个脚本都加了 `.rstrip(".md") + ".md"` 修复，但仍应自查：
  ```bash
  find wiki/ -name '*.md.md'
  ```

### 3. 语言一致性
- 内容全中文，frontmatter 字段名用英文。
- 文件路径中的概念名可能中英文混杂 — 统一用小写 slug 或中文语义名。具体规则见 TheSchema.md §7。

### 4. Max tokens 限制（2026-05 实测）
| Provider | 模型 | max_tokens 上限 | 注意 |
|----------|------|-----------------|------|
| DashScope | qwen-turbo | 8,192 | ❌ 硬编码 32000 会 400 错误 |
| DashScope | qwen-plus | 32,768 | ✅ 但输出大时易截断 |
| DeepSeek | deepseek-chat | 8,192 | ❌ 小模型，不够用 |
| DeepSeek | deepseek-v4-flash | ~128K | ✅ 但生成大输出时缓慢 |

详见 `references/api-provider-notes.md`。

### 5a. JSON 截断 — 即使 1 份报告也可能被截断（2026-05-09）
DeepSeek deepseek-v4-flash、qwen-plus 等模型在生成长 JSON 时可能中途截断，导致解析失败。
即使只有 **1 份报告**（期望 9 个页面），实测 JSON 在 ~11700 字符处截断。

**症状**：脚本报 `JSONDecodeError: Unterminated string`。

**恢复策略（三步法）：**

**Step 1 — 检查 raw response 文件**
```bash
ls logs/webhook-runs/{run_id}-r2-raw.txt   # 脚本保存的 raw response
wc -c logs/webhook-runs/{run_id}-r2-raw.txt
```
响应文件以 `{"pages": [...` 开头，包含部分完整的 JSON 页面对象 + 一个截断的末页。

**Step 2 — 用 brace-counting 提取完整页面**
不要用 `json.loads()` 整体解析（会失败），改用逐对象提取：
```python
import json, os
with open('logs/webhook-runs/{run_id}-r2-raw.txt') as f:
    raw = f.read()
# 定位 "pages": [ 之后的内容
pages_start = raw.index('"pages": [') + len('"pages": [')
text = raw[pages_start:]
pages = []
i = 0
while i < len(text):
    while i < len(text) and text[i] in ' \n\r\t,':
        i += 1
    if i >= len(text) or text[i] == ']':
        break
    if text[i] == '{':
        depth, start = 0, i
        while i < len(text):
            if text[i] == '{': depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0: i += 1; break
            i += 1
        try:
            obj = json.loads(text[start:i])
            pages.append(obj)
            filepath = f"{wiki_path}/{obj['path']}"
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as fw: fw.write(obj['content'])
            print(f"✅ {obj['path']}")
        except json.JSONDecodeError:
            print(f"❌ 截断页 at offset {i}（需手动补全）")
print(f"完成: {len(pages)} 页")
```
第 1-5 页通常完好，第 6 页（概念页）常被截断，需手动补全。

**Step 3 — 补全 + 修复死链 + reconcile pipeline-context.json**
- 参考 raw response 的残余内容 + 原报告 + 脑图，手写截断页的完整内容
- 修复死链（可能引用不存在的概念/实体页 — 创建之或删除链接）
- **⚠️ 手动更新 pipeline-context.json**：脚本自动写入的 `pages_created` 可能只统计了成功解析的页数（如 9 而非实际 15），必须手动修正 `pages_created`、`sources`、`entities`、`concepts` 等计数
- 修复 run-log 命名（Pitfall #7）
- 运行强制质量检查（见下方）
- `git add -A && git commit && git push`

**强制质量检查（恢复后必须执行）**：
```bash
cd {wiki_local_path}
find wiki/ -name '*.md.md' 2>/dev/null  # 双扩展名
python3 -c "import re,glob; e={f.replace('wiki/','').rsplit('.md',1)[0].lower() for f in glob.glob('wiki/**/*.md',recursive=True)}; d=0; [print(f'DEAD: {f}: [[{l.strip()}]]') or (d:=d+1) for f in glob.glob('wiki/**/*.md',recursive=True) for l in re.findall(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]',open(f).read()) if not any(l.strip().lower()==s or l.strip().lower()==s.split('/')[-1] for s in e)]; print('OK' if d==0 else f'{d} DEAD')"
```

### 5b. 文件名截断 — LLM 输出不完整
LLM 有时输出截断的文件名（如 `openclou` 缺末尾 'd'）。脚本不会报错，但创建错误的文件名。

**症状**：`openclou.md` 等文件存在，但 wikilink 引用的是全名。

**检查**：Phase 3 step 14c。

**修复**：`mv` 重命名 + `sed` 更新所有 wikilink + 重新提交。

### 6. `sop_wiki_builder.py` 的 git diff 可能找不到文件 — 而非单次调用截断

注意：`sop_wiki_builder.py` 实际上**已经是按报告逐份调用 API**（ThreadPoolExecutor 并行处理），并非单次调用。不存在"一次调用处理所有报告导致输出截断"的问题。

真正的问题是 `get_new_report_files()` 使用 `git diff --name-only --diff-filter=AM` 查找新增文件。当另一个 Webhook 并发提交了同视频但不同文件名的分析报告时，git diff 找不到它（文件不在 `before_sha..sha` 范围内），脚本判断"no new reports"直接跳过。

**症状**：脚本输出 `No new analysis reports in this commit, skipping.` 但磁盘上确实有分析文件。

**检查方法**：
```bash
cd {wiki_local_path}
echo "=== git diff 显示 ==="
git diff --name-only --diff-filter=AM {before_sha} {sha} | grep 'analysis/'
echo "=== 磁盘实际文件 ==="
ls raw/notebooklm-analysis/
```

**解决方案 A — 强制指定 before-sha 为空**（让脚本 fallback 到 glob 扫描）：
```bash
python3 /home/zhouhuijuan1987/.hermes/scripts/sop_wiki_builder.py \
  --wiki-path {wiki_local_path} \
  --run-id {run_id} \
  --before-sha "" \
  --sha HEAD
```

**解决方案 B — 使用 v2 脚本**（始终 glob 扫描，无 git diff 依赖）：
```bash
python3 /home/zhouhuijuan1987/.hermes/scripts/sop-wiki-builder-v2.py \
  --wiki-path {wiki_local_path} \
  --run-id {run_id}
```

### 7. Run-log 命名约定不一致

`sop_wiki_builder.py` 用 `task_id`（格式 `T-{video_id}`）命名运行日志，写为 `logs/webhook-runs/T-9MCjT-eUrTs.md`。但 Phase 3 Step 13 验证的路径是 `logs/webhook-runs/{run_id}.md`（格式 `gh-25605869621-1`）。

**症状**：Phase 3 验证失败（`ls` 找不到文件）。

**处理方式**：
- `sop_wiki_builder.py` 运行后必须用 `run_id` 复制一份 run-log：
  ```bash
  cp logs/webhook-runs/T-{video_id}.md logs/webhook-runs/{run_id}.md
  git add logs/webhook-runs/{run_id}.md
  ```
- `sop-wiki-builder-v2.py` 正常写入 `{run_id}.md`，无需额外处理。

### 7. 失败恢复策略
- 脚本失败后不会自动 git commit。若已写入部分文件但提交失败：
  ```bash
  cd {wiki_local_path}
  git status
  git add -A && git commit -m "chore: partial stage-c [run:{run_id}]" && git push origin main
  ```
- 脚本超时后，删掉 `raw/pipeline-context.json` 中的 `stage_c` 字段后再重试。
- git commit 后发现死链 → 直接修复后新建 commit，无需 revert。

### 8. 并发覆盖 — 多个 webhook 同时运行

另一 webhook 可能在 Phase 1 同步之后推送了新 commit。重置到 origin/main 后分析文件内容可能与原始 run_id 参数不匹配。**始终以 on-disk 扫描结果为准**，不依赖 git diff 或传入 SHA 参数。

#### 8a. 文件重命名/重建 — git diff 找不到文件

**问题（2026-05-09 实测）**：并发 Stage B 运行生成了**改进版分析报告**（同视频、同 video_id）但文件名不同。例如：
- git 历史记录的：`Codex-Chrome-插件技术简报-AI-浏览器自动化的深度评测与分析.md`
- 磁盘上实际有的：`Codex-Chrome-插件功能实测与深度解析简报.md`

`sop_wiki_builder.py` 的 `get_new_report_files()` 通过 `git diff --name-only --diff-filter=AM` 查找文件，但只查 `before_sha` → `sha` 范围内的变更。并发生成的文件名不在该范围内，脚本判断"no new reports"直接跳过。

**诊断方法**：检查 git diff 目标文件名与磁盘实际文件名的差异：
```bash
cd {wiki_local_path}
echo "=== git diff 显示 ==="
git diff --name-only --diff-filter=AM {before_sha} {sha} | grep 'analysis/'
echo "=== 磁盘实际文件 ==="
ls raw/notebooklm-analysis/
```

**解决方案 A — 符号链接（仅用于让脚本通过 exists() 检查）**：
```bash
cd {wiki_local_path}
# 从 git diff 找到旧名，从 ls 找到新名
ln -s "实际文件名.md" "git-diff期望的文件名.md"
# 脚本运行完毕后删除符号链接
rm "git-diff期望的文件名.md"
```

**解决方案 B — 直接使用 v2 脚本**：`sop-wiki-builder-v2.py` 用 `glob("*.md")` 扫描磁盘而非 git diff，天生抗此类问题。但 v2 有坑（见 Pitfall #10）。

#### 8b. 并发 Stage C 写入中文名 wiki 页 — 未跟踪文件堆积

**问题（2026-05-09 实测）**：另一并发 Stage C 运行在本地创建了中文文件名 wiki 页（如 `多代理协作.md`、`端到端自动化.md`、`Chrome调试协议.md`），但未提交也未推送。这些文件作为 `git status` 中的"untracked files"堆积，导致 `git add -A` 时一并提交，可能覆盖/混入你的修复。

**检查方法**：
```bash
cd {wiki_local_path}
git ls-files --others --exclude-standard -- wiki/
```

**处理**：提交前确认这些 untracked 文件是否为本运行期望的内容。若属于并发运行但不冲突，可保留；若冲突（同概念不同文件名），需协调或删除。

#### 8c. 合并冲突时的提交策略

当并发提交导致本地 HEAD 落后远端时，不要丢失你的修复：
```bash
# 先拉取
git pull --ff-only origin main
# 若有冲突，优先保留你的修复版本
# 将你的修复合并后提交
git add -A
git commit -m "fix: merge concurrent runs, keep quality fixes [run:{run_id}]"
git push origin main
```

### 9. verify-quality.sh 假阳性 — 带路径前缀的 wikilink

`verify-quality.sh` 的 Check 5（死链检测）在 version 2.8.0 之前使用 `find -name`，无法匹配带路径前缀的 wikilink（如 `[[sources/Codex-Chrome-插件功能特性与实测深度简报]]`），导致假阳性。

**症状**：验证报告显示死链 `[[sources/xxx]]`，但文件实际存在于 `wiki/sources/xxx.md`。

**确认方法**：用 Python 脚本进行精确扫描（Pitfall 5a 的 Python 脚本支持路径前缀，是更准确的死链检测方式）：
```bash
python3 -c "import re,glob; e={f.replace('wiki/','').rsplit('.md',1)[0].lower() for f in glob.glob('wiki/**/*.md',recursive=True)}; d=0; [print(f'DEAD: {f}: [[{l.strip()}]]') or (d:=d+1) for f in glob.glob('wiki/**/*.md',recursive=True) for l in re.findall(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]',open(f).read()) if not any(l.strip().lower()==s or l.strip().lower()==s.split('/')[-1] for s in e)]; print('OK' if d==0 else f'{d} DEAD')"
```

**⚠️ 注意**：上述 Python 方法比 `verify-quality.sh` 的 Check 5 更**严格**。它会捕获以下 `verify-quality.sh` 可能漏掉的死链类型：

| 类型 | 示例 | 原因 |
|------|------|------|
| **大小写不匹配** | `[[Computer Use]]` → `computer-use.md` | wikilink 区分大小写，Python 用 `.lower()` 比较 |
| **空格 vs 连字符** | `[[Codex Chrome 插件]]` → `Codex-Chrome-插件.md` | LLM 随机生成空格或连字符 |
| **缩写 vs 全名** | `[[CDP]]` → `chrome-devtools-protocol.md` | LLM 可能用缩写，但文件名用全名 |
| **词序变化** | `[[Chrome调试协议]]` → `chrome-devtools-protocol.md` | LLM 用中文名，但文件名用英文 slug |

**建议**：在 Phase 3 质量验证时，**同时运行** `verify-quality.sh` 和 Python 死链检测，以覆盖所有类型的死链。

**已修复**：version 2.9.0 已将 `find -name` 改为 `find -path`，消除了此假阳性。

### 10. 重复分析文件 — 同视频多版本/identical 输出

**问题**：Stage B 可能为同一视频生成多个分析文件（不同文件名但同一 `video_id` 或完全相同的内容）。此时：
- `sop_wiki_builder.py` 的 `get_new_report_files()` 通过 `git diff --diff-filter=AM` 检测"新"文件，可能把 duplicate 文件也视为新报告
- 处理 duplicate 文件会创建第二个 source 页（违反 TheSchema "每视频一个 source 页" 规则）

**实测案例（2026-05-09）**：
- 磁盘上有两个文件：`Codex-Chrome-插件功能实测与深度解析简报.md`（已有 source 页）和 `Codex-Chrome-插件技术简报-AI-浏览器自动化的深度评测与分析.md`（新文件，但内容完全 identical）
- git HEAD 中第二个文件仅 55 字节（引用文件），但本地工作树恢复后有 6932 字节完整内容
- 脚本若处理第二个文件，会创建重复 source 页

**检测方法**：

```bash
# 方法 1：对比 video_id（推荐）
cd {wiki_local_path}
for f in raw/notebooklm-analysis/*.md; do
  vid=$(grep -m1 '^video_id:' "$f" | sed 's/video_id: *//')
  echo "$(basename "$f") → video_id=$vid"
done | sort -k2

# 方法 2：对比文件内容
cd {wiki_local_path}
for f in raw/notebooklm-analysis/*.md; do
  md5sum "$f"
done | sort

# 方法 3：检查 git diff 与磁盘实际文件的差异
echo "=== git diff 显示 ==="
git diff --name-only --diff-filter=AM {before_sha} {sha} | grep 'analysis/'
echo "=== 磁盘实际文件 ==="
ls raw/notebooklm-analysis/
```

**处理**：
- **内容完全一致**：只处理第一个文件（按字母序或按 git diff 顺序），其余跳过
- **内容不同但同 video_id**：保留最完整的版本，日志中记录选择依据
- **若所有文件都已处理过**：走 Step 6 跳过流程，写日志，不发 Telegram

**❗ 不要强行运行脚本处理 duplicate**：脚本不会检测 duplicate，会直接调用 LLM 并生成第二个重复的 source 页。手动跳过并在日志中记录重复原因。

### 11. git 存储的分析文件与工作树不一致

**问题**：`git stash` + `git stash pop` 的保护性同步流程可能恢复出与 git HEAD 不一致的文件版本。典型场景：
- git HEAD 中某分析文件仅 55 字节（引用/占位文件）
- stash 恢复后该文件有 6932 字节（完整分析内容，来自并发 Stage B 的未跟踪文件）

**后果**：`get_new_report_files()` 检查 `p.exists()` 会看到完整文件，但脚本的 prompt 输入可能与预期不同。

**处理**：
```bash
# 恢复后先检查文件大小，对比 git HEAD
cd {wiki_local_path}
for f in raw/notebooklm-analysis/*.md; do
  head_size=$(git show HEAD:"$f" 2>/dev/null | wc -c)
  disk_size=$(wc -c < "$f")
  if [ "$head_size" != "$disk_size" ]; then
    echo "⚠️ $f: git_HEAD=${head_size}B vs disk=${disk_size}B"
  fi
done

# 若文件大小不一致，以 git HEAD 版本为准
git checkout HEAD -- "raw/notebooklm-analysis/不一致的文件.md"
```

### 10. v2 脚本（`sop-wiki-builder-v2.py`）的已知限制

`sop-wiki-builder-v2.py`（分批调用版本）有以下几个已知问题：

| 问题 | 详情 | 严重度 |
|------|------|--------|
| **模型选择固化** | 硬编码使用 `deepseek-chat`（max_tokens=8192），不使用 `deepseek-v4-flash`。这在生成长 JSON 时容量不足。 | ⚠️ 高 |
| **内容截断** | 报告内容截断到 5000 字符（`content[:5000]`），脑图截断到 1500 字符。可能导致 LLM 缺失关键上下文。 | ⚠️ 中 |
| **max_tokens 低** | 只设 12000 tokens，比 v1 脚本的 16000 少 | ⚠️ 中 |
| **无重试机制** | 单次 API 调用失败后直接 `continue`，不保存 raw response 供恢复 | ⚠️ 中 |
| **覆盖 index.md** | 全量重写 index.md，不合并已有条目（v1 脚本有合并逻辑） | ✅ 低（仅在首次运行时） |

**何时用 v2**：仅当报告数 ≤2 且 v1 脚本因内容过大截断时（3+ 报告首选 v2，但须注意上述限制）。

### 12. 死链修复时的文件名匹配陷阱 — wikilink 格式 vs 实际文件名

**问题（2026-05-09 实测）**：手动创建缺失页面修复死链时，创建的文件名可能与 wikilink 不匹配，导致"修复"后死链依然存在。

**典型场景**：
- wikilink 是 `[[Token节省方案]]`（无连字符，纯中文）
- 你创建了 `Token-节省方案.md`（含连字符，模仿其他文件命名）
- 检查时显示 ✅ 文件存在，但死链检查器依然报死链
- 原因：`[[Token节省方案]]` 期望文件名 `Token节省方案.md`，而非 `Token-节省方案.md`

**检查方法**：
```bash
# 对每个死链修复，确认 wikilink 文本 == 文件名（不含 .md）
cd {wiki_local_path}
for link in $(grep -rho '\[\[[^]]*\]\]' wiki/ --include='*.md' | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u); do
  found=$(find wiki/ -name "${link}.md" 2>/dev/null | head -1)
  if [ -z "$found" ]; then
    echo "DEAD: [[${link}]] — 文件名不匹配"
  fi
done
```

**修复**：重命名文件以匹配 wikilink 文本：
```bash
mv wiki/concepts/Token-节省方案.md wiki/concepts/Token节省方案.md
```

**预防**：创建缺失页面时，直接用 wikilink 文本作为文件名（不做规范化），并在 `find wiki/ -name` 确认后再提交。

### 13. pipeline-context.json 页数不准确 — 恢复后须手动修正

**问题（2026-05-09 实测）**：JSON 截断恢复后，脚本自动写入的 pipeline-context.json 中 `pages_created` 只统计了成功解析的页数（如 9），但实际总页数（含恢复页）可能更多（如 15）。

**症状**：pipeline-context.json 中 `stage_c.pages_created` 远低于 `find wiki/ -type f -name '*.md' | wc -l`。

**修复**：恢复完成后，手动读取并更新 pipeline-context.json：
```python
import json
with open('raw/pipeline-context.json') as f:
    ctx = json.load(f)
ctx['stage_c']['pages_created'] = 15  # 实际页数
ctx['stage_c']['sources'] = 2
ctx['stage_c']['entities'] = 6
ctx['stage_c']['concepts'] = 6
ctx['stage_c']['note'] = 'JSON truncated, recovered from raw response'
with open('raw/pipeline-context.json', 'w') as f:
    json.dump(ctx, f, indent=2, ensure_ascii=False)
```
同样需要修正 log.md、index.md 和 run-log 中的计数。

### 11. index.md 中的死链 — 质量验证的盲区

`verify-quality.sh` 只检查 `wiki/` 目录下的文件，**不检查 `index.md`** 和 `log.md`。但脚本更新的 index.md 可能包含带空格/大小写不正确的 wikilink 条目。

**症状**：`index.md` 中的条目如 `- [[Codex Chrome 插件功能实测与深度解析简报]]`（空格）指向上不存在的文件（实际文件为全连字符 slug）。

**检查方法**（Phase 3 新增步骤）：
```bash
cd {wiki_local_path}
# 检查 index.md 和 log.md 中的 wikilink
grep -n '\[\[.*\]\]' index.md log.md 2>/dev/null | sed 's/\[\[/,/' | while IFS=, read -r line slug; do
  slug=$(echo "$slug" | sed 's/\[\[//;s/\]\]//;s/|.*//')
  found=$(find wiki/ -path "*/${slug}.md" 2>/dev/null | head -1)
  if [ -z "$found" ] && [ -n "$slug" ]; then
    echo "  ❌ DEAD LINK in $line → [[${slug}]]"
  fi
done
```
