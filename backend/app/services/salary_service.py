from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from decimal import Decimal
from app.models.salary import Salary, SalaryStatus
from app.models.order import Order, OrderStatus
from app.models.employee import Employee
from app.schemas.salary import SalaryCalculate
from app.core.exceptions import NotFoundException


def calculate_salary(
    db: Session,
    salary_calculate: SalaryCalculate
) -> Salary:
    """Расчет зарплаты сотрудника за период"""
    employee = db.query(Employee).filter(Employee.id == salary_calculate.employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")
    
    # Проверка существующего расчета
    existing = db.query(Salary).filter(
        Salary.employee_id == salary_calculate.employee_id,
        Salary.period_start == salary_calculate.period_start,
        Salary.period_end == salary_calculate.period_end
    ).first()
    
    if existing:
        raise ValueError("Расчет зарплаты за этот период уже существует")
    
    # Базовая зарплата
    base_salary = employee.salary_base
    
    # Подсчет выполненных заказ-нарядов за период
    completed_orders = db.query(Order).filter(
        Order.mechanic_id == employee.id,
        Order.status == OrderStatus.READY_FOR_PAYMENT,
        Order.completed_at >= salary_calculate.period_start,
        Order.completed_at <= salary_calculate.period_end
    ).count()
    
    # Бонус (например, 5% от базовой за каждый выполненный заказ-наряд)
    bonus_per_order = base_salary * Decimal("0.05")
    bonus = bonus_per_order * completed_orders
    
    # Штрафы (можно добавить логику)
    penalty = Decimal(0)
    
    total = base_salary + bonus - penalty
    
    salary = Salary(
        employee_id=employee.id,
        period_start=salary_calculate.period_start,
        period_end=salary_calculate.period_end,
        base_salary=base_salary,
        bonus=bonus,
        penalty=penalty,
        total=total,
        status=SalaryStatus.CALCULATED
    )
    db.add(salary)
    db.commit()
    db.refresh(salary)
    return salary

