from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.core.permissions import require_admin, require_manager_or_admin, require_accountant_or_admin


def get_db_session() -> Session:
    """Dependency для получения сессии БД"""
    return Depends(get_db)


def get_current_active_user() -> User:
    """Dependency для получения текущего активного пользователя"""
    return Depends(get_current_user)


def get_admin_user() -> User:
    """Dependency для получения администратора"""
    return Depends(lambda user: require_admin(user))


def get_manager_or_admin() -> User:
    """Dependency для получения менеджера или администратора"""
    return Depends(lambda user: require_manager_or_admin(user))


def get_accountant_or_admin() -> User:
    """Dependency для получения бухгалтера или администратора"""
    return Depends(lambda user: require_accountant_or_admin(user))

