from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.schemas.vehicle_brand import (
    BrandsImport,
    BrandsListResponse,
    ModelsRequest,
    ModelsResponse,
)
from app.schemas.responses import BrandsImportResponse, ErrorResponse
from app.core.permissions import require_manager_or_admin

router = APIRouter()

_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.post(
    "/import",
    response_model=BrandsImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Импорт марок и моделей",
    description=(
        "Полная замена справочника марок и моделей данными из запроса. "
        "Все существующие марки и модели удаляются. "
        "Доступно менеджеру и администратору."
    ),
    responses=_write,
)
def import_brands(
    data: BrandsImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    db.query(VehicleModel).delete()
    db.query(VehicleBrand).delete()
    db.commit()

    for brand_input in data.brands:
        brand = VehicleBrand(name=brand_input.name)
        db.add(brand)
        db.flush()

        for model_name in brand_input.models:
            model = VehicleModel(brand_id=brand.id, name=model_name)
            db.add(model)

    db.commit()
    return {"message": "Данные успешно импортированы", "brands_count": len(data.brands)}


@router.get(
    "/",
    response_model=BrandsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Список марок",
    description="Возвращает все марки автомобилей, отсортированные по алфавиту.",
    responses=_auth,
)
def get_brands(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    brands = db.query(VehicleBrand).order_by(VehicleBrand.name).all()
    return BrandsListResponse(brands=[{"id": b.id, "name": b.name} for b in brands])


@router.post(
    "/models",
    response_model=ModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="Модели по марке",
    description=(
        "Возвращает список моделей для указанной марки. "
        "Можно передать `brand_id` (приоритет) или `brand` (поиск по названию без учёта регистра). "
        "Возвращает 400 если не передан ни один параметр, 404 если марка не найдена."
    ),
    responses={
        **_auth,
        400: {"model": ErrorResponse, "description": "Не указан brand или brand_id"},
        404: {"model": ErrorResponse, "description": "Марка не найдена"},
    },
)
def get_models_by_brand(
    request: ModelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.brand_id is not None:
        brand = db.query(VehicleBrand).filter(VehicleBrand.id == request.brand_id).first()
    elif request.brand and request.brand.strip():
        brand = (
            db.query(VehicleBrand)
            .filter(VehicleBrand.name.ilike(request.brand.strip()))
            .first()
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите brand или brand_id",
        )
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Марка не найдена",
        )
    return ModelsResponse(models=[{"id": m.id, "name": m.name} for m in brand.models])
