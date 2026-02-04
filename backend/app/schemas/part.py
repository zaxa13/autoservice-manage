from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal
from app.models.part import PartCategory


def _normalize_article(v: Optional[str]) -> Optional[str]:
    """Обрезка пробелов по краям, верхний регистр, удаление всех пробелов внутри (например 06L 115 562 B → 06L115562B)."""
    if v is None:
        return None
    s = v.strip().upper().replace(" ", "")
    return s if s else None


def _normalize_article_required(v: Optional[str]) -> str:
    """Нормализация артикула; пустой после нормализации запрещён."""
    if v is None or not isinstance(v, str):
        raise ValueError("Артикул обязателен")
    s = v.strip().upper().replace(" ", "")
    if not s:
        raise ValueError("Артикул не может быть пустым")
    return s


class PartBase(BaseModel):
    name: str
    part_number: str  # Обязателен: без артикула нельзя идентифицировать запчасть при списании
    brand: Optional[str] = None
    price: Decimal
    purchase_price_last: Optional[Decimal] = None
    unit: str = "шт"
    category: PartCategory = PartCategory.OTHER

    @field_validator("part_number")
    @classmethod
    def normalize_part_number(cls, v: str) -> str:
        return _normalize_article_required(v)


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: Optional[str] = None
    part_number: Optional[str] = None  # при обновлении: если передан — обязан быть непустым после нормализации
    brand: Optional[str] = None
    price: Optional[Decimal] = None
    purchase_price_last: Optional[Decimal] = None
    unit: Optional[str] = None
    category: Optional[PartCategory] = None

    @field_validator("part_number")
    @classmethod
    def normalize_part_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = _normalize_article(v)
        if not s:
            raise ValueError("Артикул не может быть пустым")
        return s


class Part(PartBase):
    id: int

    class Config:
        from_attributes = True

