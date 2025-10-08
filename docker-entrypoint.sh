#!/bin/bash

# Ensure the output directory exists and is writable
echo "Creating output directory..."
mkdir -p /config/kometa/tssk
chmod -R 755 /config/kometa/tssk
ls -la /config/kometa/ || echo "Warning: /config/kometa/ does not exist"

# Create cron job with explicit environment variables
echo "$CRON cd /app && DOCKER=true /usr/local/bin/python TSSK.py 2>&1 | tee -a /var/log/cron.log" > /etc/cron.d/tssk-cron
chmod 0644 /etc/cron.d/tssk-cron
crontab /etc/cron.d/tssk-cron
echo "TSSK is starting with the following cron schedule: $CRON"
touch /var/log/cron.log

# Run once on startup
echo "Running TSSK on startup..."
echo "Current directory: $(pwd)"
echo "DOCKER env var: $DOCKER"
cd /app && DOCKER=true /usr/local/bin/python TSSK.py 2>&1 | tee -a /var/log/cron.log

echo "Startup run completed. Starting cron daemon..."
cron
tail -f /var/log/cron.log