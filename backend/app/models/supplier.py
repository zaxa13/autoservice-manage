from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    inn = Column(String, nullable=True)
    kpp = Column(String, nullable=True)
    legal_address = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    # Банковские реквизиты
    bank_name = Column(String, nullable=True)
    bik = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)  # расчётный счёт
    correspondent_account = Column(String, nullable=True)  # корр. счёт

    receipt_documents = relationship("ReceiptDocument", back_populates="supplier")
