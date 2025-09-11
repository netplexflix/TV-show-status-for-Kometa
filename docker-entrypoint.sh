#!/bin/bash
set -e

# Ensure CRON is set; default to 2AM if not
CRON_SCHEDULE="${CRON:-0 2 * * *}"

# If RUN_NOW is set, run the script immediately
if [ "$RUN_NOW" = "true" ]; then
    echo "[INFO] RUN_NOW flag detected. Running TSSK.py immediately..."
    cd /app
    DOCKER=true /usr/local/bin/python /app/TSSK.py 2>&1 | tee -a /var/log/cron.log
fi

# Write cron job for scheduled runs
echo "$CRON_SCHEDULE root cd /app && DOCKER=true /usr/local/bin/python /app/TSSK.py >> /var/log/cron.log 2>&1" > /etc/cron.d/tssk-cron

# Set permissions and install cron job
chmod 0644 /etc/cron.d/tssk-cron
crontab /etc/cron.d/tssk-cron

echo "[INFO] TSSK will also run according to cron schedule: $CRON_SCHEDULE"

# Ensure log file exists
touch /var/log/cron.log

# Start cron in foreground to keep container alive
cron -f
