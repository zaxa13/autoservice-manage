from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import os

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./autoservice.db"
    
    # Security - фиксированный SECRET_KEY для упрощенной JWT аутентификации
    # ВАЖНО: В продакшене должен быть установлен через переменные окружения
    # ДЕФОЛТНОЕ ЗНАЧЕНИЕ используется если SECRET_KEY не указан в .env или переменных окружения
    SECRET_KEY: str = "kBvn-wNzil142Y5KmOgzzh_bXfLfs3MUB_YI-McZ388"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ЮKassa
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    
    # SMS
    SMS_API_KEY: str = ""
    SMS_SENDER: str = "Autoservice"
    
    # Email
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "maliaaa@mail.ru"

    # Frontend URL (используется в ссылках для сброса пароля)
    FRONTEND_URL: str = "http://localhost:3000"

    # Время жизни токена сброса пароля (в минутах)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Поставщики
    PARTS_SUPPLIER_API_KEY: str = ""
    PARTS_SUPPLIER_API_URL: str = ""
    
    # ГИБДД
    GIBDD_API_KEY: str = ""
    GIBDD_API_URL: str = ""
    
    # Tenant identity (заполняется платформой при провижининге)
    TENANT_SLUG: str = ""
    TENANT_ID: str = ""
    PLAN: str = "start"

    # Admin seeding (заполняется платформой при провижининге)
    # Если заданы — создаётся admin-пользователь при первом старте
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore"  # Игнорируем дополнительные поля из .env
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Валидация SECRET_KEY при загрузке
        if not self.SECRET_KEY or not self.SECRET_KEY.strip():
            raise ValueError("SECRET_KEY не может быть пустым")
        if len(self.SECRET_KEY) < 32:
            logger.warning(f"SECRET_KEY слишком короткий ({len(self.SECRET_KEY)} символов). Рекомендуется минимум 32 символа.")
        
        # ДИАГНОСТИКА: Логируем какой SECRET_KEY используется
        secret_key_source = "environment variable" if os.getenv("SECRET_KEY") else ".env file" if os.path.exists(".env") and "SECRET_KEY" in open(".env").read() else "default value"
        logger.info(f"SECRET_KEY loaded from: {secret_key_source}, length: {len(self.SECRET_KEY)}, preview: {self.SECRET_KEY[:20]}...")


settings = Settings()
# Дополнительная диагностика после создания
logger.info(f"=== CONFIG: Final SECRET_KEY length: {len(settings.SECRET_KEY)}, value preview: {settings.SECRET_KEY[:30]}...")
logger.info(f"=== CONFIG: ALGORITHM: {settings.ALGORITHM}")
