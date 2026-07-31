# NovaCore Platform — bitta image: Mini App (statik) + FastAPI + aiogram + fon sikli
# Kontekst: repo ildizi (fly.toml: dockerfile = "backend/Dockerfile")

# --- 1) Mini App ---
FROM node:22-alpine AS miniapp
WORKDIR /build
COPY miniapp/package*.json ./
RUN npm ci --no-audit --no-fund
COPY miniapp/ ./
RUN npm run build

# --- 2) Backend ---
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=miniapp /build/dist ./miniapp_dist

RUN mkdir -p /app/var/media

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# Migratsiya → seed → ilova (bot ham shu process ichida)
# --proxy-headers: Fly proksisi ortida `X-Forwarded-Proto` hisobga olinadi,
# aks holda `/app` → `/app/` yo'naltirishi `http://` ga ketadi (Telegram bloklaydi)
CMD ["sh", "-c", "alembic upgrade head && python -m app.startup && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*"]
