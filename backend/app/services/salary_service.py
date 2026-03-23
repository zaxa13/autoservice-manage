from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from decimal import Decimal
from app.models.salary import Salary, SalaryStatus, SalaryScheme
from app.models.order import Order, OrderStatus
from app.models.employee import Employee, EmployeePosition
from app.schemas.salary import SalaryCalculate, SalarySchemeUpdate, SalarySchemeResponse
from app.core.exceptions import NotFoundException


def get_salary_scheme(db: Session, employee_id: int) -> SalarySchemeResponse:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")
    scheme = db.query(SalaryScheme).filter(SalaryScheme.employee_id == employee_id).first()
    if not scheme:
        return SalarySchemeResponse(id=None, employee_id=employee_id, works_percentage=Decimal(0), revenue_percentage=Decimal(0))
    return scheme


def update_salary_scheme(db: Session, employee_id: int, data: SalarySchemeUpdate) -> SalaryScheme:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")
    scheme = db.query(SalaryScheme).filter(SalaryScheme.employee_id == employee_id).first()
    if not scheme:
        scheme = SalaryScheme(employee_id=employee_id)
        db.add(scheme)
    scheme.works_percentage = data.works_percentage
    scheme.revenue_percentage = data.revenue_percentage
    db.commit()
    db.refresh(scheme)
    return scheme


def calculate_salary(db: Session, salary_calculate: SalaryCalculate) -> Salary:
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

    base_salary = employee.salary_base or Decimal(0)

    # Получаем схему зарплаты
    scheme = db.query(SalaryScheme).filter(SalaryScheme.employee_id == employee.id).first()

    # Используем func.date() чтобы отрезать время у completed_at — иначе SQLite
    # сравнивает datetime-строку с date-объектом некорректно
    period_start_str = salary_calculate.period_start.isoformat()
    period_end_str = salary_calculate.period_end.isoformat()

    if employee.position == EmployeePosition.MECHANIC:
        # Механик: % от суммы завершённых заказов где mechanic_id = employee.id
        completed_sum = db.query(func.sum(Order.total_amount)).filter(
            Order.mechanic_id == employee.id,
            Order.status == OrderStatus.COMPLETED,
            func.date(Order.completed_at) >= period_start_str,
            func.date(Order.completed_at) <= period_end_str
        ).scalar() or Decimal(0)

        percentage = scheme.works_percentage if scheme else Decimal(0)
        bonus = Decimal(str(completed_sum)) * percentage / 100

    elif employee.position in (EmployeePosition.MANAGER, EmployeePosition.ADMIN):
        # Менеджер/Админ: % от суммы завершённых заказов где employee_id = employee.id
        completed_sum = db.query(func.sum(Order.total_amount)).filter(
            Order.employee_id == employee.id,
            Order.status == OrderStatus.COMPLETED,
            func.date(Order.completed_at) >= period_start_str,
            func.date(Order.completed_at) <= period_end_str
        ).scalar() or Decimal(0)

        percentage = scheme.revenue_percentage if scheme else Decimal(0)
        bonus = Decimal(str(completed_sum)) * percentage / 100

    else:
        bonus = Decimal(0)

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
