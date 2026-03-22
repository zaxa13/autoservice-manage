"""Сервис генерации PDF-документов через xhtml2pdf."""

import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderWork, OrderPart
from app.models.vehicle import Vehicle
from app.models.warehouse import ReceiptDocument, ReceiptLine
from app.core.exceptions import NotFoundException

# Путь к шаблонам
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)

# Шрифты с поддержкой кириллицы (порядок приоритета)
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",       # macOS
    "/Library/Fonts/Arial.ttf",                            # macOS (старые версии)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",     # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

def _find_font() -> str | None:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None

_FONT_PATH = _find_font()

COMPANY_NAME = 'ООО "Рога и Копыта"'
COMPANY_ADDRESS = "г. Москва, ул. Автосервисная, д. 42, оф. 7"
COMPANY_PHONE = "+7 (495) 000-11-22"
COMPANY_INN = "7701234567"

STATUS_LABELS = {
    "new": "Новый",
    "estimation": "Проценка",
    "in_progress": "В работе",
    "ready_for_payment": "Готов к оплате",
    "paid": "Оплачен",
    "completed": "Завершён",
    "cancelled": "Отменён",
}


def _fmt(val: Decimal | float | None) -> str:
    """Форматирование числа: 12345.50 → '12 345.50'."""
    if val is None:
        return "0.00"
    return f"{float(val):,.2f}".replace(",", " ")


def _common_ctx() -> dict:
    return {
        "company_name": COMPANY_NAME,
        "company_address": COMPANY_ADDRESS,
        "company_phone": COMPANY_PHONE,
        "company_inn": COMPANY_INN,
        "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "font_path": _FONT_PATH,
    }


def _load_order(db: Session, order_id: int) -> Order:
    order = (
        db.query(Order)
        .options(
            joinedload(Order.vehicle).joinedload(Vehicle.customer),
            joinedload(Order.vehicle).joinedload(Vehicle.brand),
            joinedload(Order.vehicle).joinedload(Vehicle.vehicle_model),
            joinedload(Order.employee),
            joinedload(Order.mechanic),
            joinedload(Order.order_works).joinedload(OrderWork.work),
            joinedload(Order.order_parts).joinedload(OrderPart.part),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    return order


def _order_context(order: Order) -> dict:
    """Общий контекст для заказ-наряда и акта."""
    vehicle = order.vehicle
    customer = vehicle.customer if vehicle else None

    works = []
    for w in order.order_works:
        name = w.work.name if w.work else (w.work_name or "—")
        works.append({
            "name": name,
            "quantity": w.quantity,
            "price": _fmt(w.price),
            "discount": float(w.discount or 0),
            "total": _fmt(w.total),
        })

    parts = []
    for p in order.order_parts:
        name = p.part.name if p.part else (p.part_name or "—")
        article = p.article or (p.part.part_number if p.part else None)
        parts.append({
            "name": name,
            "article": article or "",
            "quantity": p.quantity,
            "price": _fmt(p.price),
            "discount": float(p.discount or 0),
            "total": _fmt(p.total),
        })

    works_total = sum(float(w.total or 0) for w in order.order_works)
    parts_total = sum(float(p.total or 0) for p in order.order_parts)

    has_work_discounts = any(float(w.discount or 0) > 0 for w in order.order_works)
    has_part_discounts = any(float(p.discount or 0) > 0 for p in order.order_parts)

    status_value = order.status.value if hasattr(order.status, "value") else str(order.status)

    ctx = {
        **_common_ctx(),
        "order_number": order.number,
        "status_label": STATUS_LABELS.get(status_value, status_value),
        "created_at": order.created_at.strftime("%d.%m.%Y") if order.created_at else "—",
        "completed_at": order.completed_at.strftime("%d.%m.%Y") if order.completed_at else None,
        "customer_name": customer.full_name if customer else "—",
        "customer_phone": customer.phone if customer else "—",
        "customer_address": customer.address if customer else None,
        "vehicle_brand": vehicle.brand.name if vehicle and vehicle.brand else "—",
        "vehicle_model": vehicle.vehicle_model.name if vehicle and vehicle.vehicle_model else "",
        "vehicle_year": vehicle.year if vehicle else None,
        "vehicle_plate": vehicle.license_plate if vehicle else None,
        "vehicle_vin": vehicle.vin if vehicle else None,
        "mileage": order.mileage_at_service,
        "accepted_by": order.employee.full_name if order.employee else None,
        "mechanic_name": order.mechanic.full_name if order.mechanic else None,
        "works": works,
        "parts": parts,
        "works_total": _fmt(works_total) if works_total else None,
        "parts_total": _fmt(parts_total) if parts_total else None,
        "grand_total": _fmt(works_total + parts_total),
        "has_work_discounts": has_work_discounts,
        "has_part_discounts": has_part_discounts,
        "recommendations": order.recommendations or "",
        "comments": order.comments or "",
    }
    return ctx


def _render_pdf(template_name: str, context: dict) -> bytes:
    template = _jinja_env.get_template(template_name)
    html_string = template.render(**context)
    buf = BytesIO()
    result = pisa.CreatePDF(html_string.encode("utf-8"), dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"Ошибка генерации PDF: {result.err}")
    return buf.getvalue()


# ─── Публичные функции ────────────────────────────────────────


def generate_order_pdf(db: Session, order_id: int) -> bytes:
    """Генерация PDF заказ-наряда."""
    order = _load_order(db, order_id)
    ctx = _order_context(order)
    return _render_pdf("order.html", ctx)


def generate_act_pdf(db: Session, order_id: int) -> bytes:
    """Генерация PDF акта выполненных работ."""
    order = _load_order(db, order_id)

    # Рассчитываем оплаченную сумму
    from app.models.payment import Payment, PaymentStatus
    from sqlalchemy import func as sqlfunc

    paid_amount = (
        db.query(sqlfunc.sum(Payment.amount))
        .filter(Payment.order_id == order.id, Payment.status == PaymentStatus.SUCCEEDED)
        .scalar()
        or Decimal("0")
    )

    ctx = _order_context(order)
    ctx["paid_amount"] = _fmt(paid_amount)
    return _render_pdf("act.html", ctx)


def generate_receipt_pdf(db: Session, receipt_id: int) -> bytes:
    """Генерация PDF приходной накладной."""
    receipt = (
        db.query(ReceiptDocument)
        .options(
            joinedload(ReceiptDocument.supplier),
            joinedload(ReceiptDocument.lines).joinedload(ReceiptLine.part),
        )
        .filter(ReceiptDocument.id == receipt_id)
        .first()
    )
    if not receipt:
        raise NotFoundException("Накладная не найдена")

    supplier = receipt.supplier
    lines = []
    for line in receipt.lines:
        part = line.part
        line_total = float(line.quantity) * float(line.purchase_price)
        lines.append({
            "name": part.name if part else "—",
            "article": part.part_number if part else "",
            "quantity": _fmt(line.quantity),
            "purchase_price": _fmt(line.purchase_price),
            "sale_price": _fmt(line.sale_price),
            "line_total": _fmt(line_total),
        })

    total_amount = sum(float(l.quantity) * float(l.purchase_price) for l in receipt.lines)

    status_value = receipt.status.value if hasattr(receipt.status, "value") else str(receipt.status)

    ctx = {
        **_common_ctx(),
        "receipt": receipt,
        "document_date": receipt.document_date.strftime("%d.%m.%Y") if receipt.document_date else "—",
        "status_label": "Проведена" if status_value == "posted" else "Черновик",
        "supplier_name": supplier.name if supplier else None,
        "supplier_inn": supplier.inn if supplier else None,
        "supplier_address": supplier.legal_address if supplier else None,
        "supplier_contact": supplier.contact if supplier else None,
        "supplier_doc_number": receipt.supplier_document_number,
        "supplier_doc_date": (
            receipt.supplier_document_date.strftime("%d.%m.%Y")
            if receipt.supplier_document_date
            else None
        ),
        "lines": lines,
        "total_amount": _fmt(total_amount),
    }
    return _render_pdf("receipt.html", ctx)
