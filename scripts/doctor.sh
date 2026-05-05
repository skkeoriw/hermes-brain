#!/usr/bin/env bash
set -euo pipefail

echo "Hermes brain repo: $(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Hermes home: ${HERMES_HOME:-$HOME/.hermes}"

if command -v hermes >/dev/null 2>&1; then
  hermes doctor || true
else
  echo "Hermes command not found."
fi

echo
if [ -d "${HERMES_HOME:-$HOME/.hermes}" ]; then
  echo "Top-level Hermes home files:"
  find "${HERMES_HOME:-$HOME/.hermes}" -maxdepth 1 -mindepth 1 -printf '%f\n' | sort
else
  echo "Hermes home does not exist."
fi
