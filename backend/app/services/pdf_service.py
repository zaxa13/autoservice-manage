"""Сервис генерации PDF-документов через xhtml2pdf."""

import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.employee import Employee
from app.models.order import Order, OrderWork, OrderPart
from app.models.part import Part
from app.models.setting import Setting
from app.models.supplier import Supplier
from app.models.vehicle import Vehicle
from app.models.vehicle_brand import VehicleBrand, VehicleModel
from app.models.warehouse import ReceiptDocument, ReceiptLine
from app.models.work import Work
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

_COMPANY_KEYS = ("company_name", "company_address", "company_phone", "company_inn")

_ONES_M  = ['','один','два','три','четыре','пять','шесть','семь','восемь','девять',
            'десять','одиннадцать','двенадцать','тринадцать','четырнадцать','пятнадцать',
            'шестнадцать','семнадцать','восемнадцать','девятнадцать']
_ONES_F  = ['','одна','две','три','четыре','пять','шесть','семь','восемь','девять',
            'десять','одиннадцать','двенадцать','тринадцать','четырнадцать','пятнадцать',
            'шестнадцать','семнадцать','восемнадцать','девятнадцать']
_TENS    = ['','десять','двадцать','тридцать','сорок','пятьдесят',
            'шестьдесят','семьдесят','восемьдесят','девяносто']
_HUNDS   = ['','сто','двести','триста','четыреста','пятьсот',
            'шестьсот','семьсот','восемьсот','девятьсот']


def _chunk_to_words(n: int, feminine: bool) -> list[str]:
    parts = []
    h = n // 100
    r = n % 100
    if h:
        parts.append(_HUNDS[h])
    if r < 20:
        w = (_ONES_F if feminine else _ONES_M)[r]
        if w:
            parts.append(w)
    else:
        parts.append(_TENS[r // 10])
        w = (_ONES_F if feminine else _ONES_M)[r % 10]
        if w:
            parts.append(w)
    return parts


def _thousands_word(n: int) -> str:
    r = n % 100
    d = r if r < 20 else r % 10
    if d == 1:
        return 'тысяча'
    if d in (2, 3, 4):
        return 'тысячи'
    return 'тысяч'


def _millions_word(n: int) -> str:
    r = n % 100
    d = r if r < 20 else r % 10
    if d == 1:
        return 'миллион'
    if d in (2, 3, 4):
        return 'миллиона'
    return 'миллионов'


def _rubles_in_words(amount: float) -> str:
    """Сумма прописью: 'Три тысячи пятьсот рублей 00 копеек'."""
    total_kopecks = round(amount * 100)
    rubles = total_kopecks // 100
    kopecks = total_kopecks % 100

    if rubles == 0:
        rub_str = 'ноль'
    else:
        parts = []
        millions = rubles // 1_000_000
        thousands = (rubles % 1_000_000) // 1000
        remainder = rubles % 1000

        if millions:
            parts.extend(_chunk_to_words(millions, feminine=False))
            parts.append(_millions_word(millions))
        if thousands:
            parts.extend(_chunk_to_words(thousands, feminine=True))
            parts.append(_thousands_word(thousands))
        if remainder:
            parts.extend(_chunk_to_words(remainder, feminine=False))

        rub_str = ' '.join(parts)

    r = rubles % 100
    d = r if r < 20 else r % 10
    if d == 1:
        rub_word = 'рубль'
    elif d in (2, 3, 4):
        rub_word = 'рубля'
    else:
        rub_word = 'рублей'

    rub_str = rub_str[0].upper() + rub_str[1:] if rub_str else 'Ноль'
    return f"{rub_str} {rub_word} {kopecks:02d} копеек"


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


def _company_ctx(db: Session) -> dict:
    """Реквизиты текущего тенанта из app.settings. Если не заполнены — прочерк."""
    rows = (
        db.query(Setting).filter(Setting.key.in_(_COMPANY_KEYS)).all()
    )
    by_key = {r.key: (r.value.strip() if r.value else "") for r in rows}
    return {key: (by_key.get(key) or "—") for key in _COMPANY_KEYS}


def _common_ctx(db: Session) -> dict:
    return {
        **_company_ctx(db),
        "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "font_path": _FONT_PATH,
    }


def _load_order(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Заказ-наряд не найден")
    return order


def _order_context(db: Session, order: Order) -> dict:
    """Общий контекст для заказ-наряда и акта.

    Модели shared-DB не имеют ORM-relationships (FK по composite-ключу без
    relationship()), поэтому связанное грузим вручную — как в
    generate_receipt_pdf."""
    vehicle = (
        db.query(Vehicle).filter(Vehicle.id == order.vehicle_id).first()
        if order.vehicle_id is not None else None
    )
    customer = (
        db.query(Customer).filter(Customer.id == vehicle.customer_id).first()
        if vehicle and vehicle.customer_id is not None else None
    )
    brand = (
        db.query(VehicleBrand).filter(VehicleBrand.id == vehicle.brand_id).first()
        if vehicle and vehicle.brand_id is not None else None
    )
    model = (
        db.query(VehicleModel).filter(VehicleModel.id == vehicle.model_id).first()
        if vehicle and vehicle.model_id is not None else None
    )
    accepted_by_emp = (
        db.query(Employee).filter(Employee.id == order.employee_id).first()
        if order.employee_id is not None else None
    )
    mechanic_emp = (
        db.query(Employee).filter(Employee.id == order.mechanic_id).first()
        if order.mechanic_id is not None else None
    )

    order_works = (
        db.query(OrderWork)
        .filter(OrderWork.order_id == order.id)
        .order_by(OrderWork.id)
        .all()
    )
    order_parts = (
        db.query(OrderPart)
        .filter(OrderPart.order_id == order.id)
        .order_by(OrderPart.id)
        .all()
    )

    work_ids = [w.work_id for w in order_works if w.work_id is not None]
    works_by_id: dict[int, Work] = (
        {w.id: w for w in db.query(Work).filter(Work.id.in_(work_ids)).all()}
        if work_ids else {}
    )
    part_ids = [p.part_id for p in order_parts if p.part_id is not None]
    parts_by_id: dict[int, Part] = (
        {p.id: p for p in db.query(Part).filter(Part.id.in_(part_ids)).all()}
        if part_ids else {}
    )

    works = []
    for w in order_works:
        wref = works_by_id.get(w.work_id)
        name = wref.name if wref else (w.work_name or "—")
        works.append({
            "name": name,
            "article": "",
            "quantity": w.quantity,
            "price": _fmt(w.price),
            "discount": float(w.discount or 0),
            "total": _fmt(w.total),
        })

    parts = []
    for p in order_parts:
        pref = parts_by_id.get(p.part_id)
        name = pref.name if pref else (p.part_name or "—")
        article = p.article or (pref.part_number if pref else None)
        parts.append({
            "name": name,
            "article": article or "",
            "quantity": p.quantity,
            "price": _fmt(p.price),
            "discount": float(p.discount or 0),
            "total": _fmt(p.total),
        })

    works_total = sum(float(w.total or 0) for w in order_works)
    parts_total = sum(float(p.total or 0) for p in order_parts)

    has_work_discounts = any(float(w.discount or 0) > 0 for w in order_works)
    has_part_discounts = any(float(p.discount or 0) > 0 for p in order_parts)

    status_value = order.status.value if hasattr(order.status, "value") else str(order.status)

    ctx = {
        **_common_ctx(db),
        "order_number": order.number,
        "status_label": STATUS_LABELS.get(status_value, status_value),
        "created_at": order.created_at.strftime("%d.%m.%Y") if order.created_at else "—",
        "completed_at": order.completed_at.strftime("%d.%m.%Y") if order.completed_at else None,
        "customer_name": customer.full_name if customer else "—",
        "customer_phone": customer.phone if customer else "—",
        "customer_address": customer.address if customer else None,
        "vehicle_brand": brand.name if brand else "—",
        "vehicle_model": model.name if model else "",
        "vehicle_year": vehicle.year if vehicle else None,
        "vehicle_plate": vehicle.license_plate if vehicle else None,
        "vehicle_vin": vehicle.vin if vehicle else None,
        "mileage": order.mileage_at_service,
        "accepted_by": accepted_by_emp.full_name if accepted_by_emp else None,
        "mechanic_name": mechanic_emp.full_name if mechanic_emp else None,
        "works": works,
        "parts": parts,
        "works_total": _fmt(works_total) if works_total else None,
        "parts_total": _fmt(parts_total) if parts_total else None,
        "grand_total": _fmt(works_total + parts_total),
        "works_total_words": _rubles_in_words(works_total) if works_total else None,
        "parts_total_words": _rubles_in_words(parts_total) if parts_total else None,
        "grand_total_words": _rubles_in_words(works_total + parts_total),
        "works_qty_total": sum(w.quantity for w in order_works),
        "parts_qty_total": sum(p.quantity for p in order_parts),
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
    ctx = _order_context(db, order)
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

    ctx = _order_context(db, order)
    ctx["paid_amount"] = _fmt(paid_amount)
    return _render_pdf("act.html", ctx)


def generate_receipt_pdf(db: Session, receipt_id: int) -> bytes:
    """Генерация PDF приходной накладной."""
    receipt = (
        db.query(ReceiptDocument)
        .filter(ReceiptDocument.id == receipt_id)
        .first()
    )
    if not receipt:
        raise NotFoundException("Накладная не найдена")

    # ReceiptDocument не имеет ORM-relationships (FK по composite ключу
    # настроены без relationship()), поэтому грузим связанное вручную.
    supplier = (
        db.query(Supplier).filter(Supplier.id == receipt.supplier_id).first()
        if receipt.supplier_id is not None else None
    )
    receipt_lines = (
        db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt.id).all()
    )
    part_ids = [l.part_id for l in receipt_lines if l.part_id is not None]
    parts_by_id: dict[int, Part] = {}
    if part_ids:
        parts_by_id = {
            p.id: p
            for p in db.query(Part).filter(Part.id.in_(part_ids)).all()
        }

    lines = []
    for line in receipt_lines:
        part = parts_by_id.get(line.part_id)
        line_total = float(line.quantity) * float(line.purchase_price)
        lines.append({
            "name": part.name if part else "—",
            "article": part.part_number if part else "",
            "quantity": _fmt(line.quantity),
            "purchase_price": _fmt(line.purchase_price),
            "sale_price": _fmt(line.sale_price),
            "line_total": _fmt(line_total),
        })

    total_amount = sum(float(l.quantity) * float(l.purchase_price) for l in receipt_lines)

    status_value = receipt.status.value if hasattr(receipt.status, "value") else str(receipt.status)

    ctx = {
        **_common_ctx(db),
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
