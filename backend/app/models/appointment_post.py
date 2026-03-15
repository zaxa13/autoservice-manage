import json
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import TypeDecorator
from app.database import Base


class JSONList(TypeDecorator):
    """Хранение списка строк как JSON в TEXT (для SQLite)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return None
        return None


class AppointmentPost(Base):
    """Пост для записей (колонка на доске). Один пост = одна колонка с лимитом записей."""
    __tablename__ = "appointment_posts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Пост 1", "Пост 2"
    max_slots = Column(Integer, nullable=False, default=5)  # макс. записей на посту
    slot_times = Column(JSONList, nullable=True)  # слоты по времени, напр. ["09:00", "11:00", "13:00", "15:00", "17:00"]
    color = Column(String, nullable=True)  # hex для раскраски колонки
    sort_order = Column(Integer, nullable=False, default=0)  # порядок колонок слева направо

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    appointments = relationship("Appointment", back_populates="post")
