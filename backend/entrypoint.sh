#!/usr/bin/env bash
# Tenant-app entrypoint: alembic upgrade head + exec CMD.
#
# Alembic подключается под `migrator_app` (DATABASE_URL_MIGRATOR),
# который имеет BYPASSRLS и владеет схемой `app`. Сам uvicorn —
# под `tenant_app` (DATABASE_URL), без BYPASSRLS.
set -euo pipefail

echo "[entrypoint] Running alembic upgrade head…"
alembic upgrade head

echo "[entrypoint] Starting application: $*"
exec "$@"
