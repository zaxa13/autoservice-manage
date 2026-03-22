from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.warehouse import ReceiptDocument, ReceiptLine, ReceiptStatus, TransactionType
from app.schemas.warehouse import (
    WarehouseItem as WarehouseItemSchema,
    WarehouseItemCreate,
    WarehouseItemUpdate,
    WarehouseTransaction as WarehouseTransactionSchema,
    WarehouseTransactionCreate,
    WarehouseTransactionList,
    WarehouseAdjustmentCreate,
)
from app.schemas.receipt import (
    ReceiptDocument as ReceiptDocumentSchema,
    ReceiptDocumentCreate,
    ReceiptDocumentUpdate,
    SupplierReceiptsReport,
)
from app.schemas.responses import ErrorResponse
from app.services.warehouse_service import (
    create_warehouse_item,
    add_incoming_transaction,
    get_low_stock_items,
    create_receipt_document,
    post_receipt_document,
    get_transactions,
    get_supplier_receipts_report,
    create_adjustment,
)
from app.core.permissions import require_manager_or_admin
from app.core.exceptions import NotFoundException, BadRequestException

router = APIRouter()

_auth = {401: {"model": ErrorResponse, "description": "Не авторизован"}}
_write = {**_auth, 403: {"model": ErrorResponse, "description": "Недостаточно прав"}}
_404_item = {404: {"model": ErrorResponse, "description": "Позиция склада не найдена"}}
_404_receipt = {404: {"model": ErrorResponse, "description": "Накладная не найдена"}}


@router.get(
    "/items",
    response_model=List[WarehouseItemSchema],
    status_code=status.HTTP_200_OK,
    summary="Позиции склада",
    description=(
        "Список позиций склада с пагинацией. "
        "Фильтрация по артикулу (точное совпадение после нормализации)."
    ),
    responses=_auth,
)
def get_warehouse_items(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(500, ge=1, le=1000, description="Максимум записей"),
    part_number: Optional[str] = Query(None, description="Фильтр по артикулу (точное совпадение)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.warehouse import WarehouseItem
    from app.models.part import Part
    q = db.query(WarehouseItem).join(Part, WarehouseItem.part_id == Part.id)
    if part_number is not None:
        search = part_number.strip().upper()
        if search:
            q = q.filter(func.upper(func.trim(Part.part_number)) == search)
    items = q.order_by(Part.part_number).offset(skip).limit(limit).all()
    return items


@router.get(
    "/items/{item_id}",
    response_model=WarehouseItemSchema,
    status_code=status.HTTP_200_OK,
    summary="Позиция склада по ID",
    description="Возвращает одну позицию склада по ID.",
    responses={**_auth, **_404_item},
)
def get_warehouse_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.warehouse import WarehouseItem

    item = db.query(WarehouseItem).filter(WarehouseItem.id == item_id).first()
    if not item:
        raise NotFoundException("Позиция склада не найдена")
    return item


@router.post(
    "/items",
    response_model=WarehouseItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать позицию склада",
    description="Создание новой складской позиции для запчасти. Доступно менеджеру и администратору.",
    responses=_write,
)
def create_item(
    item_create: WarehouseItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    item = create_warehouse_item(db, item_create)
    return item


@router.post(
    "/transactions/incoming",
    response_model=WarehouseTransactionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Приход на склад",
    description="Оформление прихода на склад. Увеличивает остаток позиции. Требует привязку к сотруднику.",
    responses={**_write, 400: {"model": ErrorResponse, "description": "Не привязан сотрудник"}},
)
def create_incoming_transaction(
    transaction_create: WarehouseTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник",
        )

    transaction = add_incoming_transaction(db, transaction_create, current_user.employee_id)
    return transaction


@router.get(
    "/low-stock",
    response_model=List[WarehouseItemSchema],
    status_code=status.HTTP_200_OK,
    summary="Позиции с низким остатком",
    description="Возвращает позиции склада, остаток которых ниже минимального порога.",
    responses=_auth,
)
def get_low_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = get_low_stock_items(db)
    return items


@router.get(
    "/transactions",
    response_model=List[WarehouseTransactionList],
    status_code=status.HTTP_200_OK,
    summary="Журнал движений склада",
    description=(
        "Журнал складских операций с фильтрацией по дате, типу, запчасти, заказу или накладной."
    ),
    responses=_auth,
)
def list_transactions(
    date_from: Optional[date] = Query(None, description="Дата начала периода"),
    date_to: Optional[date] = Query(None, description="Дата конца периода"),
    transaction_type: Optional[TransactionType] = Query(None, description="Тип операции"),
    part_id: Optional[int] = Query(None, description="ID запчасти"),
    order_id: Optional[int] = Query(None, description="ID заказ-наряда"),
    receipt_id: Optional[int] = Query(None, description="ID накладной"),
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_transactions(
        db,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        part_id=part_id,
        order_id=order_id,
        receipt_id=receipt_id,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/transactions/adjustment",
    response_model=WarehouseTransactionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Корректировка остатка",
    description=(
        "Ручная корректировка количества на складе. "
        "Положительное значение — увеличение, отрицательное — списание. "
        "Требует привязку к сотруднику."
    ),
    responses={**_write, 400: {"model": ErrorResponse, "description": "Не привязан сотрудник"}},
)
def adjustment(
    payload: WarehouseAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник",
        )
    return create_adjustment(db, payload, current_user.employee_id)


@router.get(
    "/reports/supplier-receipts",
    response_model=SupplierReceiptsReport,
    status_code=status.HTTP_200_OK,
    summary="Отчёт по приходу от поставщика",
    description=(
        "Отчёт для сверки: все накладные от конкретного поставщика за период. "
        "Фильтрация по дате документа накладной."
    ),
    responses=_auth,
)
def get_supplier_receipts_report_endpoint(
    supplier_id: int = Query(..., description="ID поставщика"),
    date_from: Optional[date] = Query(None, description="Дата начала периода"),
    date_to: Optional[date] = Query(None, description="Дата конца периода"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = get_supplier_receipts_report(db, supplier_id=supplier_id, date_from=date_from, date_to=date_to)
    return SupplierReceiptsReport(
        receipts=data["receipts"],
        total_count=data["total_count"],
        total_amount=data["total_amount"],
    )


@router.get(
    "/receipts",
    response_model=List[ReceiptDocumentSchema],
    status_code=status.HTTP_200_OK,
    summary="Список приходных накладных",
    description="Список накладных с фильтрацией по статусу. Строки подгружаются для расчёта итого.",
    responses=_auth,
)
def list_receipts(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=500, description="Максимум записей"),
    receipt_status: Optional[ReceiptStatus] = Query(None, alias="status", description="Фильтр по статусу (draft / posted)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import joinedload
    q = (
        db.query(ReceiptDocument)
        .options(
            joinedload(ReceiptDocument.lines).joinedload(ReceiptLine.part),
        )
        .order_by(ReceiptDocument.created_at.desc())
    )
    if receipt_status is not None:
        q = q.filter(ReceiptDocument.status == receipt_status)
    return q.offset(skip).limit(limit).all()


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptDocumentSchema,
    status_code=status.HTTP_200_OK,
    summary="Накладная по ID",
    description="Возвращает приходную накладную со строками. Возвращает 404 если не найдена.",
    responses={**_auth, **_404_receipt},
)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import joinedload
    r = (
        db.query(ReceiptDocument)
        .options(
            joinedload(ReceiptDocument.lines).joinedload(ReceiptLine.part),
        )
        .filter(ReceiptDocument.id == receipt_id)
        .first()
    )
    if not r:
        raise NotFoundException("Накладная не найдена")
    return r


@router.post(
    "/receipts",
    response_model=ReceiptDocumentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать приходную накладную",
    description="Создание приходной накладной в статусе «Черновик». Доступно менеджеру и администратору.",
    responses=_write,
)
def create_receipt(
    payload: ReceiptDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    return create_receipt_document(db, payload)


@router.put(
    "/receipts/{receipt_id}",
    response_model=ReceiptDocumentSchema,
    status_code=status.HTTP_200_OK,
    summary="Обновить черновик накладной",
    description=(
        "Обновление приходной накладной в статусе «Черновик». "
        "Если переданы строки — все существующие заменяются. "
        "Редактирование проведённых накладных запрещено (400)."
    ),
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Можно редактировать только черновик"},
        **_404_receipt,
    },
)
def update_receipt(
    receipt_id: int,
    payload: ReceiptDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    r = db.query(ReceiptDocument).filter(ReceiptDocument.id == receipt_id).first()
    if not r:
        raise NotFoundException("Накладная не найдена")
    if r.status != ReceiptStatus.DRAFT:
        raise BadRequestException("Можно редактировать только черновик")
    if payload.document_date is not None:
        r.document_date = payload.document_date
    if payload.supplier_id is not None:
        r.supplier_id = payload.supplier_id
    if payload.lines is not None:
        from app.models.warehouse import ReceiptLine as ReceiptLineModel
        db.query(ReceiptLineModel).filter(ReceiptLineModel.receipt_id == receipt_id).delete()
        for line in payload.lines:
            rl = ReceiptLineModel(
                receipt_id=r.id,
                part_id=line.part_id,
                quantity=line.quantity,
                purchase_price=line.purchase_price,
                sale_price=line.sale_price,
            )
            db.add(rl)
    db.commit()
    db.refresh(r)
    return r


@router.post(
    "/receipts/{receipt_id}/post",
    response_model=ReceiptDocumentSchema,
    status_code=status.HTTP_200_OK,
    summary="Провести накладную",
    description=(
        "Проведение приходной накладной: статус меняется на POSTED, "
        "создаются складские транзакции, обновляются остатки и закупочные цены запчастей. "
        "Требует привязку к сотруднику."
    ),
    responses={
        **_write,
        400: {"model": ErrorResponse, "description": "Не привязан сотрудник или накладная уже проведена"},
        **_404_receipt,
    },
)
def post_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    if not current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не привязан сотрудник",
        )
    return post_receipt_document(db, receipt_id, current_user.employee_id)


@router.get(
    "/receipts/{receipt_id}/print",
    status_code=status.HTTP_200_OK,
    summary="PDF приходной накладной",
    description="Генерирует и возвращает PDF-файл приходной накладной.",
    responses={**_auth, **_404_receipt},
)
def print_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.pdf_service import generate_receipt_pdf

    pdf_bytes = generate_receipt_pdf(db, receipt_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=receipt-{receipt_id}.pdf"},
    )
