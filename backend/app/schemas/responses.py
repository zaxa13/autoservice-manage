from pydantic import BaseModel, Field
from typing import Optional, List, Any
from decimal import Decimal


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str = Field(..., description="Сообщение о результате операции")


class TokenResponse(BaseModel):
    """JWT token response returned on successful login."""
    access_token: str = Field(..., description="JWT access-токен для авторизации")
    token_type: str = Field(default="bearer", description="Тип токена (всегда bearer)")


class ChangePasswordResponse(BaseModel):
    """Response for password change endpoint."""
    message: str = Field(..., description="Сообщение об успешной смене пароля")
    user: Any = Field(None, description="Данные обновлённого пользователя")


class LabelValueItem(BaseModel):
    """Key-value pair for enum-like lookups (positions, roles, statuses)."""
    value: str = Field(..., description="Программное значение (enum)")
    label: str = Field(..., description="Человекочитаемое название")


class BrandsImportResponse(BaseModel):
    """Response after importing vehicle brands."""
    message: str = Field(..., description="Сообщение о результате импорта")
    brands_count: int = Field(..., description="Количество импортированных марок")


class RevenuePlanResponse(BaseModel):
    """Revenue plan for a specific month."""
    year: int = Field(..., description="Год")
    month: int = Field(..., description="Месяц (1-12)")
    amount: Optional[float] = Field(None, description="Сумма плана выручки (null если не задан)")


# ── YooKassa ──────────────────────────────────────────────────────────────────

class YooKassaPaymentResponse(BaseModel):
    """Response after creating a YooKassa payment."""
    payment_id: int = Field(..., description="ID платежа в системе")
    yookassa_payment_id: Optional[str] = Field(None, description="ID платежа в YooKassa")
    confirmation_url: Optional[str] = Field(None, description="URL для перенаправления клиента на оплату")


class WebhookResponse(BaseModel):
    """Generic webhook processing response."""
    status: str = Field(..., description="Статус обработки (ok / error)")
    message: Optional[str] = Field(None, description="Детали (при ошибке)")


# ── Integrations ──────────────────────────────────────────────────────────────

class IntegrationResponse(BaseModel):
    """Generic response wrapper for external API integrations."""
    data: Optional[Any] = Field(None, description="Данные от внешнего API")
    error: Optional[str] = Field(None, description="Сообщение об ошибке (если есть)")


class SupplierOrderRequest(BaseModel):
    """Request to create an order with an external parts supplier."""
    supplier_id: str = Field(..., description="ID поставщика во внешней системе")
    parts: List[dict] = Field(..., description="Список запчастей для заказа")
    delivery_address: Optional[str] = Field(None, description="Адрес доставки")
    comment: Optional[str] = Field(None, description="Комментарий к заказу")


class PartsSearchResponse(BaseModel):
    """Parts search results from external suppliers."""
    results: List[Any] = Field(default_factory=list, description="Найденные запчасти")
    error: Optional[str] = Field(None, description="Сообщение об ошибке (если есть)")


# ── Dashboard ─────────────────────────────────────────────────────────────────

class RevenueMetric(BaseModel):
    value: float = Field(..., description="Выручка за текущий период")
    prev_value: float = Field(..., description="Выручка за предыдущий период")
    change_pct: Optional[float] = Field(None, description="Изменение в процентах")
    plan: Optional[float] = Field(None, description="План выручки на период")
    plan_pct: Optional[float] = Field(None, description="Процент выполнения плана")


class AvgCheckMetric(BaseModel):
    value: float = Field(..., description="Средний чек за текущий период")
    prev_value: float = Field(..., description="Средний чек за предыдущий период")
    change_pct: Optional[float] = Field(None, description="Изменение в процентах")


class OrdersCountMetric(BaseModel):
    value: int = Field(..., description="Количество заказов за текущий период")
    prev_value: int = Field(..., description="Количество заказов за предыдущий период")
    change_pct: Optional[float] = Field(None, description="Изменение в процентах")


class PipelineDayItem(BaseModel):
    date: str = Field(..., description="Дата в формате ISO")
    day_name: str = Field(..., description="Короткое название дня недели (Пн, Вт, ...)")
    day_label: str = Field(..., description="Дата с названием месяца (5 марта)")
    appointments_count: int = Field(..., description="Количество записей")
    load_pct: Optional[int] = Field(None, description="Загрузка постов в процентах")
    is_today: bool = Field(..., description="Является ли день сегодняшним")


class StuckOrderItem(BaseModel):
    id: int = Field(..., description="ID заказ-наряда")
    number: str = Field(..., description="Номер заказ-наряда")
    mechanic_name: Optional[str] = Field(None, description="ФИО механика")
    days_in_work: int = Field(..., description="Дней в работе")


class AlertsInfo(BaseModel):
    unpaid_orders_count: int = Field(..., description="Кол-во неоплаченных заказов")
    unpaid_orders_sum: float = Field(..., description="Сумма неоплаченных заказов")
    stuck_orders: List[StuckOrderItem] = Field(default_factory=list, description="Зависшие заказы (>2 дней в работе)")
    orders_without_mechanic_count: int = Field(..., description="Заказы без назначенного механика")
    no_shows_today: int = Field(..., description="Неявки сегодня")
    no_shows_pct: int = Field(..., description="Процент неявок сегодня")


class RevenueChartPoint(BaseModel):
    label: str = Field(..., description="Подпись точки на графике")
    date: str = Field(..., description="Дата в формате ISO")
    current: float = Field(..., description="Значение текущего периода")
    previous: float = Field(..., description="Значение предыдущего периода")
    is_today: bool = Field(False, description="Является ли точка сегодняшней")
    is_future: bool = Field(False, description="Является ли точка будущей датой")


class MechanicStatItem(BaseModel):
    id: int = Field(..., description="ID сотрудника-механика")
    name: str = Field(..., description="ФИО механика")
    orders_count: int = Field(..., description="Количество заказов за период")
    revenue: float = Field(..., description="Выручка за период")
    avg_check: float = Field(..., description="Средний чек")
    vs_team_pct: Optional[float] = Field(None, description="Отклонение от среднего чека по команде (%)")


class DashboardStatsResponse(BaseModel):
    """Full dashboard statistics response."""
    period: str = Field(..., description="Тип периода (day, week, month, quarter, year, custom)")
    period_label: str = Field(..., description="Человекочитаемое название периода")
    nav_ref: str = Field(..., description="Опорная дата навигации (ISO)")
    can_go_next: bool = Field(..., description="Можно ли перейти к следующему периоду")
    revenue: RevenueMetric = Field(..., description="Метрика выручки")
    avg_check: AvgCheckMetric = Field(..., description="Метрика среднего чека")
    orders_count: OrdersCountMetric = Field(..., description="Метрика количества заказов")
    wip_amount: float = Field(..., description="Сумма заказов в работе")
    post_load_today_pct: Optional[int] = Field(None, description="Загрузка постов сегодня (%)")
    post_load_tomorrow_pct: Optional[int] = Field(None, description="Загрузка постов завтра (%)")
    pipeline_7d: List[PipelineDayItem] = Field(..., description="Загрузка по дням на 7 дней вперёд")
    revenue_chart: List[RevenueChartPoint] = Field(..., description="Данные графика выручки")
    mechanics_stats: List[MechanicStatItem] = Field(default_factory=list, description="Статистика по механикам")
    alerts: AlertsInfo = Field(..., description="Уведомления и проблемы")


# ── Error schemas (for OpenAPI responses docs) ───────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response body."""
    detail: str = Field(..., description="Описание ошибки")
