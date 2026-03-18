from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.setting import Setting
from app.schemas.responses import RevenuePlanResponse, ErrorResponse

router = APIRouter()


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администратора",
        )
    return current_user


class RevenuePlanIn(BaseModel):
    year: int = Field(..., ge=2020, le=2099, description="Год")
    month: int = Field(..., ge=1, le=12, description="Месяц (1-12)")
    amount: float = Field(..., ge=0, description="Сумма плана выручки")


@router.get(
    "/revenue-plan",
    response_model=RevenuePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить план выручки",
    description=(
        "Возвращает план выручки на указанный месяц. "
        "Если план не задан — `amount` будет `null`."
    ),
    responses={401: {"model": ErrorResponse, "description": "Не авторизован"}},
)
def get_revenue_plan(
    year: int = Query(..., ge=2020, le=2099, description="Год"),
    month: int = Query(..., ge=1, le=12, description="Месяц (1-12)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = f"revenue_plan_{year}_{month:02d}"
    row = db.query(Setting).filter(Setting.key == key).first()
    return {"year": year, "month": month, "amount": float(row.value) if row else None}


@router.put(
    "/revenue-plan",
    response_model=RevenuePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Установить план выручки",
    description="Устанавливает или обновляет план выручки на месяц. Только администратор.",
    responses={
        401: {"model": ErrorResponse, "description": "Не авторизован"},
        403: {"model": ErrorResponse, "description": "Только для администратора"},
    },
)
def set_revenue_plan(
    body: RevenuePlanIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    key = f"revenue_plan_{body.year}_{body.month:02d}"
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = str(body.amount)
    else:
        db.add(Setting(key=key, value=str(body.amount)))
    db.commit()
    return {"year": body.year, "month": body.month, "amount": body.amount}
