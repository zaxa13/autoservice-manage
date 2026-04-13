# Деплой tenant-приложения

## Два режима запуска

### 1. Локальная разработка (hot reload)

```bash
# из корня autoservice-management/
docker-compose up
```

- Backend монтируется из `./backend` — изменения применяются без перезапуска
- Frontend монтируется из `./frontend` — Vite dev server с HMR
- БД Postgres поднимается отдельным контейнером

Порты:
- `http://localhost:3000` — React frontend
- `http://localhost:8000` — FastAPI backend (swagger: `/docs`)
- `localhost:5432` — Postgres

---

### 2. Тест production-образа локально

```bash
docker-compose -f docker-compose.prod.yml up --build
# Открыть: http://localhost
# Логин: admin@example.com / admin123
```

Один контейнер, как в продакшне: nginx (port 80) → статика React + proxy `/api` → uvicorn:8000.
Используй перед тем как пушить образ в registry.

---

## Обновление образа в registry (деплой на платформу)

```bash
bash ~/autoservice-platform/infrastructure/scripts/deploy-tenant-image.sh ~/autoservice-management
```

Что происходит:
1. `docker build` из корневого `Dockerfile` (multi-stage: Node → nginx + Python → uvicorn)
2. `docker push` в локальный registry `localhost:5000`
3. Новые тенанты при провижининге получат актуальный образ

> **Существующие контейнеры НЕ перезапускаются автоматически.**
> Rolling update существующих тенантов — отдельный скрипт (`deploy-tenant-rolling.sh`), пока в беклоге.

---

## Жизненный цикл контейнера при старте

```
entrypoint.sh
  └── ждёт пока Postgres ответит (asyncpg probe)
  └── alembic upgrade head      # накатывает все миграции
  └── supervisord
        ├── uvicorn app.main:app --host 127.0.0.1 --port 8000
        └── nginx (port 80)

main.py lifespan (FastAPI startup):
  └── seed_system_categories()  # системные категории cashflow (идемпотентно)
  └── _seed_admin()             # если заданы ADMIN_EMAIL + ADMIN_PASSWORD (идемпотентно)
```

---

## Переменные окружения

Платформа подставляет эти переменные при провижининге тенанта:

| Переменная | Пример | Описание |
|---|---|---|
| `DATABASE_URL` | `postgresql://user:pass@db:5432/tenant_db` | Подключение к БД тенанта |
| `SECRET_KEY` | `<random 32 bytes hex>` | JWT секрет |
| `TENANT_SLUG` | `autoservice-volga` | Идентификатор тенанта |
| `TENANT_ID` | `uuid` | UUID тенанта в платформе |
| `PLAN` | `start` | Тарифный план |
| `ADMIN_EMAIL` | `owner@example.com` | Email владельца (создаётся при первом старте) |
| `ADMIN_PASSWORD` | `<strong password>` | Пароль владельца |
| `ENVIRONMENT` | `production` | Режим приложения |

Опциональные (для интеграций):
- `GIBDD_API_KEY`, `GIBDD_API_URL`

---

## Структура образа

```
Dockerfile (multi-stage)
  Stage 1: node:20-alpine
    └── npm ci && npm run build → /frontend/dist

  Stage 2: python:3.11-slim
    └── pip install requirements.txt
    └── COPY backend/
    └── COPY --from=stage1 /frontend/dist → /usr/share/nginx/html
    └── supervisord.conf + nginx.tenant.conf + entrypoint.sh
    └── CMD: /entrypoint.sh
```

nginx роутинг внутри контейнера:
```
port 80
  /api/*   → proxy http://127.0.0.1:8000
  /        → /usr/share/nginx/html (React SPA, fallback index.html)
```

---

## FAQ

**Нужно ли пересобирать образ при изменении env-переменных?**
Нет. Переменные передаются при запуске контейнера, не запекаются в образ.

**Что если alembic упадёт при старте?**
`entrypoint.sh` использует `set -e` — контейнер завершится с ошибкой, оркестратор перезапустит его. БД не будет инициализирована до тех пор пока миграции не пройдут успешно.

**Как добавить новую миграцию?**
```bash
# локально, в режиме dev:
docker-compose exec backend alembic revision --autogenerate -m "add_column_x"
```
При следующем деплое `alembic upgrade head` применит её автоматически.
