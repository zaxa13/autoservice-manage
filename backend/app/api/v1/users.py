from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Annotated
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate, ResetPasswordRequest
from app.schemas.responses import MessageResponse, ErrorResponse
from app.core.permissions import require_admin
from app.core.security import get_password_hash
from app.core.exceptions import NotFoundException

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Пользователь не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}, 403: {"model": ErrorResponse, "description": "Только для администратора"}}


@router.get(
    "/",
    response_model=List[UserSchema],
    status_code=status.HTTP_200_OK,
    summary="Список пользователей",
    description="Возвращает список всех пользователей системы. Доступно только администратору.",
    responses=_auth,
)
def get_users(
    current_user: Annotated[User, Depends(require_admin)],
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get(
    "/{user_id}",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Получить пользователя по ID",
    description="Возвращает данные пользователя. Доступно только администратору. Возвращает 404 если пользователь не найден.",
    responses={**_auth, **_404},
)
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("Пользователь не найден")
    return user


@router.put(
    "/{user_id}",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить пользователя",
    description=(
        "Обновляет данные пользователя (логин, email, роль, статус, привязку к сотруднику, пароль). "
        "Передавать нужно только изменяемые поля. Доступно только администратору."
    ),
    responses={**_auth, **_404},
)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("Пользователь не найден")

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.employee_id is not None:
        user.employee_id = user_update.employee_id
    if user_update.password is not None:
        user.password_hash = get_password_hash(user_update.password)

    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Сброс пароля пользователя",
    description=(
        "Сбрасывает пароль указанного пользователя. Устанавливает новый пароль "
        "и флаг `password_must_be_changed`, требующий смену при следующем входе. "
        "Доступно только администратору."
    ),
    responses={**_auth, **_404},
)
def reset_user_password(
    user_id: int,
    data: ResetPasswordRequest,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("Пользователь не найден")
    user.password_hash = get_password_hash(data.new_password)
    user.password_must_be_changed = True
    db.commit()
    return {"message": "Пароль сброшен. Пользователь должен сменить его при следующем входе."}
