from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.core.permissions import require_manager_or_admin
from app.integrations.gibdd import check_vehicle_gibdd
from app.integrations.parts_suppliers import search_parts, create_supplier_order

router = APIRouter()


@router.get("/gibdd/vehicle/{vin}")
def get_vehicle_info_gibdd(
    vin: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Проверка транспортного средства в базе ГИБДД"""
    result = check_vehicle_gibdd(db, vin)
    return result


@router.get("/suppliers/search")
def search_parts_suppliers(
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Поиск запчастей у поставщиков"""
    result = search_parts(db, query)
    return result


@router.post("/suppliers/order")
def create_supplier_order_endpoint(
    supplier_order_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание заказа у поставщика"""
    result = create_supplier_order(db, supplier_order_data)
    return result

