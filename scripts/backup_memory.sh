#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEMORY_FILE="$ROOT/MEMORY.md"
BACKUP_DIR="$ROOT/memory/backups"
LATEST_BACKUP="$BACKUP_DIR/MEMORY.latest.md"
STAMP="$(date -u +%F)"

if [[ ! -f "$MEMORY_FILE" ]]; then
  if [[ -f "$LATEST_BACKUP" ]]; then
    cp "$LATEST_BACKUP" "$MEMORY_FILE"
    echo "Restored missing MEMORY.md from: $LATEST_BACKUP"
  else
    echo "MEMORY.md not found at: $MEMORY_FILE" >&2
    exit 1
  fi
fi

mkdir -p "$BACKUP_DIR"
cp "$MEMORY_FILE" "$BACKUP_DIR/MEMORY.latest.md"
cp "$MEMORY_FILE" "$BACKUP_DIR/MEMORY-$STAMP.md"

echo "Backed up MEMORY.md to:"
echo "- $BACKUP_DIR/MEMORY.latest.md"
echo "- $BACKUP_DIR/MEMORY-$STAMP.md"
