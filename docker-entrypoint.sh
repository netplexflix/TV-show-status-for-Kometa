#!/bin/bash
set -e

CRON_SCHEDULE="${CRON:-0 2 * * *}"

if [ "$RUN_NOW" = "true" ]; then
    echo "[INFO] RUN_NOW flag detected. Running TSSK.py immediately..."
    cd /app
    DOCKER=true /usr/local/bin/python /app/TSSK.py 2>&1 | tee -a /var/log/cron.log
fi

echo "$CRON_SCHEDULE root cd /app && DOCKER=true /usr/local/bin/python /app/TSSK.py >> /var/log/cron.log 2>&1" > /etc/cron.d/tssk-cron

chmod 0644 /etc/cron.d/tssk-cron
crontab /etc/cron.d/tssk-cron

echo "[INFO] TSSK will also run according to cron schedule: $CRON_SCHEDULE"

touch /var/log/cron.log

# Start dcron in foreground
crond -f -l 2
