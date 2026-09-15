#!/usr/bin/env bash
# Daily backup of data/ (SQLite + class registry + transcripts). Keeps the last 14.
# Schedule it with: crontab -e  ->  0 4 * * * /opt/knowly/deploy/backup.sh
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR=/opt/knowly-backups
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

# Consistent copy of the live SQLite database (safe while the app is running)
docker compose -f docker-compose.prod.yml exec -T backend python -c \
  "import sqlite3; s=sqlite3.connect('/app/data/knowly.db'); d=sqlite3.connect('/app/data/knowly.backup.db'); s.backup(d); d.close(); s.close()"

# Videos and audio are skipped: they can be downloaded again
tar -czf "$BACKUP_DIR/knowly-$STAMP.tar.gz" \
  --exclude='data/raw_videos' --exclude='data/audio' --exclude='data/frames' \
  --exclude='data/knowly.db' --exclude='data/knowly.db-wal' --exclude='data/knowly.db-shm' \
  data
rm -f data/knowly.backup.db

ls -1t "$BACKUP_DIR"/knowly-*.tar.gz | tail -n +15 | xargs -r rm --
echo "Backup: $BACKUP_DIR/knowly-$STAMP.tar.gz"
