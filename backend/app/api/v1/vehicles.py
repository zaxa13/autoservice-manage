from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.schemas.vehicle import Vehicle as VehicleSchema, VehicleCreate, VehicleUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()


def _vehicle_query(db: Session):
    return db.query(Vehicle).options(
        joinedload(Vehicle.customer),
        joinedload(Vehicle.brand),
        joinedload(Vehicle.vehicle_model),
    )


@router.get("/", response_model=List[VehicleSchema])
def get_vehicles(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = Query(None, description="Фильтр по клиенту"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка транспортных средств"""
    query = _vehicle_query(db)
    if customer_id is not None:
        query = query.filter(Vehicle.customer_id == customer_id)
    vehicles = query.offset(skip).limit(limit).all()
    return vehicles


@router.get("/search/by-license-plate", response_model=VehicleSchema)
def search_vehicle_by_license_plate(
    license_plate: str = Query(..., description="Государственный номер"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск транспортного средства по государственному номеру"""
    license_plate_normalized = license_plate.strip().upper().replace(' ', '')
    vehicle = _vehicle_query(db).filter(
        Vehicle.license_plate.ilike(f"%{license_plate_normalized}%")
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транспортное средство с указанным гос номером не найдено"
        )
    return vehicle


@router.get("/search/by-vin", response_model=VehicleSchema)
def search_vehicle_by_vin(
    vin: str = Query(..., min_length=6, max_length=17, description="VIN номер (6 последних символов или полный 17-символьный)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск транспортного средства по VIN номеру"""
    vin_normalized = vin.strip().upper()
    if len(vin_normalized) == 17:
        vehicle = _vehicle_query(db).filter(Vehicle.vin == vin_normalized).first()
    elif len(vin_normalized) == 6:
        vehicle = _vehicle_query(db).filter(func.substr(Vehicle.vin, -6) == vin_normalized).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VIN номер должен содержать либо 6 последних символов, либо полный 17-символьный номер"
        )
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транспортное средство с указанным VIN номером не найдено"
        )
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleSchema)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение транспортного средства по ID"""
    vehicle = _vehicle_query(db).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise NotFoundException("Транспортное средство не найдено")
    return vehicle


@router.post("/", response_model=VehicleSchema)
def create_vehicle(
    vehicle_create: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание транспортного средства"""
    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.id == vehicle_create.customer_id).first()
    if not customer:
        raise NotFoundException("Клиент не найден")
    brand = db.query(VehicleBrand).filter(VehicleBrand.id == vehicle_create.brand_id).first()
    if not brand:
        raise NotFoundException("Марка не найдена")
    model = db.query(VehicleModel).filter(VehicleModel.id == vehicle_create.model_id).first()
    if not model:
        raise NotFoundException("Модель не найдена")
    if model.brand_id != brand.id:
        raise HTTPException(status_code=400, detail="Модель не принадлежит указанной марке")
    vehicle = Vehicle(**vehicle_create.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    vehicle = _vehicle_query(db).filter(Vehicle.id == vehicle.id).first()
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleSchema)
def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление транспортного средства"""
    from app.models.customer import Customer
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise NotFoundException("Транспортное средство не найдено")
    update_data = vehicle_update.model_dump(exclude_unset=True)
    if 'customer_id' in update_data:
        customer = db.query(Customer).filter(Customer.id == update_data['customer_id']).first()
        if not customer:
            raise NotFoundException("Клиент не найден")
    if 'brand_id' in update_data:
        brand = db.query(VehicleBrand).filter(VehicleBrand.id == update_data['brand_id']).first()
        if not brand:
            raise NotFoundException("Марка не найдена")
    if 'model_id' in update_data:
        model = db.query(VehicleModel).filter(VehicleModel.id == update_data['model_id']).first()
        if not model:
            raise NotFoundException("Модель не найдена")
        brand_id = update_data.get('brand_id', vehicle.brand_id)
        if model.brand_id != brand_id:
            raise HTTPException(status_code=400, detail="Модель не принадлежит указанной марке")
    for field, value in update_data.items():
        setattr(vehicle, field, value)
    db.commit()
    vehicle = _vehicle_query(db).filter(Vehicle.id == vehicle_id).first()
    return vehicle

