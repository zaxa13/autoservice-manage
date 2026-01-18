from sqlalchemy import Column, Integer, String, Numeric, Enum
import enum
from app.database import Base


class WorkCategory(str, enum.Enum):
    DIAGNOSTICS = "diagnostics"
    REPAIR = "repair"
    MAINTENANCE = "maintenance"
    BODY_WORK = "body_work"
    PAINTING = "painting"
    OTHER = "other"


class Work(Base):
    __tablename__ = "works"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    category = Column(Enum(WorkCategory), nullable=False, default=WorkCategory.OTHER)

