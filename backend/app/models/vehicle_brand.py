from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class VehicleBrand(Base):
    """Марки автомобилей"""
    __tablename__ = "vehicle_brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)

    models = relationship("VehicleModel", back_populates="brand", cascade="all, delete-orphan")


class VehicleModel(Base):
    """Модели автомобилей"""
    __tablename__ = "vehicle_models"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("vehicle_brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)

    brand = relationship("VehicleBrand", back_populates="models")
