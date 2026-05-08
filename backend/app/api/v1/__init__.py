"""API v1 router.

В Phase 3 мигрированы только роутеры из этого списка ниже.
Остальные (orders, vehicles, parts, works, employees, ...) лежат в файлах
рядом, но НЕ подключены — их код использует старый sync-database и сломан
до миграции в следующих коммитах. См. backend/PHASE3_TODO.md.
"""
from fastapi import APIRouter

from app.api.v1 import auth_me, customers

api_router = APIRouter()

api_router.include_router(auth_me.router, prefix="/auth", tags=["Auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["Клиенты"])
