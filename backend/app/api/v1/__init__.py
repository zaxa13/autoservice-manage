"""API v1 router.

Phase 3 wave 1 routers (мигрированы и подключены): auth_me, customers,
works, parts, suppliers, vehicle_brands, settings_api.

Остальные ~14 роутеров не подключены до миграции — см. backend/PHASE3_TODO.md.
"""
from fastapi import APIRouter

from app.api.v1 import (
    auth_me,
    customers,
    parts,
    settings_api,
    suppliers,
    vehicle_brands,
    works,
)

api_router = APIRouter()

api_router.include_router(auth_me.router, prefix="/auth", tags=["Auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["Клиенты"])
api_router.include_router(works.router, prefix="/works", tags=["Виды работ"])
api_router.include_router(parts.router, prefix="/parts", tags=["Запчасти"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Поставщики"])
api_router.include_router(
    vehicle_brands.router, prefix="/vehicle-brands", tags=["Марки и модели"]
)
api_router.include_router(settings_api.router, prefix="/settings", tags=["Настройки"])
