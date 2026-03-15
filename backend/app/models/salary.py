from sqlalchemy import Column, Integer, ForeignKey, Date, Numeric, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class SalaryStatus(str, enum.Enum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    PAID = "paid"


class Salary(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_salary = Column(Numeric(10, 2), nullable=False, default=0)
    bonus = Column(Numeric(10, 2), nullable=False, default=0)
    penalty = Column(Numeric(10, 2), nullable=False, default=0)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(Enum(SalaryStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=SalaryStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="salaries")

