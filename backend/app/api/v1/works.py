from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.work import Work
from app.schemas.work import Work as WorkSchema, WorkCreate, WorkUpdate
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()


@router.get("/", response_model=List[WorkSchema])
def get_works(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="Поиск по названию работы"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка видов работ"""
    query = db.query(Work)
    if search:
        query = query.filter(Work.name.ilike(f"%{search}%"))
    works = query.offset(skip).limit(limit).all()
    return works


@router.get("/{work_id}", response_model=WorkSchema)
def get_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение вида работы по ID"""
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise NotFoundException("Вид работы не найден")
    return work


@router.post("/", response_model=WorkSchema)
def create_work(
    work_create: WorkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Создание вида работы"""
    work = Work(**work_create.dict())
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


@router.put("/{work_id}", response_model=WorkSchema)
def update_work(
    work_id: int,
    work_update: WorkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin)
):
    """Обновление вида работы"""
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise NotFoundException("Вид работы не найден")
    
    update_data = work_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(work, field, value)
    
    db.commit()
    db.refresh(work)
    return work

