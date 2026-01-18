from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.salary import Salary
from app.schemas.salary import Salary as SalarySchema, SalaryCalculate, SalaryUpdate
from app.services.salary_service import calculate_salary
from app.core.exceptions import NotFoundException
from app.core.permissions import require_accountant_or_admin

router = APIRouter()


@router.get("/", response_model=List[SalarySchema])
def get_salaries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin)
):
    """Получение списка расчетов зарплаты"""
    salaries = db.query(Salary).offset(skip).limit(limit).all()
    return salaries


@router.get("/{salary_id}", response_model=SalarySchema)
def get_salary(
    salary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin)
):
    """Получение расчета зарплаты по ID"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise NotFoundException("Расчет зарплаты не найден")
    return salary


@router.post("/calculate", response_model=SalarySchema)
def calculate_employee_salary(
    salary_calculate: SalaryCalculate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin)
):
    """Расчет зарплаты сотрудника за период"""
    try:
        salary = calculate_salary(db, salary_calculate)
        return salary
    except ValueError as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{salary_id}/pay", response_model=SalarySchema)
def mark_salary_paid(
    salary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin)
):
    """Отметка о выплате зарплаты"""
    from datetime import datetime
    from app.models.salary import SalaryStatus
    
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise NotFoundException("Расчет зарплаты не найден")
    
    salary.status = SalaryStatus.PAID
    salary.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(salary)
    return salary

