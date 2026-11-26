# Stage 1: Dependencies builder
FROM python:3.14-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.14-slim

# Non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Create required directories with proper ownership
RUN mkdir -p /app /data /app/logs && chown -R appuser:appuser /app /data /app/logs

# Copy dependencies from builder
COPY --from=builder --chown=appuser:appuser /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder --chown=appuser:appuser /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser requirements.txt setup.py ./
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser alembic.ini ./

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --access-log"]
