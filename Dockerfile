FROM python:3.12-slim AS production

# Create non-root user early
RUN addgroup --system rmias && adduser --system --ingroup rmias rmias

WORKDIR /app

# Copy package metadata and application code before installing the package.
# pyproject.toml references README.md and packages = ["app"], so these must exist at install time.
COPY pyproject.toml README.md ./
COPY app ./app

# Copy migration files so `alembic upgrade head` works inside the app container.
COPY alembic.ini ./
COPY migrations ./migrations

# Install runtime dependencies only.
RUN pip install --no-cache-dir .

# Raw payload storage — mounted as a volume in production.
RUN mkdir -p /data/raw_payloads && chown -R rmias:rmias /data

USER rmias

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
