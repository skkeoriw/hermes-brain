#!/usr/bin/env bash
set -euo pipefail

if command -v hermes >/dev/null 2>&1; then
  echo "Hermes already installed: $(command -v hermes)"
  hermes --version || true
  exit 0
fi

echo "Installing Hermes Agent..."
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

echo "Hermes install attempted. If hermes is not on PATH yet, open a new shell or source your shell rc file."
