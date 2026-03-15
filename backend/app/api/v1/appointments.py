from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.models.vehicle import Vehicle
from app.schemas.appointment import Appointment as AppointmentSchema, AppointmentCreate, AppointmentUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()


def _appointment_query(db: Session):
    return db.query(Appointment).options(
        joinedload(Appointment.vehicle).joinedload(Vehicle.brand),
        joinedload(Appointment.vehicle).joinedload(Vehicle.vehicle_model),
        joinedload(Appointment.order),
    )


@router.get("/", response_model=List[AppointmentSchema])
def get_appointments(
    appointment_date: Optional[date] = Query(None, alias="date", description="Фильтр по дате"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка записей"""
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


@router.get("/{appointment_id}", response_model=AppointmentSchema)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение записи по ID"""
    appointment = _appointment_query(db).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundException("Запись не найдена")
    return appointment


@router.post("/", response_model=AppointmentSchema)
def create_appointment(
    appointment_create: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание новой записи"""
    appointment = Appointment(**appointment_create.dict())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    appointment = _appointment_query(db).filter(Appointment.id == appointment.id).first()
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentSchema)
def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление записи (в т.ч. post_id, sort_order при drag-drop, status)."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundException("Запись не найдена")

    update_data = appointment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.commit()
    appointment = _appointment_query(db).filter(Appointment.id == appointment_id).first()
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Удаление записи"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise NotFoundException("Запись не найдена")

    db.delete(appointment)
    db.commit()
    return None
