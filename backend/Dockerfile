# NovaCore Platform — bitta image: FastAPI + aiogram + fon sikli
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/var/media

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# Migratsiya → so'ng ilova (bot ham shu process ichida)
CMD ["sh", "-c", "alembic upgrade head && python -m app.startup && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
