from pydantic import BaseModel, Field
from typing import Optional


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, description="Наименование поставщика")
    inn: Optional[str] = Field(None, description="ИНН")
    kpp: Optional[str] = Field(None, description="КПП")
    legal_address: Optional[str] = Field(None, description="Юридический адрес")
    contact: Optional[str] = Field(None, description="Контактное лицо / телефон")
    bank_name: Optional[str] = Field(None, description="Наименование банка")
    bik: Optional[str] = Field(None, description="БИК банка")
    bank_account: Optional[str] = Field(None, description="Расчётный счёт")
    correspondent_account: Optional[str] = Field(None, description="Корреспондентский счёт")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Наименование поставщика")
    inn: Optional[str] = Field(None, description="ИНН")
    kpp: Optional[str] = Field(None, description="КПП")
    legal_address: Optional[str] = Field(None, description="Юридический адрес")
    contact: Optional[str] = Field(None, description="Контактное лицо / телефон")
    bank_name: Optional[str] = Field(None, description="Наименование банка")
    bik: Optional[str] = Field(None, description="БИК банка")
    bank_account: Optional[str] = Field(None, description="Расчётный счёт")
    correspondent_account: Optional[str] = Field(None, description="Корреспондентский счёт")


class Supplier(SupplierBase):
    id: int = Field(..., description="Уникальный ID поставщика")

    class Config:
        from_attributes = True
