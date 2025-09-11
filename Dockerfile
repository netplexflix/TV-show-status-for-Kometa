# Use Alpine-based Python image for small size
FROM python:3.11-alpine

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CRON="0 2 * * *"

# Set working directory
WORKDIR /app

# Install bash, cron, tzdata, and build dependencies
RUN apk add --no-cache \
        bash \
        tzdata \
        dcron \
        build-base \
        musl-dev \
        libffi-dev \
        python3-dev \
        py3-pip

# Copy dependencies first (to leverage caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint and make executable
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose log volume (optional)
VOLUME ["/var/log"]

# Start container with entrypoint
ENTRYPOINT ["/entrypoint.sh"]
