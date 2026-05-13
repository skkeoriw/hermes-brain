# Direct Telegram Fallback Procedure

When `hermes_brain_sync_fallback.sh` hangs (typically due to `hermes chat` subprocess hangs), kill it and send the report directly.

## Kill hung processes

```bash
pkill -f hermes_brain_sync_fallback
pkill -f 'hermes chat'
```

## Collect diff info manually

```bash
cd ~/hermes-brain
SHORT_SHA=$(git log -1 --format="%h")
COMMIT_MSG=$(git log -1 --format="%s")
DIFF_STAT=$(git diff HEAD~1 HEAD --stat 2>/dev/null || echo "N/A")
HOSTNAME=$(hostname)
ISO_TIME=$(date -Is)
```

## Send via curl (no hermes dependency)

```bash
TG_BOT_TOKEN="<bot_token>"
TG_CHAT_ID="<chat_id>"
TG_API_URL="https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage"

REPORT="✅ Hermes Brain 同步完成 (manual fallback)

⚠️ 回退脚本超时，手动发送报告

📊 变更统计：
${DIFF_STAT}

📝 最后提交: ${SHORT_SHA} - ${COMMIT_MSG}

🏠 ${HOSTNAME} ⏰ ${ISO_TIME}"

# CRITICAL: Truncate to avoid Telegram 4096-char limit
REPORT="${REPORT:0:3800}"

echo "$REPORT" > /tmp/hermes_brain_sync_tg.txt

curl -sS -X POST "$TG_API_URL" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "disable_web_page_preview=true" \
  --data-urlencode "text@/tmp/hermes_brain_sync_tg.txt"
```

**⚠️ Telegram message length limit**: Telegram caps messages at ~4096 characters. Always truncate the report to ≤3800 chars before sending. The `hermes_brain_sync_fallback.sh` script does NOT do this — if the AI model succeeds and generates a long report, the TG send will fail with `400 Bad Request: message is too long`. This has occurred on 2026-05-12 and 2026-05-13.

## Verification

Check the response for `"ok":true`:

```bash
# Should contain: {"ok":true,"result":{"message_id":...
```

## When to use this fallback

- `hermes_brain_sync_fallback.sh` has been running for >5 minutes with no output
- `ps aux | grep 'hermes chat'` shows stale processes (days old)
- All AI models are returning errors or timing out
- You need to send a report NOW and can't wait for the script

## Root cause

`hermes chat -m <model>` has two failure modes when the model/provider is unreachable:

**Mode 1 — Hang (most common)**: The subprocess never returns. `timeout 45` doesn't always propagate the signal to the hermes subprocess tree, so zombie `hermes chat` processes accumulate over days. Kill with `pkill -f 'hermes chat'`.

**Mode 2 — KeyboardInterrupt crash (observed 2026-05-10)**: `hermes chat` sometimes crashes with a `KeyboardInterrupt` traceback. This is an internal signal handler issue in `hermes_cli/main.py` and `cli.py` — the `_signal_handler_q` raise can be triggered by the timeout wrapper, killing the process but also printing a noisy traceback. The script treats this as a model failure and moves on, but the traceback can confuse log parsing.

In both modes, the outcome is the same: the model call fails and the script should fall through to the next model or the simple diff report. If ALL models fail, use the direct curl procedure above.
