FROM python:3.12-slim

# Create non-root user early so pip cache is owned correctly
RUN addgroup --system rmias && adduser --system --ingroup rmias rmias

WORKDIR /app

# Install dependencies first (cache layer — only invalidated when pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && pip install --no-cache-dir ".[dev]"

# Copy application source
COPY app ./app

# Raw payload storage — mounted as a volume in production
RUN mkdir -p /data/raw_payloads && chown -R rmias:rmias /data

USER rmias

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
