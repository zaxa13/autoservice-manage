from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.schemas.customer import Customer as CustomerSchema, CustomerCreate, CustomerUpdate
from app.schemas.responses import ErrorResponse
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Клиент не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав (менеджер / админ)"}}


@router.get(
    "/",
    response_model=List[CustomerSchema],
    status_code=status.HTTP_200_OK,
    summary="Список клиентов",
    description="Возвращает список клиентов с пагинацией. Доступно всем авторизованным пользователям.",
    responses=_auth,
)
def get_customers(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers


@router.get(
    "/search/by-phone",
    response_model=List[CustomerSchema],
    status_code=status.HTTP_200_OK,
    summary="Поиск клиентов по телефону",
    description=(
        "Нечёткий поиск клиентов по номеру телефона. "
        "Номер нормализуется: убираются пробелы, дефисы, скобки, "
        "8 заменяется на +7 в начале."
    ),
    responses=_auth,
)
def search_customers_by_phone(
    phone: str = Query(..., min_length=3, description="Номер телефона (или его часть)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    phone_normalized = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

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

    if not customers:
        customers = db.query(Customer).filter(
            Customer.phone.like(f"%{phone_normalized}%")
        ).all()

    return customers


@router.get(
    "/{customer_id}",
    response_model=CustomerSchema,
    status_code=status.HTTP_200_OK,
    summary="Получить клиента по ID",
    description="Возвращает данные клиента. Возвращает 404 если клиент не найден.",
    responses={**_auth, **_404},
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException("Клиент не найден")
    return customer


@router.post(
    "/",
    response_model=CustomerSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать клиента",
    description="Создание нового клиента. Доступно менеджеру и администратору.",
    responses=_write,
)
def create_customer(
    customer_create: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    customer = Customer(**customer_create.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put(
    "/{customer_id}",
    response_model=CustomerSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить клиента",
    description=(
        "Обновление данных клиента. Передавать нужно только изменяемые поля. "
        "Доступно менеджеру и администратору. Возвращает 404 если клиент не найден."
    ),
    responses={**_write, **_404},
)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException("Клиент не найден")

    update_data = customer_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer
