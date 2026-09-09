FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory
WORKDIR /app

# Install minimal system dependencies for Pillow, healthcheck, and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Install Python dependencies first (leveraging Docker layer caching)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source code with proper ownership
COPY --chown=appuser:appuser . /app/

# Ensure media and staticfiles directories exist and are owned by appuser
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R appuser:appuser /app/media /app/staticfiles

# Collect static files with a build-time fallback key
RUN SECRET_KEY="docker-build-static-collection-key" python manage.py collectstatic --noinput

# Switch to non-root user for security
USER appuser

# Expose web service port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default startup command running Gunicorn WSGI server
CMD ["gunicorn", "nit_home.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
