#!/bin/sh
set -e

echo "→ Ожидание базы данных..."
until python -c "
import asyncpg, asyncio, os
async def check():
    url = os.environ['DATABASE_URL']
    # Преобразуем postgresql:// → asyncpg-совместимый формат
    url = url.replace('postgresql://', 'postgres://')
    conn = await asyncpg.connect(url)
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
  echo "  БД недоступна, ждём 2 сек..."
  sleep 2
done
echo "  БД готова"

echo "→ Запуск миграций..."
cd /app/backend
alembic upgrade head

# Sanity check: alembic_version в БД должна совпадать с head из миграций.
# Был кейс, когда `alembic upgrade head` выходил 0, но реально миграции не
# коммитились (alembic_version застревал на промежуточной ревизии). Тогда
# контейнер стартовал, но FastAPI падал в lifespan на отсутствующих таблицах.
EXPECTED=$(alembic heads 2>/dev/null | awk '{print $1}' | head -1)
CURRENT=$(alembic current 2>/dev/null | awk '/^[a-z0-9]/{print $1}' | head -1)
if [ -z "$EXPECTED" ] || [ "$CURRENT" != "$EXPECTED" ]; then
  echo "FATAL: alembic_version=$CURRENT, ожидалось $EXPECTED. Миграции применились не полностью." >&2
  exit 1
fi
echo "  Миграции применены до $CURRENT"

echo "→ Запуск приложения..."
exec supervisord -c /app/supervisord.conf
