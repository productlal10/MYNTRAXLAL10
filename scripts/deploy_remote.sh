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
ExecStart=${VENV_DIR}/bin/gunicorn --workers 1 --threads 4 --worker-class gthread --bind 127.0.0.1:${PORT} --timeout 120 server:app
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

echo "[6/6] Starting background analytics rebuild..."
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
