#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

SKIP_INSTALL=0
RUN_DOCTOR=1
INSTALL_AUTO_SYNC=1
AUTO_SYNC_INTERVAL="hourly"
for arg in "$@"; do
  case "$arg" in
    --skip-install) SKIP_INSTALL=1 ;;
    --no-doctor) RUN_DOCTOR=0 ;;
    --no-auto-sync) INSTALL_AUTO_SYNC=0 ;;
    --auto-sync-interval=*) AUTO_SYNC_INTERVAL="${arg#*=}" ;;
  esac
done

command -v git >/dev/null || { echo "missing git" >&2; exit 1; }
command -v curl >/dev/null || { echo "missing curl" >&2; exit 1; }
command -v python3 >/dev/null || { echo "missing python3" >&2; exit 1; }

if [ "$SKIP_INSTALL" = "0" ]; then
  bash scripts/install_hermes.sh
fi

# Pull latest repo content if origin exists.
if git remote get-url origin >/dev/null 2>&1; then
  git pull --ff-only || true
fi

python3 scripts/hermes_brain_sync.py repo-to-local

# ── 路径适配：将 brain 里的旧机器路径替换为当前用户 home ──────────────────────
# brain 里的 config.yaml / webhook_subscriptions.json 可能含有原机器的绝对路径
# 找出 brain 里记录的旧 home（取第一个 /home/xxx 或 /Users/xxx 路径）
OLD_HOME=$(grep -oE '/home/[^/]+|/Users/[^/]+' \
  "$HOME/.hermes/config.yaml" "$HOME/.hermes/webhook_subscriptions.json" 2>/dev/null \
  | grep -oE '/home/[^:]+|/Users/[^:]+' | head -1 | sed 's|/[^/]*$||' || true)

if [ -n "$OLD_HOME" ] && [ "$OLD_HOME" != "$HOME" ]; then
  echo "Adapting paths: $OLD_HOME → $HOME"
  sed -i "s|$OLD_HOME|$HOME|g" "$HOME/.hermes/config.yaml"
  sed -i "s|$OLD_HOME|$HOME|g" "$HOME/.hermes/webhook_subscriptions.json"
  echo "Path substitution done."
fi

# ── 克隆 agent-brain-plugins（skills 来源）────────────────────────────────────
BRAIN_REPO="https://github.com/skkeoriw/agent-brain-plugins.git"
BRAIN_LOCAL="$HOME/agent-brain-plugins"
if [ ! -d "$BRAIN_LOCAL/.git" ]; then
  echo "Cloning agent-brain-plugins → $BRAIN_LOCAL"
  git clone "$BRAIN_REPO" "$BRAIN_LOCAL"
else
  echo "agent-brain-plugins already exists, pulling latest..."
  git -C "$BRAIN_LOCAL" pull --ff-only || true
fi

# New machines default to pull role. Only a deliberate
# `./scripts/set_sync_role.sh push --git --push` makes a machine the single writer.
if [ ! -f "$HOME/.config/hermes-brain/sync-role" ]; then
  python3 scripts/hermes_brain_role.py set pull
fi

if [ "$INSTALL_AUTO_SYNC" = "1" ]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl --user status >/dev/null 2>&1; then
    bash scripts/install_auto_sync.sh "$AUTO_SYNC_INTERVAL" || true
  else
    echo "systemd user service not available; skip auto sync timer install"
    echo "You can run manually: cd $(pwd) && ./scripts/auto_sync.sh"
  fi
fi

if [ "$RUN_DOCTOR" = "1" ] && command -v hermes >/dev/null 2>&1; then
  hermes doctor || true
fi

echo "Bootstrap finished. Start Hermes with: hermes"
