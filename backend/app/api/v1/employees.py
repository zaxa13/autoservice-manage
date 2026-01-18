from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Annotated
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.employee import Employee, EmployeePosition
from app.schemas.employee import Employee as EmployeeSchema, EmployeeCreate, EmployeeUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_admin

router = APIRouter()


# Словарь переводов должностей сотрудников
EMPLOYEE_POSITION_NAMES = {
    EmployeePosition.ADMIN: "Администратор",
    EmployeePosition.MANAGER: "Менеджер",
    EmployeePosition.MECHANIC: "Механик",
}

# Словарь переводов ролей пользователей
USER_ROLE_NAMES = {
    UserRole.ADMIN: "Администратор",
    UserRole.MANAGER: "Менеджер",
    UserRole.MECHANIC: "Механик",
    UserRole.ACCOUNTANT: "Бухгалтер",
}


@router.get("/positions")
def get_employee_positions():
    """Получение списка возможных должностей сотрудников с переводами"""
    return [
        {"value": position.value, "label": EMPLOYEE_POSITION_NAMES.get(position, position.value)}
        for position in EmployeePosition
    ]


@router.get("/user-roles")
def get_user_roles():
    """Получение списка возможных ролей пользователей с переводами"""
    return [
        {"value": role.value, "label": USER_ROLE_NAMES.get(role, role.value)}
        for role in UserRole
    ]


@router.get("/", response_model=List[EmployeeSchema])
def get_employees(
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получение списка сотрудников"""
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


@router.get("/{employee_id}", response_model=EmployeeSchema)
def get_employee(
    employee_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Получение сотрудника по ID"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")
    return employee


@router.post("/", response_model=EmployeeSchema)
def create_employee(
    employee_create: EmployeeCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db)
):
    """Создание сотрудника с автоматическим созданием пользователя"""
    # Создаем сотрудника
    employee = Employee(**employee_create.dict(exclude={"username", "password", "user_role"}))
    db.add(employee)
    db.flush()  # Получаем ID сотрудника без коммита
    
    # Если указаны данные для создания пользователя, создаем его
    if employee_create.username and employee_create.password and employee_create.user_role:
        from app.schemas.user import UserCreate
        from app.core.security import get_password_hash
        
        # Проверяем, что username и email уникальны
        existing_user = db.query(User).filter(
            (User.username == employee_create.username) | 
            (User.email == employee_create.email)
        ).first()
        
        if existing_user:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином или email уже существует"
            )
        
        # Создаем пользователя
        user = User(
            username=employee_create.username,
            email=employee_create.email if employee_create.email else f"{employee_create.username}@autoservice.local",
            password_hash=get_password_hash(employee_create.password),
            role=employee_create.user_role,
            employee_id=employee.id
        )
        db.add(user)
    
    db.commit()
    db.refresh(employee)
    return employee


@router.put("/{employee_id}", response_model=EmployeeSchema)
def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db)
):
    """Обновление сотрудника"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise NotFoundException("Сотрудник не найден")
    
    update_data = employee_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    db.commit()
    db.refresh(employee)
    return employee

