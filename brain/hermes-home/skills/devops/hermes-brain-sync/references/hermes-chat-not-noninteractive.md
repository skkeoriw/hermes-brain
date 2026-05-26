# `hermes chat` is NOT Non-Interactive — Cron Incompatibility

## Problem

The `hermes_brain_sync_fallback.sh` script calls `hermes chat -m <model> -q <prompt> --quiet` expecting it to work in a non-interactive cron context. It does not.

## Root Cause

`hermes chat` always initializes a streaming TUI (terminal UI) thread, regardless of the `--quiet` or `-q` flags. The threading model requires a real TTY. When run without one (cron, subprocess, background), the command:

1. Starts the agent conversation loop
2. Attempts to join a streaming thread (`t.join(timeout=0.3)`)
3. Either hangs indefinitely or raises `KeyboardInterrupt` after `timeout` kills the parent
4. The `timeout 45` wrapper does NOT reliably clean up the subprocess tree

## Evidence (2026-05-25)

```
$ timeout 10 hermes chat -m "openrouter/owl-alpha" --provider openrouter -q "hello" --quiet
# Hangs for 10s, then:
KeyboardInterrupt
EXIT: 124
```

The same command in an interactive terminal works fine.

## Workaround: Direct Telegram Report (No AI)

When the AI chain hangs, skip it entirely:

```bash
pkill -f hermes_brain_sync_fallback
pkill -f 'hermes chat'

cd ~/hermes-brain
SHORT_SHA=$(git log -1 --format="%h")
COMMIT_MSG=$(git log -1 --format="%s")
DIFF_STAT=$(git diff HEAD~1 HEAD --stat 2>/dev/null || echo "N/A")
HOSTNAME=$(hostname)
ISO_TIME=$(date -Is)

REPORT="✅ Hermes Brain 同步完成

⚠️ AI 分析不可用（hermes chat 无法在 cron 模式下运行）

📊 变更统计（commit ${SHORT_SHA}）：
$(echo "$DIFF_STAT" | head -15)

🔗 https://github.com/skkeoriw/hermes-brain/commit/$(git log -1 --format="%H")

🏠 ${HOSTNAME} ⏰ ${ISO_TIME}"

echo "$REPORT" > /tmp/hermes_brain_sync_tg.txt
curl -sS -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "disable_web_page_preview=true" \
  --data-urlencode "text@/tmp/hermes_brain_sync_tg.txt"
```

This completes in ~10s with no AI dependency.

## Proper Fix

Replace `hermes chat` in `hermes_brain_sync_fallback.sh` with a direct HTTP API call:

```bash
# Example: direct OpenRouter API call via curl
curl -sS https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"openrouter/owl-alpha","messages":[{"role":"user","content":"'"$HERMES_PROMPT"'"}]}'
```

This avoids the Hermes CLI entirely and works in any context (cron, background, subprocess).
