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

6b. 读取 `raw/pipeline-context.json`（若存在），记录 stage_b 数据备用。

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

    根据报告数量选择脚本：

    | 报告数 | 脚本 | 策略 |
    |--------|------|------|
    | 1-2 份 | `sop_wiki_builder.py`（单次调用） | 一次 API 生成所有页面，简单快速 |
    | 3+ 份 | `sop_wiki_builder_v2.py`（分批调用） | 每份报告单独 API 调用，避免输出截断 |

    **路径 10a — 单次调用（≤2 份报告）：**
    ```bash
    python3 /home/zhouhuijuan1987/.hermes/scripts/sop_wiki_builder.py \
      --wiki-path {wiki_local_path} \
      --run-id {run_id} \
      --before-sha {before} \
      --sha {sha}
    ```

    **路径 10b — 分批调用（3+ 份报告，推荐）：**
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
即使只有 **1 份报告**（期望 9 个页面），实测 JSON 在 ~11700 字符处截断，auto-start 概念内容不全。

**症状**：脚本报 `JSONDecodeError: Unterminated string`。

**恢复策略**：
1. 检查 `logs/webhook-runs/{run_id}.response.txt`，找到完整的 JSON prefix
2. 手动提取已经生成的完整页面（前 8 页通常完好）
3. 补全被截断页面的缺失部分（参考原文）
4. 修复死链（`[[hermes-agent]]` 等已删除页面的引用）
5. 手动写入 index.md、pipeline-context.json、log.md
6. `git add -A && git commit && git push`

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

### 6. 单次调用 3+ 报告 → 输出过大 → 截断/超时
`sop_wiki_builder.py` 用一次 LLM 调用处理所有报告。实测：
- **3 份报告**：期望输出 15+ 页面（~30KB JSON），易截断
- **解决方案**：报告数 ≥ 3 时使用 `sop_wiki_builder_v2.py`（分批调用）

### 7. 失败恢复策略
- 脚本失败后不会自动 git commit。若已写入部分文件但提交失败：
  ```bash
  cd {wiki_local_path}
  git status
  git add -A && git commit -m "chore: partial stage-c [run:{run_id}]" && git push origin main
  ```
- 脚本超时后，删掉 `raw/pipeline-context.json` 中的 `stage_c` 字段后再重试。
- git commit 后发现死链 → 直接修复后新建 commit，无需 revert。

### 8. 并发覆盖 — 两个 webhook 同时运行

另一 webhook 可能在 Phase 1 同步之后推送了新 commit。重置到 origin/main 后分析文件内容可能与原始 run_id 参数不匹配。**始终以 on-disk 扫描结果为准**，不依赖 git diff 或传入 SHA 参数。

**实测案例（2026-05-09）**：
Stage C 脚本 `sop_wiki_builder.py` 提交了含文件名截断（`openclou.md`）的文件到 `6495426`。修复时在本地 `mv` 重命名后使用 `git reset HEAD .` 清空了暂存区。此时另一并发的 Stage B 任务拉取了 `6495426`，添加了 raw 分析文件，随后执行 `git add -A` 并 commit → **自动捕获了本地重命名的修正文件**，将 `openclou.md` 和 `api-enable.md` 的修正一并 push。

**启发**：
- 并发 Stage B 的 `git add -A` 会捕获工作目录的所有变更，包含你的本地修复 → 自动传播到远端
- 相当于"顺便帮你提交了修复"，省去一次单独 commit
- 这不是 bug，而是 git 的预期行为，但前提是工作目录的乱状态是"干净的修复"而非"半成品"

### 9. verify-quality.sh 假阳性 — 带路径前缀的 wikilink

`verify-quality.sh` 的 Check 5（死链检测）在 version 2.8.0 之前使用 `find -name`，无法匹配带路径前缀的 wikilink（如 `[[sources/Codex-Chrome-插件功能特性与实测深度简报]]`），导致假阳性。

**症状**：验证报告显示死链 `[[sources/xxx]]`，但文件实际存在于 `wiki/sources/xxx.md`。

**确认方法**：用 Python 脚本进行精确扫描（Pitfall 5a 的 Python 脚本支持路径前缀，是更准确的死链检测方式）：
```bash
python3 -c "import re,glob; e={f.replace('wiki/','').rsplit('.md',1)[0].lower() for f in glob.glob('wiki/**/*.md',recursive=True)}; d=0; [print(f'DEAD: {f}: [[{l.strip()}]]') or (d:=d+1) for f in glob.glob('wiki/**/*.md',recursive=True) for l in re.findall(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]',open(f).read()) if not any(l.strip().lower()==s or l.strip().lower()==s.split('/')[-1] for s in e)]; print('OK' if d==0 else f'{d} DEAD')"
```

**已修复**：version 2.9.0 已将 `find -name` 改为 `find -path`，消除了此假阳性。
