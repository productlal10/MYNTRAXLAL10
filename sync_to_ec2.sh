#!/usr/bin/env bash
# ==============================================================================
# sync_to_ec2.sh
# Lightweight manual deploy that mirrors the GitHub Actions production flow.
# - sync code
# - upload .env
# - restart app quickly
# - rebuild DuckDB analytics in the background
# ==============================================================================

set -euo pipefail

EC2_IP="${EC2_IP:-13.203.86.141}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$HOME/Downloads/myntralal10.pem}"
REMOTE_DIR="${REMOTE_DIR:-/var/www/myntra_database}"
APP_USER="${APP_USER:-$EC2_USER}"
APP_PORT="${APP_PORT:-5050}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$PEM_KEY" ]; then
  echo "SSH key not found: $PEM_KEY"
  exit 1
fi

chmod 400 "$PEM_KEY"

echo ""
echo "======================================================="
echo "  EC2 DEPLOY"
echo "  Target : $EC2_USER@$EC2_IP"
echo "  App Dir: $REMOTE_DIR"
echo "======================================================="

echo ""
echo "[1/4] Testing SSH connection..."
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "echo Connected"

echo ""
echo "[2/4] Syncing code..."
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "mkdir -p '$REMOTE_DIR'"
rsync -az --delete \
  -e "ssh -i $PEM_KEY -o StrictHostKeyChecking=no" \
  --exclude ".git" \
  --exclude ".github" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude "*.pyo" \
  --exclude "venv" \
  --exclude ".env" \
  --exclude "logs/*" \
  --exclude "data/*.duckdb" \
  --exclude "data/*.duckdb.wal" \
  --exclude "*.db" \
  "$LOCAL_DIR/" "$EC2_USER@$EC2_IP:$REMOTE_DIR/"

echo ""
echo "[3/4] Uploading .env..."
if [ ! -f "$LOCAL_DIR/.env" ]; then
  echo "Local .env not found at $LOCAL_DIR/.env"
  exit 1
fi
cat "$LOCAL_DIR/.env" | ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "cat > '$REMOTE_DIR/.env'"

echo ""
echo "[4/4] Running remote deploy..."
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "\
  cd '$REMOTE_DIR' && \
  chmod +x scripts/deploy_remote.sh scripts/rebuild_analytics.sh && \
  APP_DIR='$REMOTE_DIR' \
  APP_USER='$APP_USER' \
  PORT='$APP_PORT' \
  SERVICE_NAME='myntra_dashboard' \
  bash scripts/deploy_remote.sh"

echo ""
echo "======================================================="
echo "  DEPLOY REQUESTED"
echo "  App URL       : http://$EC2_IP:$APP_PORT"
echo "  Health URL    : http://$EC2_IP:$APP_PORT/api/health"
echo "  Remote status : $REMOTE_DIR/tmp/analytics_rebuild_status.json"
echo "  Remote log    : $REMOTE_DIR/logs/analytics_rebuild.log"
echo "======================================================="
