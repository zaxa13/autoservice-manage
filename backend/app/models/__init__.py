"""Re-export всех моделей tenant-приложения."""
from app.models._base import Base, TenantMixin
from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_post import AppointmentPost
from app.models.cashflow import (
    Account,
    AccountType,
    CashTransaction,
    CashflowTransactionType,
    TransactionCategory,
)
from app.models.customer import Customer
from app.models.employee import Employee, EmployeePosition
from app.models.integration import IntegrationLog, IntegrationType
from app.models.order import Order, OrderPart, OrderStatus, OrderWork
from app.models.part import Part, PartCategory
from app.models.part_brand import PartBrand
from app.models.password_reset import PasswordResetToken
from app.models.payment import Payment, PaymentLog, PaymentMethod, PaymentStatus
from app.models.salary import Salary, SalaryScheme, SalaryStatus
from app.models.setting import Setting
from app.models.supplier import Supplier
from app.models.tenant_counter import TenantCounter
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.models.warehouse import (
    ReceiptDocument,
    ReceiptLine,
    ReceiptStatus,
    TransactionType,
    WarehouseItem,
    WarehouseTransaction,
)
from app.models.work import Work, WorkCategory

__all__ = [
    "Base",
    "TenantMixin",
    "Account",
    "AccountType",
    "Appointment",
    "AppointmentPost",
    "AppointmentStatus",
    "CashTransaction",
    "CashflowTransactionType",
    "Customer",
    "Employee",
    "EmployeePosition",
    "IntegrationLog",
    "IntegrationType",
    "Order",
    "OrderPart",
    "OrderStatus",
    "OrderWork",
    "Part",
    "PartBrand",
    "PartCategory",
    "PasswordResetToken",
    "Payment",
    "PaymentLog",
    "PaymentMethod",
    "PaymentStatus",
    "ReceiptDocument",
    "ReceiptLine",
    "ReceiptStatus",
    "Salary",
    "SalaryScheme",
    "SalaryStatus",
    "Setting",
    "Supplier",
    "TenantCounter",
    "TransactionCategory",
    "TransactionType",
    "User",
    "UserRole",
    "Vehicle",
    "VehicleBrand",
    "VehicleModel",
    "WarehouseItem",
    "WarehouseTransaction",
    "Work",
    "WorkCategory",
]
