#!/usr/bin/env bash
set -euo pipefail
if command -v hermes >/dev/null 2>&1; then
  echo "Hermes already installed: $(command -v hermes)"
  hermes --version || true
  exit 0
fi
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
