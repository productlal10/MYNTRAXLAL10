#!/usr/bin/env bash
# ==============================================================================
# Cloud Setup & 24/7 Daemon Deployment Script for Myntra Scraper & UI
# Works on Ubuntu / Debian / Amazon Linux EC2
# ==============================================================================

set -e

echo "=== 1. Updating system packages & installing Python3-pip ==="
if command -v apt-get &>/dev/null; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python3 python3-pip python3-venv
elif command -v yum &>/dev/null; then
    sudo yum update -y
    sudo yum install -y python3 python3-pip
fi

echo "=== 2. Setting up Python Virtual Environment ==="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "=== 3. Installing Python Dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 4. Ensuring Data & Logs Directories ==="
mkdir -p data logs

echo "=== 5. Starting Web Dashboard Server on port 5050 ==="
pkill -f "python3 server.py" || true
nohup python3 server.py > logs/server.log 2>&1 &
sleep 2
echo "[✓] Web Dashboard running on http://$(curl -s ifconfig.me 2>/dev/null || echo '<YOUR_EC2_IP>'):5050"

echo "=== 6. Preparing Manual Daily Scraper Script ==="
cat << 'EOF' > run_daily_scrape.sh
#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate
mkdir -p logs data
echo "Starting Myntra Daily Scrape for Shirts & Denims across all brands..."
python3 main.py --workers 8 --categories shirts,denims --brand-type all >> logs/scraper_daily.log 2>&1 &
echo "[✓] Scraper launched in background (PID: $!)."
echo "[✓] Follow live progress with: tail -f logs/scraper_daily.log"
EOF
chmod +x run_daily_scrape.sh

echo "=== Setup complete! ==="
echo "To trigger the scraper manually at any time, run: ./run_daily_scrape.sh"
echo "Or click 'Start Crawl' directly from the Web UI at http://<YOUR_EC2_IP>:5050"
