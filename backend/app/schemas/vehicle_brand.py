from pydantic import BaseModel, Field
from typing import List, Optional


class BrandInput(BaseModel):
    """Один бренд с моделями для импорта"""
    name: str = Field(..., min_length=1, description="Название марки")
    models: List[str] = Field(..., min_length=1, description="Список названий моделей")


class BrandsImport(BaseModel):
    """Тело запроса для импорта марок и моделей"""
    brands: List[BrandInput] = Field(..., min_length=1, description="Список марок с моделями")


class BrandItem(BaseModel):
    """Марка с id"""
    id: int = Field(..., description="ID марки")
    name: str = Field(..., description="Название марки")

    class Config:
        from_attributes = True


class BrandsListResponse(BaseModel):
    """Список марок с id"""
    brands: List[BrandItem] = Field(..., description="Список марок автомобилей")


class ModelsRequest(BaseModel):
    """Запрос моделей по марке (name или brand_id)"""
    brand: Optional[str] = Field(None, description="Название марки (поиск без учёта регистра)")
    brand_id: Optional[int] = Field(None, description="ID марки (приоритетнее name)")


class ModelItem(BaseModel):
    """Модель с id"""
    id: int = Field(..., description="ID модели")
    name: str = Field(..., description="Название модели")

    class Config:
        from_attributes = True


class ModelsResponse(BaseModel):
    """Список моделей с id"""
    models: List[ModelItem] = Field(..., description="Список моделей для марки")
