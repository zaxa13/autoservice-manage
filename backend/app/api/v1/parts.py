from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from typing import List, Optional
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.part import Part
from app.models.warehouse import WarehouseItem
from app.schemas.part import Part as PartSchema, PartCreate, PartUpdate
from app.schemas.responses import ErrorResponse
from app.core.exceptions import NotFoundException
from app.core.permissions import require_manager_or_admin

router = APIRouter()

_404 = {404: {"model": ErrorResponse, "description": "Запчасть не найдена"}}
_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}


def _enrich_parts_with_stock(parts: list[Part], db: Session) -> list[dict]:
    """Добавляет stock_quantity к списку запчастей через один запрос к БД."""
    if not parts:
        return []
    part_ids = [p.id for p in parts]
    stock_map: dict[int, int] = {}
    rows = (
        db.query(WarehouseItem.part_id, WarehouseItem.quantity)
        .filter(WarehouseItem.part_id.in_(part_ids))
        .all()
    )
    for row in rows:
        stock_map[row.part_id] = int(row.quantity)

    result = []
    for part in parts:
        data = {
            "id": part.id,
            "name": part.name,
            "part_number": part.part_number,
            "brand": part.brand,
            "price": part.price,
            "purchase_price_last": part.purchase_price_last,
            "unit": part.unit,
            "category": part.category,
            "stock_quantity": stock_map.get(part.id, 0),
        }
        result.append(data)
    return result


@router.get(
    "/",
    response_model=List[PartSchema],
    status_code=status.HTTP_200_OK,
    summary="Список запчастей",
    description=(
        "Возвращает справочник запчастей с пагинацией. "
        "Поиск по артикулу нормализуется (верхний регистр, без пробелов) и ищется нечётко. "
        "Каждая позиция дополняется полем stock_quantity — текущим остатком на складе."
    ),
    responses=_auth,
)
def get_parts(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    search: Optional[str] = Query(None, description="Поиск по артикулу (part_number)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Part)
    if search and search.strip():
        term = search.strip().upper().replace(" ", "")
        q = q.filter(Part.part_number.ilike(f"%{term}%"))
    parts = q.offset(skip).limit(limit).all()
    return _enrich_parts_with_stock(parts, db)


@router.get(
    "/{part_id}",
    response_model=PartSchema,
    status_code=status.HTTP_200_OK,
    summary="Получить запчасть по ID",
    description=(
        "Возвращает данные запчасти включая stock_quantity — текущий остаток на складе. "
        "Возвращает 404 если не найдена."
    ),
    responses={**_auth, **_404},
)
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise NotFoundException("Запчасть не найдена")
    enriched = _enrich_parts_with_stock([part], db)
    return enriched[0]


@router.post(
    "/",
    response_model=PartSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать запчасть",
    description="Создание новой запчасти. Артикул нормализуется (верхний регистр, без пробелов).",
    responses=_write,
)
def create_part(
    part_create: PartCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    part = Part(**part_create.model_dump())
    db.add(part)
    db.commit()
    db.refresh(part)
    enriched = _enrich_parts_with_stock([part], db)
    return enriched[0]


@router.put(
    "/{part_id}",
    response_model=PartSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить запчасть",
    description="Обновление данных запчасти. Передавать нужно только изменяемые поля.",
    responses={**_write, **_404},
)
def update_part(
    part_id: int,
    part_update: PartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise NotFoundException("Запчасть не найдена")

    update_data = part_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(part, field, value)

    db.commit()
    db.refresh(part)
    enriched = _enrich_parts_with_stock([part], db)
    return enriched[0]
