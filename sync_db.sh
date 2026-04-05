#!/bin/bash
# sync_db.sh - Upload local listings.db to the deployed app
# Usage: ./sync_db.sh
#
# For Render: Use Render's persistent disk or upload via SCP
# For now: commit the DB to a private repo and Render pulls it on deploy

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Current DB stats:"
sqlite3 listings.db "SELECT COUNT(*) || ' total listings' FROM listings;"
sqlite3 listings.db "SELECT COUNT(*) || ' with rent' FROM listings WHERE rent IS NOT NULL;"
sqlite3 listings.db "SELECT COUNT(*) || ' with contact' FROM listings WHERE contact IS NOT NULL;"

echo ""
echo "To deploy:"
echo "  1. git add listings.db"
echo "  2. git commit -m 'Update listings DB'"
echo "  3. git push"
echo "  Render will auto-deploy on push."
