# Algorithmic Trading Platform v2.0 - Complete End-to-End System
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create comprehensive directory structure
RUN mkdir -p \
    /app/artifacts/screener \
    /app/artifacts/analyzer \
    /app/artifacts/strategy \
    /app/artifacts/execution \
    /app/artifacts/backtests \
    /app/artifacts/pipeline_runs \
    /app/logs \
    /app/cache \
    /app/data/historical

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TRADING_ENVIRONMENT=docker
ENV ARTIFACTS_PATH=/app/artifacts
ENV CACHE_PATH=/app/cache
ENV LOG_LEVEL=INFO

# Expose ports
EXPOSE 8501
EXPOSE 8000
EXPOSE 8080

# Health check for complete system
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create non-root user for security
RUN groupadd -r trader && useradd -r -g trader trader
RUN chown -R trader:trader /app
USER trader

# Default command launches advanced platform
CMD ["python", "launch_advanced.py"]
