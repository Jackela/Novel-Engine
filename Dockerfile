# Novel Engine Production Dockerfile
# Multi-stage build for optimized production deployment
# Security-hardened and optimized for container environments

# Build stage - larger image with development tools
FROM python:3.11-slim-bullseye as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip wheel setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Production stage - minimal runtime image
FROM python:3.11-slim-bullseye as production

# Create non-root user for security
RUN groupadd -r novel && useradd -r -g novel novel

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=novel:novel . .

# Create necessary directories for runtime
RUN mkdir -p /app/staging/logs \
    /app/staging/private \
    /app/staging/private/knowledge_base \
    /app/staging/private/sessions \
    /app/staging/evaluation \
    /app/staging/exports \
    /app/data \
    /app/logs && \
    chown -R novel:novel /app

# Security hardening
RUN chmod -R 750 /app && \
    chmod -R 640 /app/*.py && \
    chmod 750 /app/api_server.py /app/production_api_server.py

# Switch to non-root user
USER novel

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment configuration
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NOVEL_ENGINE_ENV=production \
    PORT=8000

# Expose port
EXPOSE 8000

# Default command - production API server
CMD ["python", "production_api_server.py"]

# Alternative commands for different deployments:
# Development: CMD ["python", "api_server.py"]
# Testing: CMD ["python", "-m", "pytest", "tests/"]