#!/usr/bin/env bash
# State DB Backup/Restore Helper
# Compresses state.db for GitHub storage and decompresses on restore

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DB="${REPO_ROOT}/brain/hermes-home/state.db"
STATE_DB_COMPRESSED="${REPO_ROOT}/brain/hermes-home/state.db.tar.gz"

case "${1:-}" in
  backup)
    # Compress state.db for GitHub
    if [ -f "$STATE_DB" ]; then
      echo "📦 Compressing state.db..."
      tar -czf "$STATE_DB_COMPRESSED" -C "$(dirname "$STATE_DB")" state.db
      COMPRESSED_SIZE=$(du -h "$STATE_DB_COMPRESSED" | cut -f1)
      ORIGINAL_SIZE=$(du -h "$STATE_DB" | cut -f1)
      echo "✅ Backup complete: $ORIGINAL_SIZE → $COMPRESSED_SIZE"
      echo "   File: $STATE_DB_COMPRESSED"
      
      # Remove original to avoid committing both
      rm -f "$STATE_DB"
      echo "✅ Original state.db removed"
    else
      echo "⚠️  state.db not found, skipping backup"
    fi
    ;;
  
  restore)
    # Decompress state.db from archive
    if [ -f "$STATE_DB_COMPRESSED" ]; then
      echo "📦 Restoring state.db from archive..."
      tar -xzf "$STATE_DB_COMPRESSED" -C "$(dirname "$STATE_DB")"
      SIZE=$(du -h "$STATE_DB" | cut -f1)
      echo "✅ Restore complete: $STATE_DB ($SIZE)"
    elif [ ! -f "$STATE_DB" ]; then
      echo "⚠️  Neither state.db nor state.db.tar.gz found"
      exit 1
    else
      echo "✅ state.db already exists, no restore needed"
    fi
    ;;
  
  check)
    # Check if restore is needed
    if [ ! -f "$STATE_DB" ] && [ -f "$STATE_DB_COMPRESSED" ]; then
      echo "RESTORE_NEEDED"
      exit 0
    fi
    echo "OK"
    exit 0
    ;;
  
  *)
    echo "Usage: $0 {backup|restore|check}"
    exit 1
    ;;
esac
