#!/bin/bash
set -e

# Cron schedule (default 2AM)
CRON_SCHEDULE="${CRON:-0 2 * * *}"

# Run immediately if RUN_NOW=true
if [ "$RUN_NOW" = "true" ]; then
    echo "[INFO] RUN_NOW flag detected. Running TSSK.py immediately..."
    cd /app
    DOCKER=true /usr/local/bin/python /app/TSSK.py 2>&1 | tee -a /var/log/cron.log
fi

# Create cron job
echo "$CRON_SCHEDULE root cd /app && DOCKER=true /usr/local/bin/python /app/TSSK.py >> /var/log/cron.log 2>&1" > /etc/cron.d/tssk-cron
chmod 0644 /etc/cron.d/tssk-cron
crontab /etc/cron.d/tssk-cron

echo "[INFO] TSSK will also run according to cron schedule: $CRON_SCHEDULE"

# Ensure log file exists
touch /var/log/cron.log

# Start dcron in foreground to keep container alive
crond -f -l 2
