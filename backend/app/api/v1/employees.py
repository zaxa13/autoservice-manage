from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Annotated
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.employee import Employee, EmployeePosition
from app.schemas.employee import Employee as EmployeeSchema, EmployeeCreate, EmployeeUpdate
from app.schemas.responses import LabelValueItem, ErrorResponse
from app.core.exceptions import NotFoundException
from app.core.permissions import require_admin

router = APIRouter()

EMPLOYEE_POSITION_NAMES = {
    EmployeePosition.ADMIN: "Администратор",
    EmployeePosition.MANAGER: "Менеджер",
    EmployeePosition.MECHANIC: "Механик",
}

USER_ROLE_NAMES = {
    UserRole.ADMIN: "Администратор",
    UserRole.MANAGER: "Менеджер",
    UserRole.MECHANIC: "Механик",
    UserRole.ACCOUNTANT: "Бухгалтер",
}

_404 = {404: {"model": ErrorResponse, "description": "Сотрудник не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_admin = {**_auth, 403: {"model": ErrorResponse, "description": "Только для администратора"}}


@router.get(
    "/positions",
    response_model=List[LabelValueItem],
    status_code=status.HTTP_200_OK,
    summary="Должности сотрудников",
    description="Возвращает список возможных должностей сотрудников с русскоязычными названиями.",
)
def get_employee_positions():
    return [
        {"value": position.value, "label": EMPLOYEE_POSITION_NAMES.get(position, position.value)}
        for position in EmployeePosition
    ]


@router.get(
    "/user-roles",
    response_model=List[LabelValueItem],
    status_code=status.HTTP_200_OK,
    summary="Роли пользователей",
    description="Возвращает список возможных ролей пользователей с русскоязычными названиями.",
)
def get_user_roles():
    return [
        {"value": role.value, "label": USER_ROLE_NAMES.get(role, role.value)}
        for role in UserRole
    ]


@router.get(
    "/",
    response_model=List[EmployeeSchema],
    status_code=status.HTTP_200_OK,
    summary="Список сотрудников",
    description="Возвращает список сотрудников с пагинацией. Доступно всем авторизованным пользователям.",
    responses=_auth,
)
def get_employees(
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
):
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


@router.get(
    "/{employee_id}",
    response_model=EmployeeSchema,
    status_code=status.HTTP_200_OK,
    summary="Получить сотрудника по ID",
    description="Возвращает данные сотрудника. Возвращает 404 если сотрудник не найден.",
    responses={**_auth, **_404},
)
def get_employee(
    employee_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")
    return employee


@router.post(
    "/",
    response_model=EmployeeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать сотрудника",
    description=(
        "Создание нового сотрудника. Если переданы `username`, `password` и `user_role` — "
        "автоматически создаётся связанная учётная запись пользователя. "
        "Возвращает 400 при дублировании логина / email. Только администратор."
    ),
    responses={
        **_admin,
        400: {"model": ErrorResponse, "description": "Дубликат логина или email"},
    },
)
def create_employee(
    employee_create: EmployeeCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    employee = Employee(**employee_create.model_dump(exclude={"username", "password", "user_role"}))
    db.add(employee)
    db.flush()

    if employee_create.username and employee_create.password and employee_create.user_role:
        from app.core.security import get_password_hash

        existing_user = db.query(User).filter(
            (User.username == employee_create.username) |
            (User.email == employee_create.email)
        ).first()

        if existing_user:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином или email уже существует",
            )

        user = User(
            username=employee_create.username,
            email=employee_create.email if employee_create.email else f"{employee_create.username}@autoservice.local",
            password_hash=get_password_hash(employee_create.password),
            role=employee_create.user_role,
            employee_id=employee.id,
        )
        db.add(user)

    db.commit()
    db.refresh(employee)
    return employee


@router.put(
    "/{employee_id}",
    response_model=EmployeeSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить сотрудника",
    description="Обновление данных сотрудника. Передавать нужно только изменяемые поля. Только администратор.",
    responses={**_admin, **_404},
)
def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")

    update_data = employee_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee
