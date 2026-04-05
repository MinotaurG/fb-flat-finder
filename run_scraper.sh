#!/bin/bash
# run_scraper.sh - Run the scraper and log output
# Usage: ./run_scraper.sh
# Schedule with cron: crontab -e
#   0 8,20 * * * cd /Users/adishum/Developer/fb-flat-finder && ./run_scraper.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="scraper.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Starting scraper run" >> "$LOG_FILE"
python3 scraper.py >> "$LOG_FILE" 2>&1
echo "[$TIMESTAMP] Scraper run complete" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
