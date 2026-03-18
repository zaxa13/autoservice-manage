from pydantic import BaseModel, Field, field_validator
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
    name: str = Field(..., min_length=1, description="Название запчасти")
    part_number: str = Field(..., min_length=1, description="Артикул запчасти (нормализуется: верхний регистр, без пробелов)")
    brand: Optional[str] = Field(None, description="Бренд / производитель запчасти")
    price: Decimal = Field(..., ge=0, description="Цена продажи")
    purchase_price_last: Optional[Decimal] = Field(None, ge=0, description="Последняя закупочная цена")
    unit: str = Field("шт", description="Единица измерения")
    category: PartCategory = Field(PartCategory.OTHER, description="Категория запчасти")

    @field_validator("part_number")
    @classmethod
    def normalize_part_number(cls, v: str) -> str:
        return _normalize_article_required(v)


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Название запчасти")
    part_number: Optional[str] = Field(None, description="Артикул запчасти")
    brand: Optional[str] = Field(None, description="Бренд / производитель")
    price: Optional[Decimal] = Field(None, ge=0, description="Цена продажи")
    purchase_price_last: Optional[Decimal] = Field(None, ge=0, description="Последняя закупочная цена")
    unit: Optional[str] = Field(None, description="Единица измерения")
    category: Optional[PartCategory] = Field(None, description="Категория запчасти")

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
    id: int = Field(..., description="Уникальный ID запчасти")

    class Config:
        from_attributes = True
