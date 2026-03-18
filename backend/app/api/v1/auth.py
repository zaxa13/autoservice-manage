from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
import secrets
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.password_reset import PasswordResetToken
from app.schemas.user import UserCreate, User as UserSchema, ChangePasswordRequest, ForgotPasswordRequest, ConfirmResetPasswordRequest
from app.schemas.responses import TokenResponse, ChangePasswordResponse, ErrorResponse, MessageResponse
from app.services.auth_service import authenticate_user, create_user, create_token
from app.services.email_service import send_password_reset_email
from app.core.security import verify_password, get_password_hash
from app.core.security import decode_access_token
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
optional_bearer = HTTPBearer(auto_error=False)

_401 = {401: {"model": ErrorResponse, "description": "Неверные учётные данные"}}
_403 = {403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Авторизация (получение JWT)",
    description=(
        "Принимает `username` и `password` через OAuth2 form-data. "
        "Возвращает JWT access-токен для дальнейших запросов. "
        "При неверных учётных данных возвращает 401."
    ),
    responses=_401,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    token = create_token(user)
    logger.info(f"Успешный вход пользователя: {user.username}")
    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserSchema,
    status_code=status.HTTP_200_OK,
    summary="Текущий пользователь",
    description="Возвращает данные авторизованного пользователя по JWT-токену.",
    responses=_401,
)
def get_current_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Смена пароля",
    description=(
        "Смена пароля текущего пользователя. "
        "Требует ввод текущего пароля. Доступно любому авторизованному пользователю. "
        "После успешной смены снимает флаг `password_must_be_changed`. "
        "Возвращает 400 при неверном текущем пароле."
    ),
    responses={**_401, 400: {"model": ErrorResponse, "description": "Неверный текущий пароль"}},
)
def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль",
        )
    current_user.password_hash = get_password_hash(data.new_password)
    current_user.password_must_be_changed = False
    db.commit()
    db.refresh(current_user)
    return {"message": "Пароль успешно изменён", "user": current_user}


@router.post(
    "/register",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description=(
        "Регистрация нового пользователя. Первый пользователь автоматически становится "
        "администратором и не требует JWT-токен. Последующие регистрации доступны только "
        "администратору с валидным токеном. "
        "Возвращает 401 при отсутствии/невалидном токене, 403 если пользователь не админ."
    ),
    responses={**_401, **_403},
)
def register(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
):
    user_count = db.query(User).count()

    if user_count == 0:
        logger.info("Creating first admin user (no token required)")
        user_create.role = UserRole.ADMIN
        user = create_user(db, user_create)
        return user
    else:
        if not credentials:
            logger.warning(f"Registration attempted without credentials when {user_count} user(s) exist")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"В системе уже есть {user_count} пользователь(ей). Для регистрации нового пользователя требуется авторизация администратора. Войдите в систему через /api/v1/auth/login и используйте полученный токен.",
                headers={"WWW-Authenticate": "Bearer"},
            )

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
            logger.warning("Token payload missing 'sub' field during registration")
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
                detail="Пользователь неактивен",
            )

        if current_user.role != UserRole.ADMIN:
            logger.warning(f"Non-admin user attempted registration: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администратор может создавать пользователей",
            )

        user = create_user(db, user_create)
        logger.info(f"User registered by admin {current_user.username}: {user.username}")
        return user


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Запрос сброса пароля",
    description=(
        "Принимает email. Если пользователь с таким email существует — "
        "отправляет письмо со ссылкой для сброса пароля (токен действует 30 минут). "
        "В целях безопасности всегда возвращает одинаковый ответ, "
        "независимо от того, найден ли пользователь."
    ),
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.is_active:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
        ).update({"is_used": True})
        db.flush()

        raw_token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=raw_token,
            expires_at=expires_at,
        )
        db.add(reset_token)
        db.commit()

        sent = send_password_reset_email(user.email, user.username, raw_token)
        if sent:
            logger.info(f"Password reset email sent to user id={user.id}")
        else:
            logger.warning(f"Failed to send reset email to user id={user.id} (SMTP not configured?)")

    return {"message": "Если аккаунт с таким email существует, письмо со ссылкой для сброса пароля было отправлено."}


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Подтверждение сброса пароля",
    description=(
        "Принимает токен из письма и новый пароль. "
        "Устанавливает новый пароль и инвалидирует токен. "
        "Токен одноразовый и действителен 30 минут."
    ),
    responses={400: {"model": ErrorResponse, "description": "Токен недействителен или истёк"}},
)
def reset_password(
    data: ConfirmResetPasswordRequest,
    db: Session = Depends(get_db),
):
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == data.token)
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный токен сброса пароля",
        )

    if reset_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Токен уже был использован",
        )

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок действия токена истёк. Запросите новую ссылку.",
        )

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не найден или неактивен",
        )

    user.password_hash = get_password_hash(data.new_password)
    user.password_must_be_changed = False
    reset_token.is_used = True
    db.commit()

    logger.info(f"Password successfully reset for user id={user.id} ({user.username})")
    return {"message": "Пароль успешно изменён. Теперь вы можете войти с новым паролем."}
