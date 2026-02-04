from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supplier import Supplier
from app.schemas.supplier import Supplier as SupplierSchema, SupplierCreate, SupplierUpdate
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException

router = APIRouter()


@router.get("/", response_model=List[SupplierSchema])
def list_suppliers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список поставщиков."""
    return db.query(Supplier).offset(skip).limit(limit).all()


@router.get("/{supplier_id}", response_model=SupplierSchema)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Поставщик по ID."""
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise NotFoundException("Поставщик не найден")
    return s


@router.post("/", response_model=SupplierSchema)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Создание поставщика."""
    s = Supplier(name=payload.name, inn=payload.inn, contact=payload.contact)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/{supplier_id}", response_model=SupplierSchema)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Обновление поставщика."""
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise NotFoundException("Поставщик не найден")
    if payload.name is not None:
        s.name = payload.name
    if payload.inn is not None:
        s.inn = payload.inn
    if payload.contact is not None:
        s.contact = payload.contact
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Удаление поставщика."""
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise NotFoundException("Поставщик не найден")
    db.delete(s)
    db.commit()
    return None
