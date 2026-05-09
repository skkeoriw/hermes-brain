# API Provider Notes (2026-05 实测)

## DashScope (阿里通义千问)

| 模型 | max_tokens 上限 | 上下文窗口 | 备注 |
|------|----------------|-----------|------|
| qwen-turbo | 8,192 | 1M tokens | ❌ `max_tokens: 32000` 会 400 |
| qwen-plus | 32,768 | 1M tokens | ✅ 可用，但大输出易截断 |
| qwen-max | 32,768 | 32K tokens | 备用，速度较慢 |

**Endpoint**: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
**Auth**: `Authorization: Bearer {DASHSCOPE_API_KEY}`

**实测结果**:
- qwen-plus + max_tokens=32000 + 3报告(23KB prompt) → 29,934 chars 输出，JSON 截断
- 截断点位于最后一个字符串值内（`Unterminated string`）
- qwen-plus + max_tokens=32768 → API 调用超时

## DeepSeek

| 模型 | max_tokens 上限 | 上下文窗口 | 备注 |
|------|----------------|-----------|------|
| deepseek-chat | 8,192 | 64K tokens | ❌ 仅 8K 输出限制 |
| deepseek-v4-flash | ~16,384 | 未知 | ✅ 但 `max_tokens=32768` 会 400 Bad Request |

**Endpoint**: `https://api.deepseek.com/v1/chat/completions`
**Auth**: `Authorization: Bearer {DEEPSEEK_API_KEY}`

**实测结果**:
- deepseek-v4-flash + max_tokens=32768 → **400 Bad Request**（该模型不支持 32K 输出 token）
- 改 `max_tokens=16384` → 1 份报告（11K prompt）→ 15K 输出，正常
- deepseek-v4-flash + 3报告 → 5,211 字节后在 ~50 秒后停止传输数据
- 前台 300s timeout 后仍未完成

**注意**: `sop_wiki_builder.py` 原设 `max_tokens: 32768`，与 deepseek-v4-flash 不兼容。已修复为 16384。

## OpenRouter (免费)

| 模型 | 备注 |
|------|------|
| deepseek/deepseek-v4-flash:free | 未测试，备用 |

## 经验法则

### 输出量估计
- 1 份分析报告 → 5-7 页面 → ~8-12KB JSON
- 3 份分析报告 → 15-20 页面 → ~25-35KB JSON

### 推荐策略
```
报告数 ≤ 2 → 单次调用，DeepSeek v4 flash（需耐心等待 2-3 分钟）
报告数 ≥ 3 → 分批次，每份报告单独调用（v2 脚本）
max_tokens 不要设到 provider 上限，留 20% 余量
```

### 脚本 auto-pick 优先级（sop_wiki_builder.py line 21-31）
1. `DASHSCOPE_API_KEY` 存在 → 用 `qwen-turbo`（最大 8K 输出，不够用！）
2. `DEEPSEEK_API_KEY` 存在 → 用 `deepseek-v4-flash`
3. `OPENROUTER_API_KEY` 存在 → 用 `deepseek/deepseek-v4-flash:free`

⚠️ 两个 key 都设了 → 自动选 DashScope (qwen-turbo) → 400 错误！
