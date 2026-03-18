from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.responses import IntegrationResponse, PartsSearchResponse, SupplierOrderRequest, ErrorResponse
from app.core.permissions import require_manager_or_admin
from app.integrations.gibdd import check_vehicle_gibdd
from app.integrations.parts_suppliers import search_parts, create_supplier_order

router = APIRouter()

_write = {
    401: {"model": ErrorResponse, "description": "Не авторизован"},
    403: {"model": ErrorResponse, "description": "Недостаточно прав"},
}


@router.get(
    "/gibdd/vehicle/{vin}",
    response_model=IntegrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Проверка ТС в ГИБДД",
    description=(
        "Проверка транспортного средства по VIN в базе ГИБДД. "
        "Возвращает данные о регистрации, ДТП, розыске и ограничениях. "
        "При ошибке внешнего API в поле `error` возвращается описание проблемы."
    ),
    responses=_write,
)
def get_vehicle_info_gibdd(
    vin: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    result = check_vehicle_gibdd(db, vin)
    if "error" in result:
        return IntegrationResponse(data=None, error=result["error"])
    return IntegrationResponse(data=result, error=None)


@router.get(
    "/suppliers/search",
    response_model=PartsSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Поиск запчастей у поставщиков",
    description=(
        "Поиск запчастей через внешний API поставщиков по артикулу или названию. "
        "Возвращает список найденных позиций с ценами и наличием."
    ),
    responses=_write,
)
def search_parts_suppliers(
    query: str = Query(..., min_length=2, description="Артикул или название запчасти"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    result = search_parts(db, query)
    if "error" in result and "results" not in result:
        return PartsSearchResponse(results=[], error=result["error"])
    return PartsSearchResponse(
        results=result.get("results", []),
        error=result.get("error"),
    )


@router.post(
    "/suppliers/order",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Заказ запчастей у поставщика",
    description=(
        "Создание заказа на запчасти через внешний API поставщиков. "
        "Передаётся ID поставщика, список запчастей и параметры доставки."
    ),
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Ошибка создания заказа"},
    },
)
def create_supplier_order_endpoint(
    supplier_order_data: SupplierOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    result = create_supplier_order(db, supplier_order_data.model_dump())
    if "error" in result:
        return IntegrationResponse(data=None, error=result["error"])
    return IntegrationResponse(data=result, error=None)
