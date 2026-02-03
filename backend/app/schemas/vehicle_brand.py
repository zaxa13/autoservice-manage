from pydantic import BaseModel
from typing import List


class BrandInput(BaseModel):
    """Один бренд с моделями для импорта"""
    name: str
    models: List[str]


class BrandsImport(BaseModel):
    """Тело запроса для импорта марок и моделей"""
    brands: List[BrandInput]


class BrandItem(BaseModel):
    """Марка с id"""
    id: int
    name: str

    class Config:
        from_attributes = True


class BrandsListResponse(BaseModel):
    """Список марок с id"""
    brands: List[BrandItem]


class ModelsRequest(BaseModel):
    """Запрос моделей по марке (name или brand_id)"""
    brand: str | None = None
    brand_id: int | None = None  # можно передать id марки вместо названия


class ModelItem(BaseModel):
    """Модель с id"""
    id: int
    name: str

    class Config:
        from_attributes = True


class ModelsResponse(BaseModel):
    """Список моделей с id"""
    models: List[ModelItem]
