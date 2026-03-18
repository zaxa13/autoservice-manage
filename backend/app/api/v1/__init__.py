from fastapi import APIRouter
from app.api.v1 import (
    auth, users, orders, vehicles, customers, works, parts,
    warehouse, employees, salary, payments, integrations,
    appointments, appointment_posts, vehicle_brands, suppliers,
    dashboard, settings_api,
)

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Дашборд"])
api_router.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
api_router.include_router(users.router, prefix="/users", tags=["Пользователи"])
api_router.include_router(orders.router, prefix="/orders", tags=["Заказ-наряды"])
api_router.include_router(customers.router, prefix="/customers", tags=["Клиенты"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Транспортные средства"])
api_router.include_router(works.router, prefix="/works", tags=["Виды работ"])
api_router.include_router(parts.router, prefix="/parts", tags=["Запчасти"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["Склад"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Поставщики"])
api_router.include_router(employees.router, prefix="/employees", tags=["Сотрудники"])
api_router.include_router(salary.router, prefix="/salary", tags=["Зарплата"])
api_router.include_router(payments.router, prefix="/payments", tags=["Платежи (YooKassa)"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Интеграции"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Записи на обслуживание"])
api_router.include_router(appointment_posts.router, prefix="/appointment-posts", tags=["Посты (колонки записей)"])
api_router.include_router(vehicle_brands.router, prefix="/vehicle-brands", tags=["Марки и модели"])
api_router.include_router(settings_api.router, prefix="/settings", tags=["Настройки"])
