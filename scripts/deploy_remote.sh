#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/myntra_database}"
APP_USER="${APP_USER:-ubuntu}"
SERVICE_NAME="${SERVICE_NAME:-myntra_dashboard}"
PORT="${PORT:-5050}"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
TMP_DIR="$APP_DIR/tmp"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
CPU_COUNT="$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 2)"
DEFAULT_GUNICORN_WORKERS="$((CPU_COUNT + 1))"
if [ "$DEFAULT_GUNICORN_WORKERS" -gt 4 ]; then
  DEFAULT_GUNICORN_WORKERS=4
fi
GUNICORN_WORKERS="${GUNICORN_WORKERS:-$DEFAULT_GUNICORN_WORKERS}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"
if [ "$GUNICORN_WORKERS" -lt 2 ]; then
  GUNICORN_WORKERS=2
fi

mkdir -p "$APP_DIR" "$APP_DIR/data" "$LOG_DIR" "$TMP_DIR"

echo "[1/6] Installing system packages..."
if command -v apt-get >/dev/null 2>&1; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 python3-pip python3-venv rsync curl postgresql postgresql-contrib
elif command -v yum >/dev/null 2>&1; then
  sudo yum install -y python3 python3-pip rsync curl postgresql
fi

echo "[2/6] Preparing PostgreSQL and virtualenv..."
sudo systemctl enable postgresql >/dev/null 2>&1 || true
sudo systemctl start postgresql >/dev/null 2>&1 || true

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" >/dev/null

echo "[3/6] Cleaning transient artifacts..."
find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$APP_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
rm -rf "$APP_DIR/.pytest_cache" "$APP_DIR/.mypy_cache"

echo "[4/6] Installing systemd service..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=Myntra Dashboard WSGI Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=PYTHONUNBUFFERED=1
Environment=SKIP_PREWARM=1
Environment=SKIP_DB_INIT=1
ExecStart=${VENV_DIR}/bin/gunicorn --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --worker-class gthread --bind 127.0.0.1:${PORT} --timeout 120 --keep-alive 5 --worker-tmp-dir /dev/shm server:app
Restart=always
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME" >/dev/null

echo "[5/6] Restarting live app..."
sudo systemctl restart "$SERVICE_NAME"

for _ in $(seq 1 20); do
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)"
  if [ "$HTTP_CODE" = "200" ]; then
    echo "  Health check passed with HTTP 200"
    break
  fi
  sleep 2
done

HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)"
if [ "$HTTP_CODE" != "200" ]; then
  echo "Health check failed with HTTP $HTTP_CODE"
  exit 1
fi

echo "[6/7] Priming shared API cache..."
if ! APP_DIR="$APP_DIR" SKIP_PREWARM=1 SKIP_DB_INIT=1 "$VENV_DIR/bin/python3" - <<'PY'
import os
import time
import urllib.request
import server

base = f"http://127.0.0.1:{os.environ.get('PORT', '5050')}"
token = server.create_session_token("deploy-warmup@local")
headers = {"Authorization": f"Bearer {token}"}
paths = [
    "/api/stats?sort_by=valuation_desc",
    "/api/insights?sort_by=valuation_desc",
    "/api/insights/facets",
    "/api/snapshot-dates",
    "/api/catalog/meta?category=shirts&gender=men",
    "/api/filter-counts?category=shirts&gender=men",
    "/api/products?page=1&per_page=20&sort=relevance&view_mode=grid&category=shirts&gender=men",
    "/api/brands-intelligence?category=shirts&gender=men",
]

for path in paths:
    started = time.time()
    req = urllib.request.Request(base + path, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as resp:
        resp.read()
        print(f"  Warmed {path} in {time.time() - started:.2f}s")
PY
then
  echo "  Shared cache warmup failed; continuing with deploy."
fi

echo "[7/7] Starting background analytics rebuild..."
nohup env \
  APP_DIR="$APP_DIR" \
  SERVICE_NAME="$SERVICE_NAME" \
  PYTHON_BIN="$VENV_DIR/bin/python3" \
  STATUS_FILE="$TMP_DIR/analytics_rebuild_status.json" \
  PID_FILE="$TMP_DIR/analytics_rebuild.pid" \
  LOG_FILE="$LOG_DIR/analytics_rebuild.log" \
  bash "$APP_DIR/scripts/rebuild_analytics.sh" >/dev/null 2>&1 &

echo ""
echo "Deploy complete."
echo "App health    : $HEALTH_URL"
echo "Rebuild status: $TMP_DIR/analytics_rebuild_status.json"
echo "Rebuild log   : $LOG_DIR/analytics_rebuild.log"
