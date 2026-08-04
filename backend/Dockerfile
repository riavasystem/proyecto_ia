FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLUGINS_DIR=/app/plugins

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# El build context es la raíz del repo (no backend/), para poder copiar
# también /plugins — ver .github/workflows/deploy-backend.yml.
COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache -e .

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY plugins ./plugins

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/public/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
