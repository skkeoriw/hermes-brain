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

## Phase 2: Action（调用 Python 脚本发送通知，无需 LLM）

9. 调用 sop_tg_notify.py：
   ```bash
   python3 /home/zhouhuijuan1987/.hermes/scripts/sop_tg_notify.py \
     --wiki-path {wiki_local_path} \
     --run-id {run_id} \
     --tg-token-env {tg_token_env} \
     --tg-chat-id {tg_chat_id} \
     --repo-url {repo_url}
   ```

   该脚本会：
   - 读取 raw/pipeline-context.json（B+C 完整数据）
   - 组装富文本 Telegram 消息
   - 发送通知
   - 归档 pipeline-context.json 到 logs/pipeline-runs/
   - 写 run-log 并 git commit + push

10. 任务完成，无需其他操作。

---

## Phase 3: Post-Execution（强制执行）

11. 检查脚本输出确认 TG 发送状态（`TG sent: True/False`）。
12. **git commit/push、归档、run-log 均由脚本处理，跳过手动执行。**

## 注意
- TG 发送失败：记录错误，不影响整体，仍然执行 git 归档。
- pipeline-context.json 不存在：退化到读 run-log 文件。
- **退化再退化（双重缺失）：** pipeline-context.json 和 run-logs 都为空/不存在时，从 `raw/youtube-links/` 直接读取视频链接，通过 YouTube oembed API (`https://www.youtube.com/oembed?url=...&format=json`) 获取标题。此时编排"未完整执行"状态通知，标注 Stage B/C 未执行，发送 Telegram 告知当前进展。
- 归档阶段：pipeline-context.json 不存在时，仍应创建最小归档文件 `logs/pipeline-runs/pipe-{run_id}.json`，记录 run_id、各 stage 状态和 tg 通知结果。
