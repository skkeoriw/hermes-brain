#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 1
  fi
}

need git
need curl
need python3
bash "$REPO_ROOT/scripts/install_hermes.sh"
bash "$REPO_ROOT/scripts/sync_from_repo_to_local.sh"

echo
cat <<'EOF'
Bootstrap complete.

Next recommended commands:
  hermes doctor
  hermes

If this machine should run Telegram/webhook/API gateway:
  hermes gateway install
  hermes gateway start
EOF
