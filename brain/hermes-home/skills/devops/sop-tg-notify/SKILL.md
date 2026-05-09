---
name: sop-tg-notify
description: "SOP Stage D: 读取 pipeline-context.json，组装完整 pipeline 运行报告，发送富文本 Telegram 通知。"
version: 1.0.0
---

# SOP Stage D: Pipeline TG Notification

## 触发条件
webhook 收到 `stage=tg-notify`

---

## Phase 1: Pre-Execution

1. 记录开始时间：`START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. `cd {wiki_local_path}`
3. 保护性同步：
   ```bash
   git fetch origin && git checkout main && git pull --ff-only origin main
   ```
4. 读取 `raw/pipeline-context.json`，获取 stage_b 和 stage_c 的完整数据。
5. 若文件不存在：从 `logs/webhook-runs/` 读取最近两个 run-log 推断数据。

---

## Phase 2: Action（组装消息）

6. 从 pipeline-context.json 提取：
   - stage_b: duration_s、api_calls、videos_processed、reports/mindmaps
   - stage_c: duration_s、api_calls、pages_created（sources/entities/concepts/comparisons/overviews）

7. 从 `wiki/sources/` 读取所有 source 页的 title 和 video_url。

8. 计算总耗时 = stage_b.duration_s + stage_c.duration_s

9. 组装 Telegram 消息（格式如下）：
```
[YOUTUBE-WIKI-RUN] 🎬

📹 本次处理 {n} 条视频：
{视频标题列表，每行一个，带序号}

⏱️ 各阶段耗时：
  Stage B (NotebookLM): {stage_b.duration_s}s
  Stage C (知识图谱):   {stage_c.duration_s}s
  全程合计:             {total}s

🔢 LLM 调用：
  Stage B: {stage_b.api_calls} 次
  Stage C: {stage_c.api_calls} 次

📊 知识图谱产出：
  Source 页: {sources}  Entity 页: {entities}
  Concept 页: {concepts}  Comparison: {comparisons}  Overview: {overviews}
  总页数: {total_pages}

🔗 快捷导航：
{每个视频的 source 页 GitHub 链接，格式：· {标题} → {repo_url}/blob/main/wiki/sources/{文件名}}

run: {run_id}
```

---

## Phase 3: Post-Execution（强制执行）

10. 发送 Telegram：
    ```bash
    TOKEN=$(printenv {tg_token_env})
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
      -d "chat_id={tg_chat_id}" \
      -d "disable_web_page_preview=true" \
      --data-urlencode "text={组装好的消息}"
    ```

11. 归档 pipeline-context.json：
    ```bash
    mkdir -p logs/pipeline-runs
    cp raw/pipeline-context.json logs/pipeline-runs/pipe-{run_id}.json
    rm raw/pipeline-context.json
    ```

12. 写执行日志到 `logs/webhook-runs/{run_id}.md`（标注 stage: stage_d）。

13. git add + commit + push：
    ```bash
    git add logs/
    if [ -n "$(git status --porcelain)" ]; then
      git commit -m "chore: tg notify done [run:{run_id}]"
      git push origin main
    fi
    ```

## 注意
- TG 发送失败：记录错误，不影响整体，仍然执行 git 归档。
- pipeline-context.json 不存在：退化到读 run-log 文件。
