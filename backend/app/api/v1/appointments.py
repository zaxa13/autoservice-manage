from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.models.vehicle import Vehicle
from app.schemas.appointment import Appointment as AppointmentSchema, AppointmentCreate, AppointmentUpdate
from app.schemas.responses import ErrorResponse
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Запись не найдена"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


def _appointment_query(db: Session):
    return db.query(Appointment).options(
        joinedload(Appointment.vehicle).joinedload(Vehicle.brand),
        joinedload(Appointment.vehicle).joinedload(Vehicle.vehicle_model),
        joinedload(Appointment.order),
    )


@router.get(
    "/",
    response_model=List[AppointmentSchema],
    status_code=status.HTTP_200_OK,
    summary="Список записей",
    description=(
        "Возвращает записи на обслуживание с пагинацией и фильтрацией по дате. "
        "Сортировка: по посту, порядку и времени."
    ),
    responses=_auth,
)
def get_appointments(
    appointment_date: Optional[date] = Query(None, alias="date", description="Фильтр по дате"),
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _appointment_query(db)

    if appointment_date:
        query = query.filter(Appointment.date == appointment_date)

    appointments = (
        query.order_by(
            Appointment.post_id.asc(),
            Appointment.sort_order.asc(),
            Appointment.time.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return appointments


@router.get(
    "/{appointment_id}",
    response_model=AppointmentSchema,
    status_code=status.HTTP_200_OK,
    summary="Запись по ID",
    description="Возвращает запись на обслуживание с данными о ТС и заказ-наряде.",
    responses={**_auth, **_404},
)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = _appointment_query(db).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundException("Запись не найдена")
    return appointment


@router.post(
    "/",
    response_model=AppointmentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать запись",
    description="Создание новой записи на обслуживание. Доступно менеджеру и администратору.",
    responses=_write,
)
def create_appointment(
    appointment_create: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    appointment = Appointment(**appointment_create.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    appointment = _appointment_query(db).filter(Appointment.id == appointment.id).first()
    return appointment


@router.put(
    "/{appointment_id}",
    response_model=AppointmentSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить запись",
    description=(
        "Обновление записи: статус, дата, время, пост, порядок сортировки (drag-drop) и другие поля. "
        "Передавать нужно только изменяемые поля."
    ),
    responses={**_write, **_404},
)
def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundException("Запись не найдена")

    update_data = appointment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.commit()
    appointment = _appointment_query(db).filter(Appointment.id == appointment_id).first()
    return appointment


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить запись",
    description="Удаление записи на обслуживание. Доступно менеджеру и администратору.",
    responses={**_write, **_404},
)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundException("Запись не найдена")

    db.delete(appointment)
    db.commit()
    return None
