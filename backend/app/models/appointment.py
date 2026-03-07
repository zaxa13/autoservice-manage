import enum
from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"      # Записан
    CONFIRMED = "confirmed"      # Подтверждён
    WAITING = "waiting"          # Ожидаем авто
    ARRIVED = "arrived"          # Авто на СТО
    IN_WORK = "in_work"          # В работе
    READY = "ready"              # Готов к выдаче
    COMPLETED = "completed"      # Завершён
    NO_SHOW = "no_show"          # Не явился
    CANCELLED = "cancelled"      # Отменён


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, nullable=False, default=AppointmentStatus.SCHEDULED.value)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    post_id = Column(Integer, ForeignKey("appointment_posts.id"), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="appointments")
    employee = relationship("Employee")
    post = relationship("AppointmentPost", back_populates="appointments")
