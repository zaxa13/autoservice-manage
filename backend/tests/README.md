# Phase 2 acceptance tests

Покрывают инварианты shared-DB архитектуры (схема `app` + RLS + composite
PK/FK + tenant-aware pooling).

## Категории

| Файл | Что проверяет |
|---|---|
| `phase2/test_python_models.py` | Статический контракт моделей: `TenantMixin`, composite PK, индексы и UNIQUE с `tenant_id` первым, composite FK |
| `phase2/test_db_schema.py` | DB-introspection: таблицы в `app`, NOT NULL `tenant_id`, ключи и FK составные |
| `phase2/test_rls_policies.py` | `pg_class.relrowsecurity` / `relforcerowsecurity`, `pg_policies` — на каждой бизнес-таблице |
| `phase2/test_rls_runtime.py` | Реальная RLS-изоляция: SELECT/INSERT/UPDATE/DELETE между двумя тенантами |
| `phase2/test_pgbouncer.py` | `SET LOCAL` сбрасывается на границе транзакции в transaction-pool, не утекает в следующий запрос |
| `phase2/test_tenant_counter.py` | Атомарный `UPDATE … RETURNING` для генерации номеров заказов |

## Пререкизиты

- Поднят sandbox из Фазы 1: postgres + pgbouncer (см. `infrastructure/db/init/01-init.sh`).
- Применена миграция `0001_shared_db_initial`.
- Доступны три connection-URL для разных ролей.

## Запуск

```bash
export TEST_PG_SUPER_URL='postgresql://postgres:<pw>@host:5432/autoworks'
export TEST_PG_MIGRATOR_URL='postgresql://migrator_app:<pw>@host:6432/autoworks_session'
export TEST_PG_TENANT_URL='postgresql://tenant_app:<pw>@host:6432/autoworks_tx'

cd backend
pytest tests/phase2 -v
```

Любой URL пустой / нерабочий → соответствующие тесты помечаются как
skipped с понятным сообщением.

## Гарантии и не-гарантии

- Тесты **изолированы**: перед каждым тестом fixture `clean_db` чистит
  бизнес-таблицы под ролью migrator.
- Тесты **детерминированы**: фиксированные UUID `ALPHA` / `BETA` для тенантов.
- Тесты **не моки**: всё работает против настоящего Postgres + PgBouncer.
- Тесты **не покрывают application-слой** (`api/`, `services/`) — это
  Фаза 3.
