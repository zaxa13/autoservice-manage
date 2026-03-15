from sqlalchemy import Column, Integer, String, Numeric, Enum
import enum
from app.database import Base


class PartCategory(str, enum.Enum):
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    SUSPENSION = "suspension"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    BODY = "body"
    CONSUMABLES = "consumables"
    OTHER = "other"


class Part(Base):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    part_number = Column(String, index=True, nullable=False)  # Артикул обязателен (идентификация при списании)
    brand = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    purchase_price_last = Column(Numeric(10, 2), nullable=True)
    unit = Column(String, nullable=False, default="шт")
    category = Column(Enum(PartCategory, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=PartCategory.OTHER)

