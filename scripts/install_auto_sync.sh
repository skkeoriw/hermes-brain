#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

INTERVAL="${1:-hourly}"
SERVICE_FILE="$SERVICE_DIR/hermes-brain-auto-sync.service"
TIMER_FILE="$SERVICE_DIR/hermes-brain-auto-sync.timer"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Hermes Brain auto sync
Documentation=https://github.com/ChangfengHU/hermes-brain

[Service]
Type=oneshot
WorkingDirectory=$REPO_ROOT
ExecStart=$REPO_ROOT/scripts/auto_sync.sh
EOF

cat > "$TIMER_FILE" <<EOF
[Unit]
Description=Run Hermes Brain auto sync periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=$INTERVAL
Persistent=true
RandomizedDelaySec=5min

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now hermes-brain-auto-sync.timer

echo "Installed user timer: hermes-brain-auto-sync.timer"
echo "Interval: $INTERVAL"
echo "Repo: $REPO_ROOT"
echo "Status:"
systemctl --user --no-pager status hermes-brain-auto-sync.timer || true
