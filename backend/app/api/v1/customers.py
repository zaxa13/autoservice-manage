from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.schemas.customer import Customer as CustomerSchema, CustomerCreate, CustomerUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()


@router.get("/", response_model=List[CustomerSchema])
def get_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка клиентов"""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers


@router.get("/search/by-phone", response_model=List[CustomerSchema])
def search_customers_by_phone(
    phone: str = Query(..., description="Номер телефона"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск клиентов по номеру телефона"""
    # Нормализуем номер телефона: убираем все кроме цифр и +
    phone_normalized = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Если номер начинается с +7, ищем по нему, иначе ищем по любой части
    if phone_normalized.startswith('+7'):
        phone_search = phone_normalized
    elif phone_normalized.startswith('7'):
        phone_search = '+' + phone_normalized
    elif phone_normalized.startswith('8'):
        phone_search = '+7' + phone_normalized[1:]
    else:
        phone_search = '+7' + phone_normalized
    
    customers = db.query(Customer).filter(
        Customer.phone.like(f"%{phone_search}%")
    ).all()
    
    # Если не найдено по нормализованному номеру, ищем по части
    if not customers:
        customers = db.query(Customer).filter(
            Customer.phone.like(f"%{phone_normalized}%")
        ).all()
    
    return customers


@router.get("/{customer_id}", response_model=CustomerSchema)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение клиента по ID"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException("Клиент не найден")
    return customer


@router.post("/", response_model=CustomerSchema)
def create_customer(
    customer_create: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание нового клиента"""
    customer = Customer(**customer_create.dict())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{customer_id}", response_model=CustomerSchema)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление клиента"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException("Клиент не найден")
    
    update_data = customer_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    db.commit()
    db.refresh(customer)
    return customer
