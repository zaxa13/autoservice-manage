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
echo "  Миграции применены"

echo "→ Запуск приложения..."
exec supervisord -c /app/supervisord.conf
