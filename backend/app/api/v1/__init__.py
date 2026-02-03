from fastapi import APIRouter
from app.api.v1 import auth, users, orders, vehicles, customers, works, parts, warehouse, employees, salary, payments, integrations, appointments, vehicle_brands

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(works.router, prefix="/works", tags=["works"])
api_router.include_router(parts.router, prefix="/parts", tags=["parts"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(salary.router, prefix="/salary", tags=["salary"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(vehicle_brands.router, prefix="/vehicle-brands", tags=["vehicle-brands"])

