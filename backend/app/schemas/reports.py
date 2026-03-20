from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


# ── Shared ────────────────────────────────────────────────────────────────────

class DateRangeParams(BaseModel):
    date_from: date = Field(..., description="Начало периода (включительно)")
    date_to: date = Field(..., description="Конец периода (включительно)")


# ── Revenue Report ────────────────────────────────────────────────────────────

class RevenueByDayItem(BaseModel):
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    revenue: float = Field(..., description="Выручка за день (оплаченные платежи)")
    orders_count: int = Field(..., description="Количество заказ-нарядов, оплаченных в этот день")


class RevenueByWorkCategoryItem(BaseModel):
    category: str = Field(..., description="Категория работ (ключ enum)")
    category_label: str = Field(..., description="Человекочитаемое название категории")
    revenue: float = Field(..., description="Выручка по категории")
    orders_count: int = Field(..., description="Количество заказ-нарядов с работами этой категории")


class RevenueByPaymentMethodItem(BaseModel):
    method: str = Field(..., description="Метод оплаты (cash, card, yookassa)")
    method_label: str = Field(..., description="Человекочитаемое название метода")
    amount: float = Field(..., description="Сумма платежей данным методом")
    payments_count: int = Field(..., description="Количество платежей")


class RevenueReportResponse(BaseModel):
    date_from: str = Field(..., description="Начало периода")
    date_to: str = Field(..., description="Конец периода")
    total_revenue: float = Field(..., description="Итоговая выручка за период")
    total_orders: int = Field(..., description="Всего заказ-нарядов (оплаченных/завершённых)")
    avg_check: float = Field(..., description="Средний чек")
    by_day: List[RevenueByDayItem] = Field(default_factory=list, description="Выручка по дням")
    by_work_category: List[RevenueByWorkCategoryItem] = Field(
        default_factory=list, description="Выручка по категориям работ"
    )
    by_payment_method: List[RevenueByPaymentMethodItem] = Field(
        default_factory=list, description="Выручка по методам оплаты"
    )


# ── Mechanics Report ──────────────────────────────────────────────────────────

class MechanicReportItem(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника")
    full_name: str = Field(..., description="ФИО механика")
    orders_completed: int = Field(..., description="Завершённых заказ-нарядов за период")
    orders_in_progress: int = Field(..., description="Заказов в работе на конец периода")
    revenue: float = Field(..., description="Выручка по заказам механика")
    avg_check: float = Field(..., description="Средний чек")
    works_count: int = Field(..., description="Количество выполненных работ (позиций)")
    salary_total: Optional[float] = Field(None, description="Начисленная зарплата за период (если есть)")


class MechanicsReportResponse(BaseModel):
    date_from: str = Field(..., description="Начало периода")
    date_to: str = Field(..., description="Конец периода")
    mechanics: List[MechanicReportItem] = Field(default_factory=list, description="Список механиков с показателями")
    team_total_revenue: float = Field(..., description="Суммарная выручка команды")
    team_total_orders: int = Field(..., description="Суммарное количество заказов")
    team_avg_check: float = Field(..., description="Средний чек по команде")


# ── Orders Report ─────────────────────────────────────────────────────────────

class OrderReportItem(BaseModel):
    id: int = Field(..., description="ID заказ-наряда")
    number: str = Field(..., description="Номер заказ-наряда")
    status: str = Field(..., description="Статус заказ-наряда")
    status_label: str = Field(..., description="Человекочитаемый статус")
    created_at: str = Field(..., description="Дата создания")
    completed_at: Optional[str] = Field(None, description="Дата завершения")
    customer_name: Optional[str] = Field(None, description="Имя клиента")
    vehicle_info: Optional[str] = Field(None, description="Информация об автомобиле (марка, модель, гос. номер)")
    mechanic_name: Optional[str] = Field(None, description="ФИО механика")
    total_amount: float = Field(..., description="Сумма заказа")
    paid_amount: float = Field(..., description="Оплачено")
    works_total: float = Field(..., description="Сумма работ")
    parts_total: float = Field(..., description="Сумма запчастей")


class OrdersReportResponse(BaseModel):
    date_from: str = Field(..., description="Начало периода")
    date_to: str = Field(..., description="Конец периода")
    total_count: int = Field(..., description="Общее количество заказ-нарядов")
    total_amount: float = Field(..., description="Общая сумма")
    total_paid: float = Field(..., description="Итого оплачено")
    by_status: List[dict] = Field(default_factory=list, description="Количество заказов по статусам")
    orders: List[OrderReportItem] = Field(default_factory=list, description="Список заказ-нарядов")


# ── Parts Report ──────────────────────────────────────────────────────────────

class PartUsageItem(BaseModel):
    part_id: int = Field(..., description="ID запчасти")
    part_name: str = Field(..., description="Название запчасти")
    part_number: str = Field(..., description="Артикул")
    category: str = Field(..., description="Категория")
    category_label: str = Field(..., description="Категория (текст)")
    total_quantity: float = Field(..., description="Суммарное количество использованных")
    total_revenue: float = Field(..., description="Суммарная выручка (цена продажи × кол-во)")
    total_cost: float = Field(0, description="Суммарная себестоимость (закупочная цена × кол-во)")
    total_margin: float = Field(0, description="Суммарная маржа (выручка − себестоимость)")
    margin_pct: float = Field(0, description="Маржинальность в % от выручки")
    orders_count: int = Field(..., description="Количество заказ-нарядов, где использовалась")
    current_stock: float = Field(..., description="Текущий остаток на складе")


class PartsReportResponse(BaseModel):
    date_from: str = Field(..., description="Начало периода")
    date_to: str = Field(..., description="Конец периода")
    total_parts_revenue: float = Field(..., description="Общая сумма продаж запчастей")
    total_quantity_sold: float = Field(..., description="Суммарное количество реализованных запчастей")
    total_parts_cost: float = Field(0, description="Общая себестоимость проданных запчастей")
    total_parts_margin: float = Field(0, description="Общая маржа по запчастям")
    total_margin_pct: float = Field(0, description="Маржинальность в % от общей суммы продаж")
    top_parts: List[PartUsageItem] = Field(default_factory=list, description="Топ запчастей по выручке")
    low_stock_parts: List[PartUsageItem] = Field(
        default_factory=list, description="Запчасти с остатком ниже минимума"
    )
