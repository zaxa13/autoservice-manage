from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate, ResetPasswordRequest
from app.core.permissions import require_admin
from app.core.security import get_password_hash

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
def get_users(
    current_user: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получение списка пользователей (только для администратора)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db)
):
    """Получение пользователя по ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Пользователь не найден")
    return user


@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db)
):
    """Обновление пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from app.core.exceptions import NotFoundException
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
        from app.core.security import get_password_hash
        user.password_hash = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    data: ResetPasswordRequest,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    """
    Сброс пароля пользователя (только для администратора).
    Устанавливает новый пароль и флаг password_must_be_changed.
    Пользователь при следующем входе должен сменить пароль.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Пользователь не найден")
    user.password_hash = get_password_hash(data.new_password)
    user.password_must_be_changed = True
    db.commit()
    return {"message": "Пароль сброшен. Пользователь должен сменить его при следующем входе."}

