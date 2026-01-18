from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.schemas.order import Order as OrderSchema, OrderCreate, OrderUpdate, OrderDetail
from app.services.order_service import create_order, update_order, complete_order
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException

router = APIRouter()


class OrderStatusInfo(BaseModel):
    value: str
    label: str


@router.get("/statuses", response_model=List[OrderStatusInfo])
def get_order_statuses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка доступных статусов заказ-нарядов"""
    # Исключаем COMPLETED из списка - он устанавливается только через кнопку "завершить"
    statuses = [
        OrderStatusInfo(value=OrderStatus.NEW.value, label="Новый"),
        OrderStatusInfo(value=OrderStatus.ESTIMATION.value, label="Проценка"),
        OrderStatusInfo(value=OrderStatus.IN_PROGRESS.value, label="В работе"),
        OrderStatusInfo(value=OrderStatus.READY_FOR_PAYMENT.value, label="Готов к оплате"),
        OrderStatusInfo(value=OrderStatus.PAID.value, label="Оплачен"),
        OrderStatusInfo(value=OrderStatus.CANCELLED.value, label="Отменен"),
    ]
    return statuses


@router.get("/", response_model=List[OrderSchema])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[OrderStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка заказ-нарядов"""
    from sqlalchemy.orm import joinedload
    from app.models.vehicle import Vehicle
    
    query = db.query(Order).options(
        joinedload(Order.vehicle).joinedload(Vehicle.customer),
        joinedload(Order.mechanic)
    )
    
    # Механик видит только свои заказ-наряды
    if current_user.role == UserRole.MECHANIC:
        query = query.filter(Order.mechanic_id == current_user.employee_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение заказ-наряда по ID"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    
    # Проверка прав доступа для механика
    if current_user.role == UserRole.MECHANIC:
        if order.mechanic_id != current_user.employee_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому заказ-наряду"
            )
    
    return order


@router.post("/", response_model=OrderSchema)
def create_new_order(
    order_create: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание нового заказ-наряда"""
    # Для администраторов employee_id может быть не задан
    # В этом случае пытаемся найти или создать системного сотрудника-администратора
    employee_id = current_user.employee_id
    
    if not employee_id and current_user.role == UserRole.ADMIN:
        # Ищем системного сотрудника-администратора
        from app.models.employee import Employee, EmployeePosition
        system_admin = db.query(Employee).filter(
            Employee.position == EmployeePosition.ADMIN,
            Employee.is_active == True
        ).first()
        
        if system_admin:
            employee_id = system_admin.id
        else:
            # Если нет ни одного администратора-сотрудника, берем первого активного сотрудника
            first_employee = db.query(Employee).filter(Employee.is_active == True).first()
            if first_employee:
                employee_id = first_employee.id
            else:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не найдено активных сотрудников в системе. Создайте хотя бы одного сотрудника."
                )
    elif not employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    
    order = create_order(db, order_create, employee_id)
    return order


@router.put("/{order_id}", response_model=OrderSchema)
def update_existing_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление заказ-наряда"""
    order = update_order(db, order_id, order_update)
    return order


@router.post("/{order_id}/complete", response_model=OrderSchema)
def complete_existing_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Завершение заказ-наряда"""
    # Для администраторов employee_id может быть не задан
    # В этом случае пытаемся найти системного сотрудника-администратора
    employee_id = current_user.employee_id
    
    if not employee_id and current_user.role == UserRole.ADMIN:
        # Ищем системного сотрудника-администратора
        from app.models.employee import Employee, EmployeePosition
        system_admin = db.query(Employee).filter(
            Employee.position == EmployeePosition.ADMIN,
            Employee.is_active == True
        ).first()
        
        if system_admin:
            employee_id = system_admin.id
        else:
            # Если нет ни одного администратора-сотрудника, берем первого активного сотрудника
            first_employee = db.query(Employee).filter(Employee.is_active == True).first()
            if first_employee:
                employee_id = first_employee.id
            else:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не найдено активных сотрудников в системе. Создайте хотя бы одного сотрудника."
                )
    elif not employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник"
        )
    
    order = complete_order(db, order_id, employee_id)
    return order


@router.post("/{order_id}/cancel", response_model=OrderSchema)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Отмена заказ-наряда"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order

