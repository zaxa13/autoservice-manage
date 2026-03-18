from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supplier import Supplier
from app.schemas.supplier import Supplier as SupplierSchema, SupplierCreate, SupplierUpdate
from app.schemas.responses import ErrorResponse
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Поставщик не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.get(
    "/",
    response_model=List[SupplierSchema],
    status_code=status.HTTP_200_OK,
    summary="Список поставщиков",
    description="Возвращает список поставщиков с пагинацией.",
    responses=_auth,
)
def list_suppliers(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Supplier).offset(skip).limit(limit).all()


@router.get(
    "/{supplier_id}",
    response_model=SupplierSchema,
    status_code=status.HTTP_200_OK,
    summary="Получить поставщика по ID",
    description="Возвращает данные поставщика. Возвращает 404 если не найден.",
    responses={**_auth, **_404},
)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise NotFoundException("Поставщик не найден")
    return s


@router.post(
    "/",
    response_model=SupplierSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать поставщика",
    description="Создание нового поставщика. Доступно менеджеру и администратору.",
    responses=_write,
)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    s = Supplier(
        name=payload.name,
        inn=payload.inn,
        kpp=payload.kpp,
        legal_address=payload.legal_address,
        contact=payload.contact,
        bank_name=payload.bank_name,
        bik=payload.bik,
        bank_account=payload.bank_account,
        correspondent_account=payload.correspondent_account,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put(
    "/{supplier_id}",
    response_model=SupplierSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить поставщика",
    description="Обновление данных поставщика. Передавать нужно только изменяемые поля.",
    responses={**_write, **_404},
)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise NotFoundException("Поставщик не найден")
    if payload.name is not None:
        s.name = payload.name
    if payload.inn is not None:
        s.inn = payload.inn
    if payload.kpp is not None:
        s.kpp = payload.kpp
    if payload.legal_address is not None:
        s.legal_address = payload.legal_address
    if payload.contact is not None:
        s.contact = payload.contact
    if payload.bank_name is not None:
        s.bank_name = payload.bank_name
    if payload.bik is not None:
        s.bik = payload.bik
    if payload.bank_account is not None:
        s.bank_account = payload.bank_account
    if payload.correspondent_account is not None:
        s.correspondent_account = payload.correspondent_account
    db.commit()
    db.refresh(s)
    return s


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить поставщика",
    description="Удаление поставщика. Доступно менеджеру и администратору.",
    responses={**_write, **_404},
)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise NotFoundException("Поставщик не найден")
    db.delete(s)
    db.commit()
    return None
