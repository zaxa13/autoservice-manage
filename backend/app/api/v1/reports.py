from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.reports import (
    RevenueReportResponse,
    MechanicsReportResponse,
    OrdersReportResponse,
    PartsReportResponse,
)
from app.schemas.responses import ErrorResponse
from app.services.report_service import (
    get_revenue_report,
    get_mechanics_report,
    get_orders_report,
    get_parts_report,
)

router = APIRouter()


@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    status_code=200,
    summary="Отчёт по выручке",
    description=(
        "Детальный отчёт по выручке за выбранный период. "
        "Включает: итоговую выручку, средний чек, количество заказов, "
        "динамику по дням, разбивку по категориям работ и методам оплаты. "
        "Максимальный период — 366 дней."
    ),
    tags=["Отчёты"],
    responses={
        400: {"model": ErrorResponse, "description": "Некорректный диапазон дат"},
        401: {"model": ErrorResponse, "description": "Не авторизован"},
    },
)
def revenue_report(
    date_from: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RevenueReportResponse:
    return get_revenue_report(db, date_from, date_to)


@router.get(
    "/mechanics",
    response_model=MechanicsReportResponse,
    status_code=200,
    summary="Отчёт по механикам",
    description=(
        "Производительность механиков за выбранный период: "
        "количество выполненных заказов, выручка, средний чек, "
        "количество работ и начисленная зарплата (если есть расчёт за период). "
        "Максимальный период — 366 дней."
    ),
    tags=["Отчёты"],
    responses={
        400: {"model": ErrorResponse, "description": "Некорректный диапазон дат"},
        401: {"model": ErrorResponse, "description": "Не авторизован"},
    },
)
def mechanics_report(
    date_from: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MechanicsReportResponse:
    return get_mechanics_report(db, date_from, date_to)


@router.get(
    "/orders",
    response_model=OrdersReportResponse,
    status_code=200,
    summary="Отчёт по заказ-нарядам",
    description=(
        "Список заказ-нарядов за период с агрегатными показателями: "
        "общее количество, сумма, оплачено, разбивка по статусам. "
        "Поддерживает фильтрацию по статусу. "
        "Максимальный период — 366 дней."
    ),
    tags=["Отчёты"],
    responses={
        400: {"model": ErrorResponse, "description": "Некорректный диапазон дат"},
        401: {"model": ErrorResponse, "description": "Не авторизован"},
    },
)
def orders_report(
    date_from: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    status: Optional[str] = Query(
        None,
        pattern="^(new|estimation|in_progress|ready_for_payment|paid|completed|cancelled)$",
        description="Фильтр по статусу заказа",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrdersReportResponse:
    return get_orders_report(db, date_from, date_to, status)


@router.get(
    "/parts",
    response_model=PartsReportResponse,
    status_code=200,
    summary="Отчёт по запчастям",
    description=(
        "Статистика использования запчастей за период: "
        "топ запчастей по выручке и количеству, суммарные показатели. "
        "Также содержит список позиций с остатком ниже минимума (независимо от периода). "
        "Максимальный период — 366 дней."
    ),
    tags=["Отчёты"],
    responses={
        400: {"model": ErrorResponse, "description": "Некорректный диапазон дат"},
        401: {"model": ErrorResponse, "description": "Не авторизован"},
    },
)
def parts_report(
    date_from: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PartsReportResponse:
    return get_parts_report(db, date_from, date_to)
