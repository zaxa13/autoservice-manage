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
    part_number = Column(String, index=True, nullable=True)
    brand = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    unit = Column(String, nullable=False, default="шт")
    category = Column(Enum(PartCategory), nullable=False, default=PartCategory.OTHER)

