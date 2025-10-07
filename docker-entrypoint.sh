#!/bin/bash

echo "$CRON cd /app && DOCKER=true /usr/local/bin/python TSSK.py 2>&1 | tee -a /var/log/cron.log" > /etc/cron.d/tssk-cron
chmod 0644 /etc/cron.d/tssk-cron
crontab /etc/cron.d/tssk-cron
echo "TSSK is starting with the following cron schedule: $CRON"
touch /var/log/cron.log

# Run once on startup
echo "Running TSSK on startup..."
cd /app && DOCKER=true /usr/local/bin/python TSSK.py 2>&1 | tee -a /var/log/cron.log

cron
tail -f /var/log/cron.log