"""Склад — async на shared-DB.

Три ресурса в одном роутере:
- items: список / get / создать (FK на parts).
- transactions: журнал, оформить incoming, корректировка остатка.
- receipts (приходные накладные): CRUD черновика + проводка (post).

Что НЕ в Wave 4a:
- /receipts/{id}/print (PDF) — pdf_service ещё на sync.
- Авто-outgoing при оплате заказа — мини-фича для Wave 4c.

Номера накладных — через `app.tenant_counters`, ключ 'receipts',
формат `НП-001`.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.permissions import require_admin, require_manager_or_admin
from app.core.security import TenantClaims
from app.database import sync_tenant_session
from app.dependencies import get_current_claims, get_tenant_db
from app.services.pdf_service import generate_receipt_pdf
from app.models.part import Part
from app.models.supplier import Supplier
from app.models.warehouse import (
    ReceiptDocument,
    ReceiptLine,
    ReceiptStatus,
    TransactionType,
    WarehouseItem,
    WarehouseTransaction,
)
from app.schemas.receipt import (
    ReceiptDocument as ReceiptDocumentSchema,
    ReceiptDocumentCreate,
    ReceiptDocumentUpdate,
    SupplierReceiptsReport,
)
from app.schemas.responses import ErrorResponse
from app.schemas.warehouse import (
    WarehouseAdjustmentCreate,
    WarehouseItem as WarehouseItemSchema,
    WarehouseItemCreate,
    WarehouseTransaction as WarehouseTransactionSchema,
    WarehouseTransactionCreate,
    WarehouseTransactionList,
)

router = APIRouter()

_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}
_400 = {400: {"model": ErrorResponse, "description": "Некорректные данные"}}
_404_item = {404: {"model": ErrorResponse, "description": "Позиция склада не найдена"}}
_404_receipt = {404: {"model": ErrorResponse, "description": "Накладная не найдена"}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _next_receipt_number(db: AsyncSession) -> str:
    await db.execute(
        text(
            "INSERT INTO app.tenant_counters (tenant_id, counter_name, value) "
            "VALUES (app.current_tenant(), 'receipts', 0) "
            "ON CONFLICT (tenant_id, counter_name) DO NOTHING"
        )
    )
    n = (await db.execute(
        text(
            "UPDATE app.tenant_counters SET value = value + 1 "
            "WHERE tenant_id = app.current_tenant() AND counter_name = 'receipts' "
            "RETURNING value"
        )
    )).scalar_one()
    return f"НП-{n:03d}"


def _resolve_employee_id(claims: TenantClaims) -> int:
    if claims.employee_id is None:
        raise BadRequestException(
            "JWT-токен не содержит employee_id — нужно для складских операций"
        )
    return claims.employee_id


def _part_dict(p: Part, stock: int = 0) -> dict:
    return {
        "id": p.id, "name": p.name, "part_number": p.part_number,
        "brand": p.brand, "price": p.price,
        "purchase_price_last": p.purchase_price_last,
        "unit": p.unit, "category": p.category, "stock_quantity": stock,
    }


async def _serialize_item(db: AsyncSession, item: WarehouseItem, claims: TenantClaims) -> dict:
    part = await db.get(Part, (claims.tenant_id, item.part_id))
    return {
        "id": item.id, "part_id": item.part_id,
        "quantity": item.quantity, "min_quantity": item.min_quantity,
        "location": item.location, "last_updated": item.last_updated,
        "part": _part_dict(part, int(item.quantity)) if part else None,
    }


async def _serialize_receipt(
    db: AsyncSession, r: ReceiptDocument, claims: TenantClaims
) -> dict:
    supplier = (
        await db.get(Supplier, (claims.tenant_id, r.supplier_id))
        if r.supplier_id else None
    )
    lines_rows = (
        await db.execute(
            select(ReceiptLine).where(ReceiptLine.receipt_id == r.id).order_by(ReceiptLine.id)
        )
    ).scalars().all()
    part_ids = {l.part_id for l in lines_rows}
    pmap = {}
    if part_ids:
        pmap = {
            p.id: p
            for p in (await db.execute(select(Part).where(Part.id.in_(part_ids)))).scalars()
        }
    lines = [
        {
            "id": l.id, "receipt_id": l.receipt_id,
            "part_id": l.part_id, "quantity": l.quantity,
            "purchase_price": l.purchase_price, "sale_price": l.sale_price,
            "part": _part_dict(pmap[l.part_id]) if l.part_id in pmap else None,
        }
        for l in lines_rows
    ]
    total_amount = sum(
        (Decimal(str(l["quantity"])) * Decimal(str(l["purchase_price"])) for l in lines),
        Decimal(0),
    )
    return {
        "id": r.id, "number": r.number,
        "document_date": r.document_date,
        "supplier_id": r.supplier_id,
        "supplier_document_number": r.supplier_document_number,
        "supplier_document_date": r.supplier_document_date,
        "status": r.status,
        "created_at": r.created_at,
        "supplier": supplier,
        "lines": lines,
        "total_amount": total_amount,
    }


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------
@router.get("/items", response_model=list[WarehouseItemSchema], responses=_auth)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    part_number: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    stmt = (
        select(WarehouseItem)
        .join(Part, WarehouseItem.part_id == Part.id)
        .order_by(Part.part_number)
    )
    if part_number and part_number.strip():
        norm = part_number.strip().upper().replace(" ", "")
        stmt = stmt.where(func.upper(func.trim(Part.part_number)) == norm)
    stmt = stmt.offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [await _serialize_item(db, i, claims) for i in rows]


@router.get(
    "/items/{item_id}",
    response_model=WarehouseItemSchema,
    responses={**_auth, **_404_item},
)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    item = await db.get(WarehouseItem, (claims.tenant_id, item_id))
    if item is None:
        raise NotFoundException("Позиция склада не найдена")
    return await _serialize_item(db, item, claims)


@router.post(
    "/items",
    response_model=WarehouseItemSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, **_400},
)
async def create_item(
    body: WarehouseItemCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    # Проверяем, что part существует.
    if await db.get(Part, (claims.tenant_id, body.part_id)) is None:
        raise NotFoundException("Запчасть не найдена")
    # UNIQUE(tenant_id, part_id) — повторное создание ловится IntegrityError → пусть всплывёт.
    item = WarehouseItem(
        tenant_id=claims.tenant_id,
        part_id=body.part_id,
        quantity=body.quantity,
        min_quantity=body.min_quantity,
        location=body.location,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return await _serialize_item(db, item, claims)


@router.get(
    "/low-stock",
    response_model=list[WarehouseItemSchema],
    responses=_auth,
)
async def low_stock(
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    rows = (
        await db.execute(
            select(WarehouseItem).where(WarehouseItem.quantity < WarehouseItem.min_quantity)
        )
    ).scalars().all()
    return [await _serialize_item(db, i, claims) for i in rows]


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
@router.get(
    "/transactions",
    response_model=list[WarehouseTransactionList],
    responses=_auth,
)
async def list_transactions(
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    part_id: Optional[int] = Query(None),
    order_id: Optional[int] = Query(None),
    receipt_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _claims: TenantClaims = Depends(get_current_claims),
):
    stmt = select(WarehouseTransaction).order_by(WarehouseTransaction.created_at.desc())
    if date_from:
        stmt = stmt.where(WarehouseTransaction.created_at >= date_from)
    if date_to:
        stmt = stmt.where(WarehouseTransaction.created_at <= date_to)
    if transaction_type:
        stmt = stmt.where(WarehouseTransaction.transaction_type == transaction_type.value)
    if order_id is not None:
        stmt = stmt.where(WarehouseTransaction.order_id == order_id)
    if receipt_id is not None:
        stmt = stmt.where(WarehouseTransaction.receipt_id == receipt_id)
    if part_id is not None:
        # part_id фильтр через warehouse_item.
        item_ids_stmt = select(WarehouseItem.id).where(WarehouseItem.part_id == part_id)
        stmt = stmt.where(WarehouseTransaction.warehouse_item_id.in_(item_ids_stmt))
    stmt = stmt.offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    # Bulk-fetch parts via items.
    item_ids = {t.warehouse_item_id for t in rows}
    items = {
        i.id: i
        for i in (await db.execute(select(WarehouseItem).where(WarehouseItem.id.in_(item_ids)))).scalars()
    } if item_ids else {}
    part_ids = {i.part_id for i in items.values()}
    parts = {
        p.id: p
        for p in (await db.execute(select(Part).where(Part.id.in_(part_ids)))).scalars()
    } if part_ids else {}

    return [
        {
            "id": t.id, "warehouse_item_id": t.warehouse_item_id,
            "transaction_type": t.transaction_type, "quantity": t.quantity,
            "price": t.price, "order_id": t.order_id,
            "receipt_id": t.receipt_id, "employee_id": t.employee_id,
            "created_at": t.created_at,
            "part": (
                _part_dict(parts[items[t.warehouse_item_id].part_id])
                if t.warehouse_item_id in items
                and items[t.warehouse_item_id].part_id in parts
                else None
            ),
            "order_number": None,
            "receipt_number": None,
            "employee_name": None,
        }
        for t in rows
    ]


@router.post(
    "/transactions/incoming",
    response_model=WarehouseTransactionSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, **_400},
)
async def create_incoming(
    body: WarehouseTransactionCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    employee_id = _resolve_employee_id(claims)
    item = await db.get(WarehouseItem, (claims.tenant_id, body.warehouse_item_id))
    if item is None:
        raise NotFoundException("Позиция склада не найдена")
    item.quantity = Decimal(str(item.quantity)) + Decimal(str(body.quantity))
    t = WarehouseTransaction(
        tenant_id=claims.tenant_id,
        warehouse_item_id=item.id,
        transaction_type=TransactionType.INCOMING.value,
        quantity=body.quantity,
        price=body.price,
        order_id=body.order_id,
        receipt_id=body.receipt_id,
        employee_id=employee_id,
    )
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


@router.post(
    "/transactions/adjustment",
    response_model=WarehouseTransactionSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, **_400},
)
async def create_adjustment(
    body: WarehouseAdjustmentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    employee_id = _resolve_employee_id(claims)
    item = await db.get(WarehouseItem, (claims.tenant_id, body.warehouse_item_id))
    if item is None:
        raise NotFoundException("Позиция склада не найдена")
    new_qty = Decimal(str(item.quantity)) + Decimal(str(body.quantity_delta))
    if new_qty < 0:
        raise BadRequestException("Корректировка приведёт к отрицательному остатку")
    item.quantity = new_qty
    t = WarehouseTransaction(
        tenant_id=claims.tenant_id,
        warehouse_item_id=item.id,
        transaction_type=TransactionType.ADJUSTMENT.value,
        quantity=abs(Decimal(str(body.quantity_delta))),
        price=None,
        employee_id=employee_id,
    )
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------
@router.get("/receipts", response_model=list[ReceiptDocumentSchema], responses=_auth)
async def list_receipts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    receipt_status: Optional[ReceiptStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    stmt = select(ReceiptDocument).order_by(ReceiptDocument.created_at.desc())
    if receipt_status is not None:
        stmt = stmt.where(ReceiptDocument.status == receipt_status.value)
    stmt = stmt.offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [await _serialize_receipt(db, r, claims) for r in rows]


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptDocumentSchema,
    responses={**_auth, **_404_receipt},
)
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    r = await db.get(ReceiptDocument, (claims.tenant_id, receipt_id))
    if r is None:
        raise NotFoundException("Накладная не найдена")
    return await _serialize_receipt(db, r, claims)


@router.post(
    "/receipts",
    response_model=ReceiptDocumentSchema,
    status_code=status.HTTP_201_CREATED,
    responses={**_write, **_400},
)
async def create_receipt(
    body: ReceiptDocumentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    if body.supplier_id is not None:
        if await db.get(Supplier, (claims.tenant_id, body.supplier_id)) is None:
            raise NotFoundException("Поставщик не найден")
    # Validate parts.
    for line in body.lines:
        if await db.get(Part, (claims.tenant_id, line.part_id)) is None:
            raise NotFoundException(f"Запчасть id={line.part_id} не найдена")

    number = await _next_receipt_number(db)
    r = ReceiptDocument(
        tenant_id=claims.tenant_id,
        number=number,
        document_date=body.document_date,
        supplier_id=body.supplier_id,
        supplier_document_number=body.supplier_document_number,
        supplier_document_date=body.supplier_document_date,
        status=ReceiptStatus.DRAFT.value,
    )
    db.add(r)
    await db.flush()
    for line in body.lines:
        db.add(ReceiptLine(
            tenant_id=claims.tenant_id,
            receipt_id=r.id,
            part_id=line.part_id,
            quantity=line.quantity,
            purchase_price=line.purchase_price,
            sale_price=line.sale_price,
        ))
    await db.flush()
    await db.refresh(r)
    return await _serialize_receipt(db, r, claims)


@router.put(
    "/receipts/{receipt_id}",
    response_model=ReceiptDocumentSchema,
    responses={**_write, **_400, **_404_receipt},
)
async def update_receipt(
    receipt_id: int,
    body: ReceiptDocumentUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    r = await db.get(ReceiptDocument, (claims.tenant_id, receipt_id))
    if r is None:
        raise NotFoundException("Накладная не найдена")
    if r.status != ReceiptStatus.DRAFT.value:
        raise BadRequestException("Можно редактировать только черновик")

    if body.document_date is not None:
        r.document_date = body.document_date
    if body.supplier_id is not None:
        if await db.get(Supplier, (claims.tenant_id, body.supplier_id)) is None:
            raise NotFoundException("Поставщик не найден")
        r.supplier_id = body.supplier_id
    if body.supplier_document_number is not None:
        r.supplier_document_number = body.supplier_document_number
    if body.supplier_document_date is not None:
        r.supplier_document_date = body.supplier_document_date
    if body.lines is not None:
        from sqlalchemy import delete as sa_delete
        await db.execute(sa_delete(ReceiptLine).where(ReceiptLine.receipt_id == r.id))
        for line in body.lines:
            db.add(ReceiptLine(
                tenant_id=claims.tenant_id,
                receipt_id=r.id,
                part_id=line.part_id,
                quantity=line.quantity,
                purchase_price=line.purchase_price,
                sale_price=line.sale_price,
            ))
    await db.flush()
    await db.refresh(r)
    return await _serialize_receipt(db, r, claims)


@router.post(
    "/receipts/{receipt_id}/post",
    response_model=ReceiptDocumentSchema,
    responses={**_write, **_400, **_404_receipt},
)
async def post_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_manager_or_admin),
):
    employee_id = _resolve_employee_id(claims)

    r = await db.get(ReceiptDocument, (claims.tenant_id, receipt_id))
    if r is None:
        raise NotFoundException("Накладная не найдена")
    if r.status == ReceiptStatus.POSTED.value:
        raise BadRequestException("Накладная уже проведена")

    lines = (
        await db.execute(
            select(ReceiptLine).where(ReceiptLine.receipt_id == r.id)
        )
    ).scalars().all()
    if not lines:
        raise BadRequestException("Накладная не содержит строк")

    for line in lines:
        # Find or create WarehouseItem for this part.
        item_row = (
            await db.execute(
                select(WarehouseItem).where(WarehouseItem.part_id == line.part_id)
            )
        ).scalar_one_or_none()
        if item_row is None:
            item_row = WarehouseItem(
                tenant_id=claims.tenant_id,
                part_id=line.part_id,
                quantity=Decimal(0),
                min_quantity=Decimal(0),
            )
            db.add(item_row)
            await db.flush()
        item_row.quantity = Decimal(str(item_row.quantity)) + Decimal(str(line.quantity))
        # Update part price.
        part = await db.get(Part, (claims.tenant_id, line.part_id))
        if part is not None:
            part.purchase_price_last = line.purchase_price
            part.price = line.sale_price
        # Create incoming transaction.
        db.add(WarehouseTransaction(
            tenant_id=claims.tenant_id,
            warehouse_item_id=item_row.id,
            transaction_type=TransactionType.INCOMING.value,
            quantity=line.quantity,
            price=line.purchase_price,
            receipt_id=r.id,
            employee_id=employee_id,
        ))

    r.status = ReceiptStatus.POSTED.value
    await db.flush()
    await db.refresh(r)
    return await _serialize_receipt(db, r, claims)


@router.post(
    "/receipts/{receipt_id}/unpost",
    response_model=ReceiptDocumentSchema,
    responses={**_write, **_400, **_404_receipt},
)
async def unpost_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(require_admin),
):
    """Откат проведения накладной. Только для администратора.

    Что делает:
    - Вычитает количество строк накладной из остатков (WarehouseItem.quantity);
      если остаток уходит в минус — клампим в 0 (защита от случайных списаний
      между проведением и откатом).
    - Удаляет связанные WarehouseTransaction (incoming).
    - Меняет статус накладной на draft, чтобы её можно было отредактировать
      и провести заново через обычные эндпоинты.

    Что НЕ откатывает (нет истории):
    - Part.purchase_price_last и Part.price — на момент проведения они были
      перезаписаны и предыдущие значения не сохранены. После повторного
      проведения они снова обновятся под текущие цены в накладной.
    """
    from sqlalchemy import delete as sa_delete

    r = await db.get(ReceiptDocument, (claims.tenant_id, receipt_id))
    if r is None:
        raise NotFoundException("Накладная не найдена")
    if r.status != ReceiptStatus.POSTED.value:
        raise BadRequestException("Снять с проведения можно только проведённую накладную")

    lines = (await db.execute(
        select(ReceiptLine).where(ReceiptLine.receipt_id == r.id)
    )).scalars().all()

    for line in lines:
        item_row = (
            await db.execute(
                select(WarehouseItem).where(WarehouseItem.part_id == line.part_id)
            )
        ).scalar_one_or_none()
        if item_row is not None:
            new_qty = Decimal(str(item_row.quantity)) - Decimal(str(line.quantity))
            if new_qty < 0:
                new_qty = Decimal(0)
            item_row.quantity = new_qty

    await db.execute(
        sa_delete(WarehouseTransaction).where(WarehouseTransaction.receipt_id == r.id)
    )

    r.status = ReceiptStatus.DRAFT.value
    await db.flush()
    await db.refresh(r)
    return await _serialize_receipt(db, r, claims)


@router.get(
    "/receipts/{receipt_id}/print",
    responses={**_auth, **_404_receipt},
)
async def print_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    """PDF приходной накладной. pdf_service использует sync Session,
    поэтому запускаем в threadpool с отдельной sync-сессией под тем же тенантом."""
    # Лёгкая проверка существования в async-сессии — чтобы 404 пришёл сразу.
    if await db.get(ReceiptDocument, (claims.tenant_id, receipt_id)) is None:
        raise NotFoundException("Накладная не найдена")

    def _render() -> bytes:
        with sync_tenant_session(claims.tenant_id) as sync_db:
            return generate_receipt_pdf(sync_db, receipt_id)

    pdf_bytes = await run_in_threadpool(_render)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="receipt-{receipt_id}.pdf"',
        },
    )


# ---------------------------------------------------------------------------
# Supplier receipts report
# ---------------------------------------------------------------------------
@router.get(
    "/reports/supplier-receipts",
    response_model=SupplierReceiptsReport,
    responses=_auth,
)
async def supplier_receipts_report(
    supplier_id: int = Query(...),
    date_from: Optional[date_type] = Query(None),
    date_to: Optional[date_type] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    claims: TenantClaims = Depends(get_current_claims),
):
    stmt = (
        select(ReceiptDocument)
        .where(ReceiptDocument.supplier_id == supplier_id)
        .order_by(ReceiptDocument.document_date.desc())
    )
    if date_from:
        stmt = stmt.where(ReceiptDocument.document_date >= date_from)
    if date_to:
        stmt = stmt.where(ReceiptDocument.document_date <= date_to)
    rows = (await db.execute(stmt)).scalars().all()
    receipts = [await _serialize_receipt(db, r, claims) for r in rows]
    total_amount = sum((Decimal(str(r["total_amount"])) for r in receipts), Decimal(0))
    return {
        "receipts": receipts,
        "total_count": len(receipts),
        "total_amount": total_amount,
    }
