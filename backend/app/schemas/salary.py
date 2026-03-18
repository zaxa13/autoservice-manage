from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.models.salary import SalaryStatus


class SalaryBase(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника")
    period_start: date = Field(..., description="Начало расчётного периода")
    period_end: date = Field(..., description="Конец расчётного периода")


class SalaryCreate(SalaryBase):
    base_salary: Decimal = Field(..., ge=0, description="Базовая ставка")
    bonus: Decimal = Field(0, ge=0, description="Премия")
    penalty: Decimal = Field(0, ge=0, description="Штраф / удержание")


class SalaryUpdate(BaseModel):
    bonus: Optional[Decimal] = Field(None, ge=0, description="Премия")
    penalty: Optional[Decimal] = Field(None, ge=0, description="Штраф / удержание")
    status: Optional[SalaryStatus] = Field(None, description="Статус выплаты")


class SalaryCalculate(SalaryBase):
    pass


class Salary(SalaryBase):
    id: int = Field(..., description="Уникальный ID расчёта")
    base_salary: Decimal = Field(..., description="Базовая ставка")
    bonus: Decimal = Field(..., description="Премия")
    penalty: Decimal = Field(..., description="Штраф / удержание")
    total: Decimal = Field(..., description="Итого к выплате")
    status: SalaryStatus = Field(..., description="Статус (calculated, paid)")
    created_at: datetime = Field(..., description="Дата расчёта")
    paid_at: Optional[datetime] = Field(None, description="Дата выплаты")

    class Config:
        from_attributes = True
