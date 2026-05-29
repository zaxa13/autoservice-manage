from pydantic import BaseModel, Field


class PartBrand(BaseModel):
    id: int = Field(..., description="Уникальный ID бренда")
    name: str = Field(..., description="Название бренда")

    class Config:
        from_attributes = True


class PartBrandRef(BaseModel):
    """Сокращённое представление для вложения в Part."""
    id: int
    name: str

    class Config:
        from_attributes = True


class PartBrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Название бренда")
