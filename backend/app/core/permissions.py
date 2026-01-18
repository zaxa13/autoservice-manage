from fastapi import HTTPException, status, Depends
from app.models.user import User, UserRole
from app.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Требует роль администратора"""
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}, role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user


def require_manager_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Требует роль менеджера или администратора"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        logger.warning(f"Unauthorized user attempted manager action: {current_user.username}, role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user


def require_accountant_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Требует роль бухгалтера или администратора"""
    if current_user.role not in [UserRole.ADMIN, UserRole.ACCOUNTANT]:
        logger.warning(f"Unauthorized user attempted accountant action: {current_user.username}, role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user
