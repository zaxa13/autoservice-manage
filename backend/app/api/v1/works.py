from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.work import Work
from app.schemas.work import Work as WorkSchema, WorkCreate, WorkUpdate
from app.schemas.responses import ErrorResponse
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Вид работы не найден"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


@router.get(
    "/",
    response_model=List[WorkSchema],
    status_code=status.HTTP_200_OK,
    summary="Список видов работ",
    description="Возвращает справочник видов работ с пагинацией и поиском по названию.",
    responses=_auth,
)
def get_works(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    search: Optional[str] = Query(None, description="Поиск по названию работы (нечёткий)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Work)
    if search:
        query = query.filter(Work.name.ilike(f"%{search}%"))
    works = query.offset(skip).limit(limit).all()
    return works


@router.get(
    "/{work_id}",
    response_model=WorkSchema,
    status_code=status.HTTP_200_OK,
    summary="Получить вид работы по ID",
    description="Возвращает данные вида работы. Возвращает 404 если не найдена.",
    responses={**_auth, **_404},
)
def get_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise NotFoundException("Вид работы не найден")
    return work


@router.post(
    "/",
    response_model=WorkSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать вид работы",
    description="Создание нового вида работы в справочнике. Доступно менеджеру и администратору.",
    responses=_write,
)
def create_work(
    work_create: WorkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    work = Work(**work_create.model_dump())
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


@router.put(
    "/{work_id}",
    response_model=WorkSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить вид работы",
    description="Обновление данных вида работы. Передавать нужно только изменяемые поля.",
    responses={**_write, **_404},
)
def update_work(
    work_id: int,
    work_update: WorkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise NotFoundException("Вид работы не найден")

    update_data = work_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(work, field, value)

    db.commit()
    db.refresh(work)
    return work
