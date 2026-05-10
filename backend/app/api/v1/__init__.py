"""API v1 router. Phase 3 — все 17 роутеров на shared-DB."""
from fastapi import APIRouter

from app.api.v1 import (
    appointment_posts,
    appointments,
    auth_me,
    cashflow,
    customers,
    dashboard,
    employees,
    integrations,
    orders,
    parts,
    payments,
    reports,
    salary,
    settings_api,
    suppliers,
    users,
    vehicle_brands,
    vehicles,
    warehouse,
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
api_router.include_router(employees.router, prefix="/employees", tags=["Сотрудники"])
api_router.include_router(users.router, prefix="/users", tags=["Пользователи"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["ТС"])
api_router.include_router(
    appointment_posts.router, prefix="/appointment-posts", tags=["Посты"]
)
api_router.include_router(orders.router, prefix="/orders", tags=["Заказ-наряды"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Записи"])
api_router.include_router(cashflow.router, prefix="/cashflow", tags=["Касса"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["Склад"])
api_router.include_router(salary.router, prefix="/salary", tags=["Зарплата"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Дашборд"])
api_router.include_router(reports.router, prefix="/reports", tags=["Отчёты"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Интеграции"])
api_router.include_router(payments.router, prefix="/payments", tags=["Платежи (ЮКасса)"])
