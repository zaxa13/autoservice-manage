from app.schemas.user import User, UserCreate, UserUpdate, UserInDB, Token
from app.schemas.employee import Employee, EmployeeCreate, EmployeeUpdate
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate
from app.schemas.vehicle import Vehicle, VehicleCreate, VehicleUpdate
from app.schemas.work import Work, WorkCreate, WorkUpdate
from app.schemas.part import Part, PartCreate, PartUpdate
from app.schemas.order import (
    Order, OrderCreate, OrderUpdate, OrderWorkCreate, OrderPartCreate,
    OrderDetail, OrderWork, OrderPart
)
from app.schemas.warehouse import (
    WarehouseItem, WarehouseItemCreate, WarehouseItemUpdate,
    WarehouseTransaction, WarehouseTransactionCreate
)
from app.schemas.salary import Salary, SalaryCreate, SalaryUpdate, SalaryCalculate
from app.schemas.payment import Payment, PaymentCreate, PaymentYooKassaCreate
from app.schemas.appointment import Appointment, AppointmentCreate, AppointmentUpdate

__all__ = [
    "User", "UserCreate", "UserUpdate", "UserInDB", "Token",
    "Employee", "EmployeeCreate", "EmployeeUpdate",
    "Customer", "CustomerCreate", "CustomerUpdate",
    "Vehicle", "VehicleCreate", "VehicleUpdate",
    "Work", "WorkCreate", "WorkUpdate",
    "Part", "PartCreate", "PartUpdate",
    "Order", "OrderCreate", "OrderUpdate", "OrderWorkCreate", "OrderPartCreate",
    "OrderDetail", "OrderWork", "OrderPart",
    "WarehouseItem", "WarehouseItemCreate", "WarehouseItemUpdate",
    "WarehouseTransaction", "WarehouseTransactionCreate",
    "Salary", "SalaryCreate", "SalaryUpdate", "SalaryCalculate",
    "Payment", "PaymentCreate", "PaymentYooKassaCreate",
    "Appointment", "AppointmentCreate", "AppointmentUpdate",
]

