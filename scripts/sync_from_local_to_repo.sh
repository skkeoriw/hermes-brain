#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${HERMES_HOME:-$HOME/.hermes}"
DEST="$REPO_ROOT/brain/hermes-home"

if [ ! -d "$SRC" ]; then
  echo "ERROR: Hermes home not found: $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"

echo "Syncing local Hermes data from $SRC to $DEST"

python3 - "$SRC" "$DEST" <<'PY'
import fnmatch, os, shutil, sys
from pathlib import Path
src = Path(sys.argv[1]).expanduser().resolve()
dest = Path(sys.argv[2]).expanduser().resolve()
exclude_names = {'hermes-agent', 'logs', 'cache', 'audio_cache', '__pycache__', '.update_check'}
exclude_patterns = {'*.pyc', '*.lock', '*.pid', '*.log', '*-wal', '*-shm'}

def excluded(path: Path) -> bool:
    name = path.name
    if name in exclude_names:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in exclude_patterns)

if dest.exists():
    for child in dest.iterdir():
        if child.name == '.git':
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
else:
    dest.mkdir(parents=True)

for root, dirs, files in os.walk(src):
    rootp = Path(root)
    dirs[:] = [d for d in dirs if not excluded(rootp / d)]
    rel = rootp.relative_to(src)
    out_dir = dest / rel
    out_dir.mkdir(parents=True, exist_ok=True)
    for file in files:
        inp = rootp / file
        if excluded(inp):
            continue
        out = out_dir / file
        shutil.copy2(inp, out)
PY

cat > "$REPO_ROOT/brain/manifest.json" <<EOF
{
  "source": "$SRC",
  "synced_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "mode": "plaintext-full-test",
  "excluded": [
    "hermes-agent/",
    "logs/",
    "cache/",
    "audio_cache/",
    "__pycache__/",
    "*.pyc",
    "*.lock",
    "*.pid",
    "*.log",
    "*-wal",
    "*-shm",
    ".update_check"
  ]
}
EOF

cd "$REPO_ROOT"

git add README.md SECURITY.md .gitignore brain scripts skills docs

if git diff --cached --quiet; then
  echo "No changes to commit."
else
  msg="sync: update Hermes brain $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git commit -m "$msg"
  if git remote get-url origin >/dev/null 2>&1; then
    git push origin main
  else
    echo "No origin remote configured; committed locally only."
  fi
fi
