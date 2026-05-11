# Phase 7 — cutover на shared-DB

После этой фазы:
- `auto-works.pro` — лендинг (platform-frontend) — **без изменений**.
- `api.auto-works.pro` — platform-api (`:8001`) — **без изменений**, только
  применить новую миграцию `f5a6b7c8d9e0_drop_slug_from_tenants`.
- `app.auto-works.pro` — **новое** tenant-app (`:8002`), один процесс
  на всех тенантов, RLS-изоляция.
- `{slug}.auto-works.pro` — **выключены**, 410 Gone или 301 на
  `app.auto-works.pro` (на выбор).

## Подготовка на сервере

### 0. Shared-DB sandbox уже поднят
Поднят в Phase 1 (`autoworks-postgres`, `autoworks-pgbouncer`,
network `sharedb-test_default`). Если нет — поднять из
`autoservice-platform/docker-compose.shared-db.yml`.

### 1. Запустить tenant-app

```bash
cd ~/autoservice-manage
git checkout new-architecture && git pull
cp .env.app.example .env.app
$EDITOR .env.app   # заполнить пароли БД + SECRET_KEY (общий с platform-api!)
docker compose -f docker-compose.app.yml --env-file .env.app up -d --build
```

Проверка:
```bash
docker logs autoworks-tenant-app 2>&1 | tail -20
# Должно быть:
# [entrypoint] Running alembic upgrade head…
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# (миграции применяются; на чистой БД это 0001_shared_db_initial)
# [entrypoint] Starting application: uvicorn …
# INFO:     Application startup complete.

curl http://127.0.0.1:8002/health
# {"status":"ok"}
```

### 2. Применить миграцию platform-api (drop slug)

```bash
cd ~/autoservice-platform/autoservice-platform
git checkout new-architecture && git pull
# Перебилдить platform-api с новым кодом
docker compose -f docker-compose.platform.yml up -d --build platform-api platform-worker platform-beat
# Alembic в platform-api запускается при старте или вручную:
docker exec autoservice-platform-platform-api-1 alembic upgrade head
```

### 3. Перенастроить nginx

```bash
sudo cp ~/autoservice-manage/infrastructure/nginx/app.auto-works.pro.conf \
        /etc/nginx/sites-available/

# Удалить старый блок `server_name app.auto-works.pro` из
# /etc/nginx/sites-enabled/auto-works.pro (там сейчас proxy_pass :3000).
sudo $EDITOR /etc/nginx/sites-enabled/auto-works.pro
# Удалить:
#   server { listen 443 ... server_name app.auto-works.pro;
#            proxy_pass http://127.0.0.1:3000; ... }
# HTTP redirect блок для app.auto-works.pro тоже удалить (он
# дублируется в новом конфиге).

sudo ln -sf /etc/nginx/sites-available/app.auto-works.pro.conf \
            /etc/nginx/sites-enabled/

sudo nginx -t
sudo systemctl reload nginx
```

Проверка:
```bash
curl -I https://app.auto-works.pro/health
# HTTP/2 200
```

### 4. Выключить старые per-tenant контейнеры

```bash
# Снимать без -v (volumes сохранятся для аудита, можно удалить позже).
docker stop tenant-stoloto tenant-pelmen tenant-roga 2>/dev/null
docker rm   tenant-stoloto tenant-pelmen tenant-roga 2>/dev/null

# Выключить Traefik + private registry (не нужны без tenant контейнеров).
cd ~/autoservice-platform/autoservice-platform
docker compose -f docker-compose.platform.yml rm -sf traefik registry 2>/dev/null
# (traefik/registry уже вычеркнуты из compose в Phase 4c —
# просто удалить остатки контейнеров на сервере.)
```

### 5. Старые *.auto-works.pro

В nginx конфиге сейчас есть catch-all:
```
server_name ~^(?<tenant>(?!api$)(?!app$)[a-z0-9-]+)\.auto-works\.pro$;
proxy_pass http://127.0.0.1:8080;  # Traefik (выключен)
```

Два варианта:
1. **301 redirect** на `app.auto-works.pro` (мягкий cutover):
   ```nginx
   server {
       listen 443 ssl http2;
       server_name ~^[a-z0-9-]+\.auto-works\.pro$;
       ssl_certificate /etc/letsencrypt/live/auto-works.pro-0001/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/auto-works.pro-0001/privkey.pem;
       return 301 https://app.auto-works.pro$request_uri;
   }
   ```

2. **Удалить блок** — поддомены вернут SSL error / NXDOMAIN
   (если wildcard SSL снят).

Рекомендую вариант 1 на месяц — мягко, никто не теряется.

## Rollback

Если что-то пошло не так:
```bash
# 1. Вернуть nginx app.auto-works.pro → :3000:
sudo rm /etc/nginx/sites-enabled/app.auto-works.pro.conf
sudo $EDITOR /etc/nginx/sites-enabled/auto-works.pro  # вернуть старый блок
sudo nginx -t && sudo systemctl reload nginx

# 2. Откатить platform-api:
cd ~/autoservice-platform/autoservice-platform
git checkout yookassa_integrate  # legacy ветка
docker compose -f docker-compose.platform.yml up -d --build platform-api

# Шарenная БД не трогаем — там старых данных нет (Phase 6 пропущен).
```

## Smoke после cutover

```bash
# 1. Лендинг работает
curl -I https://auto-works.pro/

# 2. API platform работает
curl -I https://api.auto-works.pro/health

# 3. Tenant-app работает
curl -I https://app.auto-works.pro/health

# 4. Регистрация (создаёт owner + tenant + admin user в shared DB):
curl -X POST https://api.auto-works.pro/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"changeme123","company_name":"Test Autoservice"}'

# Получили access_token. Подождать ~5с (celery task делает seed).

# 5. /me возвращает claims:
curl https://app.auto-works.pro/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```
