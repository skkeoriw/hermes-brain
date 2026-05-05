#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/brain/hermes-home"
DEST="${HERMES_HOME:-$HOME/.hermes}"
BACKUP_DIR="$HOME/.hermes-brain-backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$BACKUP_DIR/hermes-home-before-restore-$STAMP"

if [ ! -d "$SRC" ]; then
  echo "ERROR: repo brain not found: $SRC" >&2
  exit 1
fi

if [ -d "$DEST" ]; then
  echo "Backing up existing Hermes home: $DEST -> $BACKUP"
  python3 - "$DEST" "$BACKUP" <<'PY'
import shutil, sys
from pathlib import Path
src = Path(sys.argv[1]).expanduser()
dst = Path(sys.argv[2]).expanduser()
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst, symlinks=True)
PY
fi

mkdir -p "$DEST"

echo "Restoring Hermes brain from $SRC to $DEST"
python3 - "$SRC" "$DEST" <<'PY'
import shutil, sys
from pathlib import Path
src = Path(sys.argv[1]).expanduser()
dst = Path(sys.argv[2]).expanduser()
if dst.exists():
    for child in dst.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
else:
    dst.mkdir(parents=True)
for child in src.iterdir():
    target = dst / child.name
    if child.is_dir():
        shutil.copytree(child, target, symlinks=True)
    else:
        shutil.copy2(child, target)
PY

# Basic permission hardening for plaintext credentials.
chmod 700 "$DEST" 2>/dev/null || true
for f in "$DEST/.env" "$DEST/auth.json" "$DEST/config.yaml" "$DEST/webhook_subscriptions.json"; do
  [ -f "$f" ] && chmod 600 "$f" || true
done

if command -v hermes >/dev/null 2>&1; then
  echo "Running hermes doctor..."
  hermes doctor || true
else
  echo "Hermes command not found. Run scripts/install_hermes.sh or scripts/bootstrap_new_machine.sh."
fi

echo "Restore complete. Backup: $BACKUP"
