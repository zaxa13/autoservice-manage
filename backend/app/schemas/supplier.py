from pydantic import BaseModel
from typing import Optional


class SupplierBase(BaseModel):
    name: str
    inn: Optional[str] = None
    kpp: Optional[str] = None
    legal_address: Optional[str] = None
    contact: Optional[str] = None
    bank_name: Optional[str] = None
    bik: Optional[str] = None
    bank_account: Optional[str] = None
    correspondent_account: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    legal_address: Optional[str] = None
    contact: Optional[str] = None
    bank_name: Optional[str] = None
    bik: Optional[str] = None
    bank_account: Optional[str] = None
    correspondent_account: Optional[str] = None


class Supplier(SupplierBase):
    id: int

    class Config:
        from_attributes = True
