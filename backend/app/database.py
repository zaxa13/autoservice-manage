from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# SQLite не поддерживает пулы соединений, поэтому настраиваем engine в зависимости от типа БД
if settings.DATABASE_URL.startswith("sqlite"):
    # Для SQLite используем connect_args для включения проверки внешних ключей
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}  # Необходимо для SQLite с FastAPI
    )
else:
    # Для PostgreSQL и других БД используем пулы соединений
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

