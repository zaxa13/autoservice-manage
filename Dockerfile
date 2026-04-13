# =============================================================================
# autoservice-tenant — production image
# Содержит: React frontend (nginx) + FastAPI backend (uvicorn)
# Порт: 80 (nginx → /api → uvicorn:8000)
# =============================================================================

# --- Stage 1: сборка React фронтенда ---
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# --- Stage 2: production образ ---
FROM python:3.11-slim

# Системные зависимости: nginx, supervisord, asyncpg нативный драйвер
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend зависимости
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Backend код
COPY backend/ ./backend/

# Frontend — собранный статик из Stage 1
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html

# Конфиги
COPY nginx.tenant.conf /etc/nginx/sites-available/default
COPY supervisord.conf /app/supervisord.conf
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Alembic должен запускаться из директории backend
WORKDIR /app/backend

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
