from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, User as UserSchema
from app.services.auth_service import authenticate_user, create_user, create_token
from app.core.security import decode_access_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
optional_bearer = HTTPBearer(auto_error=False)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Эндпоинт для получения JWT токена"""
    # Ищем и аутентифицируем пользователя
    user = authenticate_user(db, form_data.username, form_data.password)
    
    # Создаем токен
    token = create_token(user)
    
    logger.info(f"Успешный вход пользователя: {user.username}")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserSchema)
def get_current_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    """Получение информации о текущем пользователе"""
    return current_user


@router.post("/register", response_model=UserSchema)
def register(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer)
):
    """Регистрация нового пользователя. Первый пользователь - админ без токена."""
    user_count = db.query(User).count()
    
    if user_count == 0:
        # Первый пользователь - автоматически администратор, не требует токен
        logger.info("Creating first admin user (no token required)")
        user_create.role = UserRole.ADMIN
        user = create_user(db, user_create)
        return user
    else:
        # Если пользователи есть, требуется токен администратора
        if not credentials:
            logger.warning(f"Registration attempted without credentials when {user_count} user(s) exist")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"В системе уже есть {user_count} пользователь(ей). Для регистрации нового пользователя требуется авторизация администратора. Войдите в систему через /api/v1/auth/login и используйте полученный токен.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем токен
        payload = decode_access_token(credentials.credentials)
        if not payload:
            logger.warning("Invalid token provided during registration")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username = payload.get("sub")
        if not username:
            logger.warning(f"Token payload missing 'sub' field during registration")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен: отсутствует username",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        current_user = db.query(User).filter(User.username == username).first()
        if not current_user:
            logger.warning(f"User not found during registration check: username={username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not current_user.is_active:
            logger.warning(f"Inactive user attempted registration: username={username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Пользователь неактивен"
            )
        
        if current_user.role != UserRole.ADMIN:
            logger.warning(f"Non-admin user attempted registration: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администратор может создавать пользователей"
            )
        
        user = create_user(db, user_create)
        logger.info(f"User registered by admin {current_user.username}: {user.username}")
        return user
