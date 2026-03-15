from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.appointment_post import AppointmentPost
from app.schemas.appointment_post import (
    AppointmentPost as AppointmentPostSchema,
    AppointmentPostCreate,
    AppointmentPostUpdate,
)
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException

router = APIRouter()


@router.get("/", response_model=List[AppointmentPostSchema])
def list_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список постов (колонок) для записей, по sort_order."""
    return db.query(AppointmentPost).order_by(AppointmentPost.sort_order.asc()).all()


@router.get("/{post_id}", response_model=AppointmentPostSchema)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(AppointmentPost).filter(AppointmentPost.id == post_id).first()
    if not post:
        raise NotFoundException("Пост не найден")
    return post


@router.post("/", response_model=AppointmentPostSchema)
def create_post(
    payload: AppointmentPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """Создание поста. Имя типа «Пост 1», max_slots — макс. записей в колонке."""
    post = AppointmentPost(
        name=payload.name,
        max_slots=payload.max_slots,
        slot_times=payload.slot_times,
        color=payload.color,
        sort_order=payload.sort_order,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.put("/{post_id}", response_model=AppointmentPostSchema)
def update_post(
    post_id: int,
    payload: AppointmentPostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    post = db.query(AppointmentPost).filter(AppointmentPost.id == post_id).first()
    if not post:
        raise NotFoundException("Пост не найден")
    if payload.name is not None:
        post.name = payload.name
    if payload.max_slots is not None:
        post.max_slots = payload.max_slots
    if payload.slot_times is not None:
        post.slot_times = payload.slot_times
    if payload.color is not None:
        post.color = payload.color
    if payload.sort_order is not None:
        post.sort_order = payload.sort_order
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    post = db.query(AppointmentPost).filter(AppointmentPost.id == post_id).first()
    if not post:
        raise NotFoundException("Пост не найден")
    db.delete(post)
    db.commit()
    return None
