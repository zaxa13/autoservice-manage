from sqlalchemy.orm import Session
from datetime import date
from fastapi import HTTPException, status

from app.repositories.report_repository import (
    get_revenue_report_data,
    get_mechanics_report_data,
    get_orders_report_data,
    get_parts_report_data,
)
from app.schemas.reports import (
    RevenueReportResponse,
    MechanicsReportResponse,
    OrdersReportResponse,
    PartsReportResponse,
)

_MAX_REPORT_DAYS = 366


def _validate_date_range(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from не может быть позже date_to",
        )
    if (date_to - date_from).days > _MAX_REPORT_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Период отчёта не может превышать {_MAX_REPORT_DAYS} дней",
        )


def get_revenue_report(db: Session, date_from: date, date_to: date) -> RevenueReportResponse:
    _validate_date_range(date_from, date_to)
    data = get_revenue_report_data(db, date_from, date_to)
    return RevenueReportResponse(**data)


def get_mechanics_report(db: Session, date_from: date, date_to: date) -> MechanicsReportResponse:
    _validate_date_range(date_from, date_to)
    data = get_mechanics_report_data(db, date_from, date_to)
    return MechanicsReportResponse(**data)


def get_orders_report(
    db: Session,
    date_from: date,
    date_to: date,
    status_filter: str | None = None,
) -> OrdersReportResponse:
    _validate_date_range(date_from, date_to)
    data = get_orders_report_data(db, date_from, date_to, status_filter)
    return OrdersReportResponse(**data)


def get_parts_report(db: Session, date_from: date, date_to: date) -> PartsReportResponse:
    _validate_date_range(date_from, date_to)
    data = get_parts_report_data(db, date_from, date_to)
    return PartsReportResponse(**data)
