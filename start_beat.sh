#!/usr/bin/env bash
# Beat startup script with health checks
set -o errexit

echo "Starting Celery beat with health checks..."

# Wait for Redis to be available
echo "Checking Redis connection..."
python -c "
import os
import redis
import time
import sys
from decouple import config

redis_url = config('REDIS_URL', default='redis://localhost:6379/0')
max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print('Redis connection successful!')
        break
    except Exception as e:
        retry_count += 1
        print(f'Redis connection attempt {retry_count}/{max_retries} failed: {e}')
        if retry_count >= max_retries:
            print('Failed to connect to Redis after maximum retries')
            sys.exit(1)
        time.sleep(2)
"

# Wait for database to be available
echo "Checking database connection..."
python manage.py check --database default

echo "Starting Celery beat..."
celery -A sms_sender beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
