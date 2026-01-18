from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class EmployeePosition(str, enum.Enum):
    ADMIN = "admin"        # Администратор
    MANAGER = "manager"   # Менеджер
    MECHANIC = "mechanic" # Механик


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    position = Column(Enum(EmployeePosition), nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    hire_date = Column(Date, nullable=False)
    salary_base = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="employee", uselist=False)
    orders_created = relationship("Order", foreign_keys="Order.employee_id", back_populates="employee")
    orders_mechanic = relationship("Order", foreign_keys="Order.mechanic_id", back_populates="mechanic")
    warehouse_transactions = relationship("WarehouseTransaction", back_populates="employee")
    salaries = relationship("Salary", back_populates="employee")

