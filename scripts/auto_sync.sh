#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

LOCK_FILE="${HERMES_BRAIN_LOCK_FILE:-/tmp/hermes-brain-auto-sync.lock}"
LOG_DIR="${HERMES_BRAIN_LOG_DIR:-$HOME/.local/state/hermes-brain}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/auto-sync.log"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date -Is) another hermes-brain auto sync is already running" | tee -a "$LOG_FILE"
  exit 0
fi

{
  echo "== $(date -Is) hermes-brain auto sync start =="
  echo "repo=$REPO_ROOT"
  echo "hostname=$(hostname)"

  if [ "${HERMES_BRAIN_NO_JITTER:-0}" != "1" ]; then
    JITTER_MAX="${HERMES_BRAIN_JITTER_MAX:-300}"
    if [ "$JITTER_MAX" -gt 0 ] 2>/dev/null; then
      DELAY=$((RANDOM % (JITTER_MAX + 1)))
      echo "jitter_sleep_seconds=$DELAY"
      sleep "$DELAY"
    fi
  fi

  if git remote get-url origin >/dev/null 2>&1; then
    echo "+ git fetch origin"
    git fetch origin || true
    echo "+ git pull --ff-only"
    git pull --ff-only || {
      echo "ERROR: git pull --ff-only failed; not syncing"
      exit 1
    }
  else
    echo "WARN: no git origin remote configured"
  fi

  ROLE_OUTPUT="$(python3 scripts/hermes_brain_role.py status)"
  echo "$ROLE_OUTPUT"
  EFFECTIVE_ROLE="$(printf '%s\n' "$ROLE_OUTPUT" | awk -F= '/^effective_role=/{print $2}' | tail -1)"

  if [ "$EFFECTIVE_ROLE" = "push" ]; then
    echo "mode=push: local Hermes -> repo -> GitHub"
    
    # Backup state.db before sync (compress to fit GitHub 100MB limit)
    echo "+ Backing up state.db..."
    ./scripts/state_db_backup.sh backup
    
    ./scripts/sync_from_local_to_repo.sh --git --push -m "sync: auto update Hermes brain from $(hostname)"
  else
    echo "mode=pull: GitHub -> repo -> local Hermes"
    # If this machine used to think it was push but no longer owns the global owner, downgrade local role.
    python3 scripts/hermes_brain_role.py downgrade-if-needed || true
    ./scripts/sync_from_repo_to_local.sh --pull --skip-if-same
    
    # Restore state.db if needed
    RESTORE_CHECK=$(./scripts/state_db_backup.sh check || echo "")
    if [ "$RESTORE_CHECK" = "RESTORE_NEEDED" ]; then
      echo "+ Restoring state.db..."
      ./scripts/state_db_backup.sh restore
    fi
  fi

  echo "== $(date -Is) hermes-brain auto sync success =="
} 2>&1 | tee -a "$LOG_FILE"
