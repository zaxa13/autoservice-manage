from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.salary import Salary
from app.schemas.salary import Salary as SalarySchema, SalaryCalculate, SalaryUpdate, SalarySchemeUpdate, SalarySchemeResponse
from app.schemas.responses import ErrorResponse
from app.services.salary_service import calculate_salary, get_salary_scheme, update_salary_scheme
from app.core.exceptions import NotFoundException
from app.core.permissions import require_accountant_or_admin, require_admin

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Расчёт зарплаты не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}, 403: {"model": ErrorResponse, "description": "Только бухгалтер / администратор"}}


@router.get(
    "/",
    response_model=List[SalarySchema],
    status_code=status.HTTP_200_OK,
    summary="Список расчётов зарплаты",
    description="Возвращает расчёты зарплат с пагинацией. Доступно бухгалтеру и администратору.",
    responses=_auth,
)
def get_salaries(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
):
    salaries = db.query(Salary).offset(skip).limit(limit).all()
    return salaries


@router.get(
    "/{salary_id}",
    response_model=SalarySchema,
    status_code=status.HTTP_200_OK,
    summary="Расчёт зарплаты по ID",
    description="Возвращает данные расчёта зарплаты. Возвращает 404 если не найден.",
    responses={**_auth, **_404},
)
def get_salary(
    salary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
):
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise NotFoundException("Расчет зарплаты не найден")
    return salary


@router.post(
    "/calculate",
    response_model=SalarySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Рассчитать зарплату",
    description=(
        "Расчёт зарплаты сотрудника за период. Учитываются базовая ставка, "
        "выполненные заказы (бонус) и штрафы. "
        "Возвращает 400 если сотрудник не найден или период некорректен."
    ),
    responses={**_auth, 400: {"model": ErrorResponse, "description": "Некорректные параметры расчёта"}},
)
def calculate_employee_salary(
    salary_calculate: SalaryCalculate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
):
    try:
        salary = calculate_salary(db, salary_calculate)
        return salary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{salary_id}/pay",
    response_model=SalarySchema,
    status_code=status.HTTP_200_OK,
    summary="Отметить зарплату как выплаченную",
    description=(
        "Устанавливает статус PAID и фиксирует дату выплаты. "
        "Автоматически создаёт расходную операцию в кассе (если есть активный счёт). "
        "Опционально принять `account_id` в query-параметре для выбора конкретного счёта."
    ),
    responses={**_auth, **_404},
)
def mark_salary_paid(
    salary_id: int,
    account_id: Optional[int] = Query(None, description="ID кассового счёта для списания"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
):
    from datetime import datetime
    from app.models.salary import SalaryStatus
    from app.models.employee import Employee
    from app.models.cashflow import Account
    from app.services.cashflow_service import record_salary_payment, _calc_account_balance

    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise NotFoundException("Расчет зарплаты не найден")

    # Проверяем баланс выбранного счёта
    if account_id:
        account = db.query(Account).filter(Account.id == account_id, Account.is_active == True).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Счёт не найден")
        balance = _calc_account_balance(db, account)
        if balance < salary.total:
            shortage = salary.total - balance
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточно средств на счёте «{account.name}». Не хватает {shortage:.2f} руб."
            )

    employee = db.query(Employee).filter(Employee.id == salary.employee_id).first()
    employee_name = employee.full_name if employee else f"Сотрудник #{salary.employee_id}"

    salary.status = SalaryStatus.PAID
    salary.paid_at = datetime.utcnow()

    record_salary_payment(
        db,
        salary_id=salary_id,
        amount=salary.total,
        employee_name=employee_name,
        account_id=account_id,
    )

    db.commit()
    db.refresh(salary)
    return salary


@router.get(
    "/scheme/{employee_id}",
    response_model=SalarySchemeResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить схему зарплаты сотрудника",
    responses={**_auth, **_404},
)
def get_employee_salary_scheme(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
):
    return get_salary_scheme(db, employee_id)


@router.put(
    "/scheme/{employee_id}",
    response_model=SalarySchemeResponse,
    status_code=status.HTTP_200_OK,
    summary="Сохранить схему зарплаты сотрудника",
    responses={**_auth, **_404},
)
def set_employee_salary_scheme(
    employee_id: int,
    data: SalarySchemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant_or_admin),
):
    return update_salary_scheme(db, employee_id, data)
