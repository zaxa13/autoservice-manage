from sqlalchemy import Column, Integer, String, Enum, DateTime, Text
from sqlalchemy.sql import func
import enum
from app.database import Base


class IntegrationType(str, enum.Enum):
    YOOKASSA = "yookassa"
    SMS = "sms"
    EMAIL = "email"
    PARTS_SUPPLIER = "parts_supplier"
    GIBDD = "gibdd"


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(Integer, primary_key=True, index=True)
    integration_type = Column(Enum(IntegrationType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status = Column(String, nullable=False)  # success, error, pending
    request_data = Column(Text, nullable=True)
    response_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

