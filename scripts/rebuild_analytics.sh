#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/myntra_database}"
SERVICE_NAME="${SERVICE_NAME:-myntra_dashboard}"
STATUS_FILE="${STATUS_FILE:-$APP_DIR/tmp/analytics_rebuild_status.json}"
PID_FILE="${PID_FILE:-$APP_DIR/tmp/analytics_rebuild.pid}"
LOG_FILE="${LOG_FILE:-$APP_DIR/logs/analytics_rebuild.log}"
PYTHON_BIN="${PYTHON_BIN:-$APP_DIR/venv/bin/python3}"

mkdir -p "$(dirname "$STATUS_FILE")" "$(dirname "$LOG_FILE")"

write_status() {
  local status="$1"
  local detail="$2"
  cat > "$STATUS_FILE" <<EOF
{
  "status": "$status",
  "detail": "$detail",
  "pid": $$,
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "log_file": "$LOG_FILE"
}
EOF
}

if [ -f "$PID_FILE" ]; then
  existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${existing_pid:-}" ] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "Analytics rebuild already running with PID $existing_pid"
    exit 0
  fi
fi

echo $$ > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

write_status "running" "DuckDB analytics rebuild started"

cd "$APP_DIR"

if "$PYTHON_BIN" build_duckdb.py >> "$LOG_FILE" 2>&1; then
  write_status "restarting-service" "DuckDB rebuild complete; restarting app service"
  sudo systemctl restart "$SERVICE_NAME"
  write_status "ready" "DuckDB rebuild complete and app service restarted"
else
  write_status "failed" "DuckDB rebuild failed; check rebuild log"
  exit 1
fi
