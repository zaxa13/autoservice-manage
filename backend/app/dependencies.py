from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.security import decode_access_token
import logging

logger = logging.getLogger(__name__)

# HTTPBearer для Swagger UI
bearer_scheme = HTTPBearer(auto_error=False)

# OAuth2PasswordBearer для стандартного OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    token_oauth: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Зависимость для получения текущего аутентифицированного пользователя"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Получаем токен из любого источника
    token = None
    if credentials:
        token = credentials.credentials
    elif token_oauth:
        token = token_oauth
    
    if not token:
        logger.warning("Токен не предоставлен")
        raise credentials_exception
    
    # Декодируем токен
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Попытка использования невалидного токена")
        raise credentials_exception
    
    # Извлекаем username из токена
    username: str = payload.get("sub")
    if username is None:
        logger.warning("Токен не содержит username")
        raise credentials_exception
    
    # Находим пользователя в БД
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        logger.warning(f"Пользователь не найден: {username}")
        raise credentials_exception
    
    # Проверяем, активен ли пользователь
    if not user.is_active:
        logger.warning(f"Попытка доступа неактивного пользователя: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись неактивна",
        )
    
    logger.info(f"User authenticated successfully: username={username}, user_id={user.id}")
    return user
