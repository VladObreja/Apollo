#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$ROOT/legacy/Backups"
STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
VERSION="${1:-v1}"

FILES=(
  "docker-compose.yaml"
  "apollo_up.bat"
  "apollo_down.bat"
  ".env"
  "AGENTS.md"
)

mkdir -p "$BACKUP_DIR"

for f in "${FILES[@]}"; do
  if [[ -f "$ROOT/$f" ]]; then
    cp "$ROOT/$f" "$BACKUP_DIR/${f}.${VERSION}.${STAMP}.bak"
    echo "Backed up: $f -> legacy/Backups/${f}.${VERSION}.${STAMP}.bak"
  fi
done
