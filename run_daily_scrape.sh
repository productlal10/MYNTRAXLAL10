#!/usr/bin/env bash
# ==============================================================================
# Daily Automated Crawler & Sales/Revenue Intelligence Snapshot Runner
# ==============================================================================

set -e
cd "$(dirname "$0")"

# Ensure logs directory exists
mkdir -p logs

LOG_FILE="logs/cron_daily_$(date +%Y%m%d).log"
echo "=======================================================" >> "$LOG_FILE"
echo "[$(date)] Starting Daily Crawl for Shirts, Denims, and Western Wear..." >> "$LOG_FILE"

# Activate Python virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "/home/ubuntu/myntra-database/venv" ]; then
    source /home/ubuntu/myntra-database/venv/bin/activate
fi

# Run the multi-category crawler with optimal workers
echo "[$(date)] Executing main scraper engine..." >> "$LOG_FILE"
python3 main.py --categories shirts,denims,western-wear --workers 6 >> "$LOG_FILE" 2>&1 || true

# Compute daily inventory deltas, sales units, GMV revenue & Rate of Sale (ROS)
echo "[$(date)] Computing daily inventory deltas & taking analytics snapshot..." >> "$LOG_FILE"
python3 -c "
from database import Database
import datetime
db = Database()
res = db.take_daily_snapshot()
print(f'[SUCCESS] Snapshot computed: {res}')
" >> "$LOG_FILE" 2>&1

echo "[$(date)] Daily Intelligence Run Complete!" >> "$LOG_FILE"
echo "=======================================================" >> "$LOG_FILE"
