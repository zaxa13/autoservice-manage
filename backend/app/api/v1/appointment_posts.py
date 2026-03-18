from fastapi import APIRouter, Depends, status
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
from app.schemas.responses import ErrorResponse
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Пост не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.get(
    "/",
    response_model=List[AppointmentPostSchema],
    status_code=status.HTTP_200_OK,
    summary="Список постов",
    description="Возвращает посты (колонки) для доски записей, отсортированные по `sort_order`.",
    responses=_auth,
)
def list_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(AppointmentPost).order_by(AppointmentPost.sort_order.asc()).all()


@router.get(
    "/{post_id}",
    response_model=AppointmentPostSchema,
    status_code=status.HTTP_200_OK,
    summary="Пост по ID",
    description="Возвращает данные поста. Возвращает 404 если не найден.",
    responses={**_auth, **_404},
)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(AppointmentPost).filter(AppointmentPost.id == post_id).first()
    if not post:
        raise NotFoundException("Пост не найден")
    return post


@router.post(
    "/",
    response_model=AppointmentPostSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пост",
    description=(
        "Создание нового поста (колонки) для доски записей. "
        "Задаётся имя, максимум слотов, временные слоты, цвет и порядок."
    ),
    responses=_write,
)
def create_post(
    payload: AppointmentPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
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


@router.put(
    "/{post_id}",
    response_model=AppointmentPostSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить пост",
    description="Обновление данных поста. Передавать нужно только изменяемые поля.",
    responses={**_write, **_404},
)
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


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пост",
    description="Удаление поста (колонки). Доступно менеджеру и администратору.",
    responses={**_write, **_404},
)
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
