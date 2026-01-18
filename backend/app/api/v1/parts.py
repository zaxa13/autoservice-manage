from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.part import Part
from app.schemas.part import Part as PartSchema, PartCreate, PartUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()


@router.get("/", response_model=List[PartSchema])
def get_parts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка запчастей"""
    parts = db.query(Part).offset(skip).limit(limit).all()
    return parts


@router.get("/{part_id}", response_model=PartSchema)
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение запчасти по ID"""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise NotFoundException("Запчасть не найдена")
    return part


@router.post("/", response_model=PartSchema)
def create_part(
    part_create: PartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание запчасти"""
    part = Part(**part_create.dict())
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.put("/{part_id}", response_model=PartSchema)
def update_part(
    part_id: int,
    part_update: PartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление запчасти"""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise NotFoundException("Запчасть не найдена")
    
    update_data = part_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(part, field, value)
    
    db.commit()
    db.refresh(part)
    return part

