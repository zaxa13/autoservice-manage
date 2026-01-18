from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import Vehicle as VehicleSchema, VehicleCreate, VehicleUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()


@router.get("/", response_model=List[VehicleSchema])
def get_vehicles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка транспортных средств"""
    from sqlalchemy.orm import joinedload
    vehicles = db.query(Vehicle).options(joinedload(Vehicle.customer)).offset(skip).limit(limit).all()
    return vehicles


@router.get("/search/by-license-plate", response_model=VehicleSchema)
def search_vehicle_by_license_plate(
    license_plate: str = Query(..., description="Государственный номер"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск транспортного средства по государственному номеру"""
    from sqlalchemy.orm import joinedload
    # Приводим к верхнему регистру и убираем пробелы для поиска
    license_plate_normalized = license_plate.strip().upper().replace(' ', '')
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).filter(
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
    vin: str = Query(..., min_length=17, max_length=17, description="VIN номер (17 символов)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск транспортного средства по VIN номеру"""
    from sqlalchemy.orm import joinedload
    # Приводим к верхнему регистру для поиска
    vin_normalized = vin.strip().upper()
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).filter(Vehicle.vin == vin_normalized).first()
    
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
    from sqlalchemy.orm import joinedload
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).filter(Vehicle.id == vehicle_id).first()
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
    from sqlalchemy.orm import joinedload
    # Проверяем, существует ли customer
    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.id == vehicle_create.customer_id).first()
    if not customer:
        raise NotFoundException("Клиент не найден")
    
    vehicle = Vehicle(**vehicle_create.dict())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    # Загружаем customer для ответа
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).filter(Vehicle.id == vehicle.id).first()
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleSchema)
def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление транспортного средства"""
    from sqlalchemy.orm import joinedload
    from app.models.customer import Customer
    
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise NotFoundException("Транспортное средство не найдено")
    
    update_data = vehicle_update.dict(exclude_unset=True)
    
    # Если обновляется customer_id, проверяем существование customer
    if 'customer_id' in update_data:
        customer = db.query(Customer).filter(Customer.id == update_data['customer_id']).first()
        if not customer:
            raise NotFoundException("Клиент не найден")
    
    for field, value in update_data.items():
        setattr(vehicle, field, value)
    
    db.commit()
    
    # Загружаем customer для ответа
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).filter(Vehicle.id == vehicle_id).first()
    return vehicle

