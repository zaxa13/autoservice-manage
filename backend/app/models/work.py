from sqlalchemy import Column, Integer, String, Numeric, Enum
import enum
from app.database import Base


class WorkCategory(str, enum.Enum):
    DIAGNOSTICS = "diagnostics"
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    SUSPENSION = "suspension"
    BRAKES = "brakes"
    ELECTRICAL = "electrical"
    COOLING = "cooling"
    FUEL_SYSTEM = "fuel_system"
    EXHAUST = "exhaust"
    CLIMATE = "climate"
    MAINTENANCE = "maintenance"
    BODY_WORK = "body_work"
    PAINTING = "painting"
    TIRE_SERVICE = "tire_service"
    GLASS = "glass"
    REPAIR = "repair"
    OTHER = "other"


class Work(Base):
    __tablename__ = "works"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    category = Column(Enum(WorkCategory, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=WorkCategory.OTHER)

