# Telegram Message Too Long — Confirmed Fix

## Problem

When the AI model succeeds, the generated report exceeds Telegram's ~4096-character limit:
```
{"ok":false,"error_code":400,"description":"Bad Request: text is too long"}
```

This has been confirmed on multiple dates (2026-05-12, 2026-05-13).

## Root Cause

The script builds a `REPORT` variable that includes:
- Fixed header text (~100 chars)
- `AI_OUTPUT` (unbounded — can be 2000-4000+ chars depending on the model)
- `DIFF_STAT` (~200-500 chars)
- GitHub links (~200 chars)
- Hostname/timestamp (~50 chars)

Even though `DIFF_CONTENT` in the prompt is capped at 500 chars, the AI model can still produce a verbose response.

## Confirmed Fix for the Script

Add truncation of `AI_OUTPUT` and final `REPORT` before sending to Telegram. In `hermes_brain_sync_fallback.sh`, before Step 5:

```bash
# Cap AI output to prevent TG overflow (leave room for headers + links)
MAX_AI_LEN=2000
if [ ${#AI_OUTPUT} -gt $MAX_AI_LEN ]; then
  AI_OUTPUT="${AI_OUTPUT:0:$MAX_AI_LEN}... (truncated)"
fi

# Also hard-cap total report at 3800 chars (TG limit ~4096 with encoding overhead)
MAX_REPORT=3800
if [ ${#REPORT} -gt $MAX_REPORT ]; then
  REPORT="${REPORT:0:$MAX_REPORT}... (truncated)"
fi
```

## Alternative: Split Into Multiple Messages

If the full report is important, send two Telegram messages:
1. Message 1: AI summary (capped at 3800 chars)
2. Message 2: Diff stat + links

```bash
# Send AI summary
echo "$SUMMARY" > /tmp/tg_part1.txt
curl -sS -X POST "$TG_API_URL" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "disable_web_page_preview=true" \
  --data-urlencode "text@/tmp/tg_part1.txt"

# Send links/details
echo "$LINKS" > /tmp/tg_part2.txt
curl -sS -X POST "$TG_API_URL" \
  -d "chat_id=${TG_CHAT_ID}" \
  --data-urlencode "text@/tmp/tg_part2.txt"
```

## Status

- 2026-05-12: First observed — `openrouter/owl-alpha` succeeded, TG send failed
- 2026-05-13: Confirmed again — same model succeeded, TG send failed with identical error
- Fix has NOT been applied to the script as of 2026-05-13
