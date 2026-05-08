# Phase 3 follow-up: миграция оставшихся 17 роутеров

В первом коммите Фазы 3 мигрированы только роутеры:
- `auth_me.py` — `/auth/me` (без login flow, тот переносится в platform-api / Фаза 4-5)
- `customers.py` — эталонный CRUD-роутер на shared-DB (use as a template)

Все остальные старые роутеры в `app/api/v1/` физически существуют,
но **не подключены** в `api_router` и **сломаны импортами** (старый sync
SQLAlchemy + удалённые поля моделей). До их миграции tenant-app поднимется,
но эти эндпоинты будут возвращать 404.

## Список к миграции

| Файл | Объём | Сложность | Зависимости |
|---|---|---|---|
| `vehicles.py` | средний | FK на customers/brands/models | customers, vehicle_brands |
| `vehicle_brands.py` | малый | CRUD | — |
| `employees.py` | малый | CRUD + auth.users link | users |
| `works.py` | малый | CRUD | — |
| `parts.py` | малый | CRUD | — |
| `suppliers.py` | малый | CRUD | — |
| `orders.py` | большой | composite FK + order_works/parts | vehicles, employees |
| `payments.py` | средний | FK orders + ЮКасса webhook | orders |
| `warehouse.py` | большой | многотабличный (receipts/items/transactions) | parts, suppliers |
| `salary.py` | средний | расчёт по периодам | employees, orders |
| `cashflow.py` | средний | счета + категории + транзакции | orders, salary, payments |
| `appointments.py` | средний | FK на vehicle/employee/post/order | appointment_posts, vehicles, orders |
| `appointment_posts.py` | малый | CRUD | — |
| `dashboard.py` | средний | агрегаты по нескольким таблицам | orders, customers, vehicles |
| `reports.py` | большой | сложные SQL-агрегаты | большинство моделей |
| `integrations.py` | малый | CRUD логов | — |
| `settings_api.py` | малый | KV-store | — |
| `users.py` | малый | управление учётками внутри тенанта | — |

## Эталонный паттерн миграции (по customers.py)

1. **Импорты**: `Session` → `AsyncSession`, `get_db` → `get_tenant_db`,
   `get_current_user` → `get_current_claims`, `User` модель → `TenantClaims`.
2. **Endpoint signatures**: каждый `def ...` → `async def`.
3. **Зависимости**: `db: Session = Depends(get_db)` →
   `db: AsyncSession = Depends(get_tenant_db)`. Для роли —
   `claims: TenantClaims = Depends(require_manager_or_admin)`.
4. **PK lookup**: composite PK `(tenant_id, id)`, поэтому
   `db.query(Model).filter(Model.id == x).first()` →
   `await db.get(Model, (claims.tenant_id, x))`.
5. **Списки/фильтры**: `db.query(Model).filter(...).all()` →
   `(await db.execute(select(Model).where(...))).scalars().all()`.
6. **Вставка**: при `Model(tenant_id=claims.tenant_id, **body.model_dump())`.
   `db.add(...)`, потом `await db.flush()` и `await db.refresh(obj)`. Commit
   делает `tenant_session` на выходе из CM.
7. **`tenant_id` в WHERE**: НЕ нужен — RLS отфильтрует.
8. **`tenant_id` в INSERT**: нужен (или server_default — но мы пока без него).
9. **403/404**: `from app.core.exceptions import NotFoundException` /
   `from app.core.permissions import require_admin`.
10. **Тесты**: смотри `tests/phase3/test_customers_endpoint.py` — эталон
    для каждого роутера должен быть свой `test_*_endpoint.py` с покрытием:
    list / get / create / update / delete + RLS-isolation между тенантами.

## Порядок миграции (по зависимостям)

1. **Wave 1** (нет FK): `vehicle_brands`, `works`, `parts`, `suppliers`,
   `appointment_posts`, `settings_api`, `integrations`, `users`, `employees`.
2. **Wave 2**: `vehicles` (зависит от brands/customers), `orders`
   (зависит от vehicles/employees), `cashflow.accounts` + `categories`.
3. **Wave 3**: `payments`, `warehouse` (receipts/items/transactions),
   `appointments`, `salary`, `cashflow.transactions`.
4. **Wave 4**: `dashboard`, `reports`.

Каждый роутер коммитится отдельно: `feat(api): мигрировать <name> на shared-DB`.
