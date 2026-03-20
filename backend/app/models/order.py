from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, DateTime, Date, TypeDecorator
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base
from app.config import settings


class OrderStatus(str, enum.Enum):
    NEW = "new"  # Новый
    ESTIMATION = "estimation"  # Проценка
    IN_PROGRESS = "in_progress"  # В работе
    READY_FOR_PAYMENT = "ready_for_payment"  # Готов к оплате
    PAID = "paid"  # Оплачен
    COMPLETED = "completed"  # Завершен
    CANCELLED = "cancelled"  # Отменен


class OrderStatusType(TypeDecorator):
    """TypeDecorator для корректной работы с OrderStatus в SQLite"""
    impl = String
    cache_ok = True

    def __init__(self, length=50):
        super().__init__(length)

    def process_bind_param(self, value, dialect):
        """Конвертация Python enum в строку для сохранения в БД"""
        if value is None:
            return None
        if isinstance(value, OrderStatus):
            return value.value  # Возвращаем значение enum (нижний регистр)
        return str(value)

    def process_result_value(self, value, dialect):
        """Конвертация строки из БД в Python enum"""
        if value is None:
            return None
        # Маппинг старых значений в верхнем регистре на новые enum значения
        old_to_new = {
            'NEW': 'new',
            'IN_PROGRESS': 'in_progress',
            'COMPLETED': 'completed',  # COMPLETED теперь мапим на completed (новый статус "завершен")
            'READY_FOR_PAYMENT': 'ready_for_payment',
            'ESTIMATION': 'estimation',
            'PAID': 'paid',
            'CANCELLED': 'cancelled',
        }
        # Если значение в верхнем регистре, конвертируем в нижний
        normalized_value = old_to_new.get(value.upper()) if value.upper() in old_to_new else value
        # Конвертируем в enum
        try:
            return OrderStatus(normalized_value)
        except ValueError:
            # Если не получилось, пробуем найти по исходному значению
            return OrderStatus(value.lower()) if hasattr(OrderStatus, value.upper()) else OrderStatus.NEW


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)  # Кто принял заказ
    mechanic_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Кто выполняет
    # Используем кастомный TypeDecorator для корректной работы со статусами в SQLite
    status = Column(
        OrderStatusType(50),
        nullable=False,
        default=OrderStatus.NEW
    )
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)
    mileage_at_service = Column(Integer, nullable=True)
    recommendations = Column(String, nullable=True)  # Рекомендации
    comments = Column(String, nullable=True)  # Комментарии
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    vehicle = relationship("Vehicle", back_populates="orders")
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="orders_created")
    mechanic = relationship("Employee", foreign_keys=[mechanic_id], back_populates="orders_mechanic")
    order_works = relationship("OrderWork", back_populates="order", cascade="all, delete-orphan")
    order_parts = relationship("OrderPart", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")


class OrderWork(Base):
    __tablename__ = "order_works"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)  # Nullable для ручного ввода
    work_name = Column(String, nullable=True)  # Название работы при ручном вводе
    mechanic_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Механик по данной работе
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=True, default=0)  # Скидка в процентах
    total = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="order_works")
    work = relationship("Work")
    mechanic = relationship("Employee", foreign_keys=[mechanic_id])


class OrderPart(Base):
    __tablename__ = "order_parts"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)  # Nullable для ручного ввода
    part_name = Column(String, nullable=True)  # Название запчасти при ручном вводе
    article = Column(String, nullable=True)  # Артикул запчасти
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=True, default=0)  # Скидка в процентах
    total = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="order_parts")
    part = relationship("Part")

