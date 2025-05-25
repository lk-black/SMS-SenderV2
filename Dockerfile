FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=sms_sender.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        curl \
        netcat-openbsd \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Copy and make all startup scripts executable
COPY wait_for_db.sh /app/
COPY start_web.sh /app/
COPY start_celery_worker.sh /app/
COPY start_celery_beat.sh /app/
COPY start_render.sh /app/
COPY validate_services.sh /app/
RUN chmod +x /app/wait_for_db.sh /app/start_web.sh /app/start_celery_worker.sh /app/start_celery_beat.sh /app/start_render.sh /app/validate_services.sh

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/webhooks/health/ || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command - run unified render script
CMD ["./start_render.sh"]
