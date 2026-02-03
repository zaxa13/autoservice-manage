from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String, unique=True, index=True, nullable=True)
    license_plate = Column(String, index=True, nullable=True)
    brand_id = Column(Integer, ForeignKey("vehicle_brands.id", ondelete="RESTRICT"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("vehicle_models.id", ondelete="RESTRICT"), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    mileage = Column(Integer, nullable=True)  # Пробег в км
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    brand = relationship("VehicleBrand", foreign_keys=[brand_id])
    vehicle_model = relationship("VehicleModel", foreign_keys=[model_id])

    @property
    def model(self):
        """Alias для vehicle_model для совместимости со схемой ответа"""
        return self.vehicle_model
    customer = relationship("Customer", back_populates="vehicles")
    orders = relationship("Order", back_populates="vehicle")
    appointments = relationship("Appointment", back_populates="vehicle")

