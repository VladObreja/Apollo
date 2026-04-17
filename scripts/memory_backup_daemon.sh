#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$ROOT/memory/backups"
PIDFILE="$BACKUP_DIR/memory-backup-daemon.pid"
LOGFILE="$BACKUP_DIR/memory-backup-daemon.log"
INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-600}"
BACKUP_SCRIPT="$ROOT/scripts/backup_memory.sh"

mkdir -p "$BACKUP_DIR"

is_running() {
  if [[ -f "$PIDFILE" ]]; then
    local pid
    pid="$(cat "$PIDFILE")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start() {
  if is_running; then
    echo "memory backup daemon already running (pid $(cat "$PIDFILE"))"
    return 0
  fi

  nohup "$0" run >> "$LOGFILE" 2>&1 &
  local pid=$!
  echo "$pid" > "$PIDFILE"
  echo "started memory backup daemon (pid $pid)"
}

run_loop() {
  echo "[$(date -u +%FT%TZ)] memory backup daemon starting (interval=${INTERVAL_SECONDS}s)"
  while true; do
    echo "[$(date -u +%FT%TZ)] running MEMORY.md backup"
    if ! "$BACKUP_SCRIPT"; then
      echo "[$(date -u +%FT%TZ)] backup failed"
    fi
    sleep "$INTERVAL_SECONDS"
  done
}

stop() {
  if ! is_running; then
    echo "memory backup daemon is not running"
    rm -f "$PIDFILE"
    return 0
  fi

  local pid
  pid="$(cat "$PIDFILE")"
  kill "$pid"
  rm -f "$PIDFILE"
  echo "stopped memory backup daemon (pid $pid)"
}

status() {
  if is_running; then
    echo "running $(cat "$PIDFILE")"
  else
    echo "stopped"
    return 1
  fi
}

case "${1:-}" in
  start)
    start
    ;;
  run)
    run_loop
    ;;
  stop)
    stop
    ;;
  restart)
    stop || true
    start
    ;;
  status)
    status
    ;;
  *)
    echo "Usage: $0 {start|run|stop|restart|status}" >&2
    exit 1
    ;;
esac
