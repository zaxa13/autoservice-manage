from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

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
from app.core.permissions import require_manager_or_admin

router = APIRouter()


@router.post("/import")
def import_brands(
    data: BrandsImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """
    Импорт марок и моделей автомобилей.
    Заменяет все существующие данные новыми из запроса.
    """
    # Удаляем существующие данные (CASCADE удалит и модели)
    db.query(VehicleModel).delete()
    db.query(VehicleBrand).delete()
    db.commit()

    for brand_input in data.brands:
        brand = VehicleBrand(name=brand_input.name)
        db.add(brand)
        db.flush()  # Получаем id для brand

        for model_name in brand_input.models:
            model = VehicleModel(brand_id=brand.id, name=model_name)
            db.add(model)

    db.commit()
    return {"message": "Данные успешно импортированы", "brands_count": len(data.brands)}


@router.get("/", response_model=BrandsListResponse)
def get_brands(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получение списка всех марок автомобилей с id"""
    brands = db.query(VehicleBrand).order_by(VehicleBrand.name).all()
    return BrandsListResponse(brands=[{"id": b.id, "name": b.name} for b in brands])


@router.post("/models", response_model=ModelsResponse)
def get_models_by_brand(
    request: ModelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получение списка моделей по марке (id или название).
    Поиск по названию выполняется без учёта регистра.
    """
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
            detail=f"Марка не найдена",
        )
    return ModelsResponse(models=[{"id": m.id, "name": m.name} for m in brand.models])
