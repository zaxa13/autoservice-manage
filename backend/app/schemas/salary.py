from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.models.salary import SalaryStatus


class SalaryBase(BaseModel):
    employee_id: int
    period_start: date
    period_end: date


class SalaryCreate(SalaryBase):
    base_salary: Decimal
    bonus: Decimal = 0
    penalty: Decimal = 0


class SalaryUpdate(BaseModel):
    bonus: Optional[Decimal] = None
    penalty: Optional[Decimal] = None
    status: Optional[SalaryStatus] = None


class SalaryCalculate(SalaryBase):
    pass


class Salary(SalaryBase):
    id: int
    base_salary: Decimal
    bonus: Decimal
    penalty: Decimal
    total: Decimal
    status: SalaryStatus
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True

