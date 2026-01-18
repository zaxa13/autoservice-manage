from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import verify_password, get_password_hash, create_access_token
from app.config import settings as app_settings
import logging

logger = logging.getLogger(__name__)


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Аутентификация пользователя"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        logger.warning(f"Неудачная попытка входа для пользователя: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Попытка входа неактивного пользователя: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись неактивна",
        )
    
    return user


def create_user(db: Session, user_create: UserCreate) -> User:
    """Создание нового пользователя"""
    if db.query(User).filter(User.username == user_create.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    if db.query(User).filter(User.email == user_create.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    user = User(
        username=user_create.username,
        email=user_create.email,
        password_hash=get_password_hash(user_create.password),
        role=user_create.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"User created: {user.username}, id: {user.id}")
    return user


def create_token(user: User) -> str:
    """Создание JWT токена для пользователя"""
    access_token_expires = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},  # Используем username вместо id
        expires_delta=access_token_expires
    )
    logger.info(f"Token created for username: {user.username}, user_id: {user.id}")
    return access_token
