#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

SKIP_INSTALL=0
RUN_DOCTOR=1
for arg in "$@"; do
  case "$arg" in
    --skip-install) SKIP_INSTALL=1 ;;
    --no-doctor) RUN_DOCTOR=0 ;;
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

if [ "$RUN_DOCTOR" = "1" ] && command -v hermes >/dev/null 2>&1; then
  hermes doctor || true
fi

echo "Bootstrap finished. Start Hermes with: hermes"
