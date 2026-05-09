# Pipeline 监控 & 追踪指南

## 概述

youtube-video-research-wiki pipeline 由三个阶段组成（Stage B → Stage C → Stage D），每个阶段以独立的 webhook-triggered Hermes session 运行。本参考文档说明如何追踪每个阶段的耗时和 token 消耗。

## 耗时追踪

### 自动追踪（pipeline-context.json）

每个阶段写入 `raw/pipeline-context.json`，记录该阶段的开始/结束时间和耗时：

```json
{
  "pipeline_id": "pipe-abc1234",
  "stage_b": {
    "run_id": "gh-12345-1",
    "start_time": "2026-05-09T10:00:00Z",
    "end_time": "2026-05-09T10:30:00Z",
    "duration_s": 1800,
    "videos_processed": 1,
    "reports_generated": 1,
    "mindmaps_generated": 1
  },
  "stage_c": { ... },
  "stage_d": { ... }
}
```

- pipeline-context.json 在每个阶段写入时追加自己的节点（保留其他阶段数据）
- `duration_s` 由阶段内自己计算（start_time - end_time）
- 归档路径：`logs/pipeline-runs/pipe-{run_id}.json`

### 手动计时（从外部观察者视角）

当你从当前 session 手动触发各阶段时，可以用以下方式计时：

```bash
# 开始计时
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_EPOCH=$(date -u +%s)

# 触发 webhook... 等待完成...

# 结束计时
END_EPOCH=$(date -u +%s)
DURATION=$((END_EPOCH - START_EPOCH))
```

## Token 消耗追踪

### 使用 hermes insights 查找 session 数据

每个 webhook-triggered 的 Hermes session 会记录在 `hermes insights` 中：

```bash
# 查看最近 1 天的所有 session（包括 webhook 触发的）
hermes insights --days 1

# 输出包含按 session 的 token 数据：
# - Input tokens
# - Output tokens
# - Total tokens
# - Tool calls
# - Messages count
# - 模型/提供商
```

webhook session 的识别：
- `hermes sessions list` 显示的平台列为 `webhook`
- 可以用 `session_search` 查找特定 run_id 的会话
- Session title 通常包含 webhook 路由名或 run_id

### 关联 webhook run 到 Hermes session

每个 webhook 触发会创建一个独立的 Hermes session。关联方式：

1. **通过 webhook_subscriptions.json** — 每个路由配置了 provider/model，可据此筛选
2. **通过 session 时间** — webhook run 日志中有 start_time/end_time，可匹配 hermes sessions 的时间范围
3. **通过 session_search** — 用 run_id 搜索可以找到相关会话记录

## 检查 webhook 路由状态

```bash
# 列出所有 webhook 订阅及其状态
hermes webhook list

# 查看具体配置（从 config 中读取）
cat ~/.hermes/webhook_subscriptions.json
```

关键路由：
- `youtube-wiki-ops` — 主编排器（可能 disabled，需确认）
- `sop-notebooklm-research` — Stage B
- `sop-wiki-build` — Stage C
- `sop-tg-notify` — Stage D

## 量化日志字段

每个阶段的 pipeline-context.json 和 webhook run log 应包含：

| 字段 | 来源 | 说明 |
|------|------|------|
| start_time | `date -u +%Y-%m-%dT%H:%M:%SZ` | 阶段开始 |
| end_time | `date -u +%Y-%m-%dT%H:%M:%SZ` | 阶段结束 |
| duration_s | end_epoch - start_epoch | 耗时（秒） |
| api_calls | `hermes insights` 或 session 统计 | 工具调用/API 调用次数 |
| input_tokens | `hermes insights` | 输入 token 数 |
| output_tokens | `hermes insights` | 输出 token 数 |
| total_tokens | `hermes insights` | 总 token 数 |

注意：api_calls/tokens 需要在 webhook session 完成后通过 `hermes insights` 查询，无法在 webhook session 内直接获取。
