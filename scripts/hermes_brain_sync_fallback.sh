#!/usr/bin/env bash
# Hermes Brain Sync with AI Fallback + Simple Diff Fallback
# 支持多个免费模型，如果都失败则发送简单 diff 报告

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="${HERMES_BRAIN_LOG_DIR:-$HOME/.local/state/hermes-brain}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/sync-fallback.log"

TG_BOT_TOKEN="8660527177:AAEC1wo1WK5CrLY1slci2pEgS3CGTa6QX1g"
TG_CHAT_ID="6938920500"
TG_API_URL="https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage"

# 免费模型列表（按优先级）
FREE_MODELS=(
  "openrouter/owl-alpha"
  "baidu/cobuddy:free"
  "poolside/laguna-m.1:free"
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
  "~google/gemini-flash-latest"
)

{
  echo "=== $(date -Is) hermes-brain sync with fallback start ==="
  
  # Step 1: 执行同步（允许 push 失败）
  echo "+ Running auto_sync.sh"
  /home/zhouhuijuan1987/hermes-brain/scripts/auto_sync.sh || {
    echo "⚠️  auto_sync.sh had issues but continuing..."
  }
  
  # 确保压缩备份存在
  echo "+ Ensuring state.db backup..."
  /home/zhouhuijuan1987/hermes-brain/scripts/state_db_backup.sh backup || true
  
  # Step 2: 收集信息
  echo "+ Capturing commit info"
  CURRENT_SHA=$(git log -1 --format="%H")
  SHORT_SHA=$(git log -1 --format="%h")
  COMMIT_MSG=$(git log -1 --format="%s")
  PREV_SHA=$(git log -1 HEAD~1 --format="%H" 2>/dev/null || echo "N/A")
  REPO_URL=$(git remote get-url origin)
  HOSTNAME=$(hostname)
  ISO_TIME=$(date -Is)
  
  # 提取 owner/repo
  REPO_NAME=$(echo "$REPO_URL" | sed 's/.*[:/]\([^/]*\/[^/]*\)\.git$/\1/')
  COMPARE_LINK="https://github.com/${REPO_NAME}/compare/${PREV_SHA}...${CURRENT_SHA}"
  COMMIT_LINK="https://github.com/${REPO_NAME}/commit/${CURRENT_SHA}"
  
  # 获取 diff 统计
  DIFF_STAT=$(git diff HEAD~1 HEAD --stat 2>/dev/null || echo "N/A")
  DIFF_CONTENT=$(git diff HEAD~1 HEAD --no-color | head -1000 2>/dev/null || echo "N/A")
  
  echo "Commit: $SHORT_SHA - $COMMIT_MSG"
  
  # Step 3: 尝试用 AI 生成报告
  AI_REPORT_SUCCESS=false
  FAILED_MODELS=()
  
  for MODEL in "${FREE_MODELS[@]}"; do
    echo "+ Trying model: $MODEL"
    
    # 构建 hermes 命令
    HERMES_PROMPT="Analyze this git diff and provide a brief Chinese summary (3-5 bullet points) of key changes:\n\n\`\`\`\n${DIFF_STAT}\n\n${DIFF_CONTENT}\n\`\`\`\n\nFormat:\n- 简明扼要\n- 列出主要改动\n- 中文输出"
    
    # 尝试用这个模型调用 hermes
    if AI_OUTPUT=$(hermes chat --model "$MODEL" --provider openrouter "$HERMES_PROMPT" 2>&1 | head -500); then
      # 检查是否成功（没有错误信息）
      if ! echo "$AI_OUTPUT" | grep -qi "error\|fail\|not supported"; then
        AI_REPORT_SUCCESS=true
        echo "✅ Model $MODEL succeeded"
        break
      fi
    fi
    
    FAILED_MODELS+=("$MODEL")
    echo "⚠️  Model $MODEL failed, trying next..."
  done
  
  # Step 4: 生成报告（AI 或简单 diff）
  if [ "$AI_REPORT_SUCCESS" = true ]; then
    echo "+ Generating AI-enhanced report with model info"
    REPORT="✅ Hermes Brain 同步完成

🤖 AI 分析摘要（使用模型: $MODEL）：
${AI_OUTPUT}

📝 变更统计：
\`\`\`
${DIFF_STAT}
\`\`\`

🔗 快速导航：
🔹 查看本次详细变更: ${COMPARE_LINK}
🔹 查看提交详情: ${COMMIT_LINK}

🏠 ${HOSTNAME} ⏰ ${ISO_TIME}"
  else
    echo "⚠️  All AI models failed, using simple diff report"
    
    # 构建失败模型列表（简化版）
    FAILED_COUNT=${#FAILED_MODELS[@]}
    FAILED_MODELS_STR="已尝试 $FAILED_COUNT 个免费模型，均不可用"
    
    # 简化报告内容以适应 TG 限制
    REPORT="✅ Hermes Brain 同步完成

⚠️ AI 分析不可用
${FAILED_MODELS_STR}

📊 变更：
$(echo "$DIFF_STAT" | head -10)

🔗 详情：
${COMMIT_LINK}

🏠 ${HOSTNAME} ⏰ ${ISO_TIME}"
  fi
  
  # Step 5: 发送 TG 报告
  echo "+ Sending Telegram report"
  echo "$REPORT" > /tmp/hermes_brain_sync_tg.txt
  
  TG_RESPONSE=$(curl -sS -X POST "$TG_API_URL" \
    -d "chat_id=${TG_CHAT_ID}" \
    -d "disable_web_page_preview=true" \
    --data-urlencode "text@/tmp/hermes_brain_sync_tg.txt")
  
  if echo "$TG_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Telegram message sent successfully"
  else
    echo "⚠️  Telegram send failed: $TG_RESPONSE"
  fi
  
  echo "=== $(date -Is) hermes-brain sync with fallback success ==="
  
} 2>&1 | tee -a "$LOG_FILE"
