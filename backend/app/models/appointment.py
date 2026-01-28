from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    description = Column(String, nullable=True)  # Описание/примечание к записи
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)  # Опциональная связь с авто
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Опциональная связь с механиком
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="appointments")
    employee = relationship("Employee")
