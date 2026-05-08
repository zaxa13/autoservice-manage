"""Runtime RLS-изоляция: tenant_app не видит и не трогает чужие строки."""
from __future__ import annotations

import uuid

import psycopg2
import pytest

from .conftest import TENANT_ALPHA, TENANT_BETA, tenant_txn


# ---------------------------------------------------------------------------
# Helpers: insert under migrator (BYPASSRLS) для удобной "загрузки фикстур"
# ---------------------------------------------------------------------------
def _seed_customer(migrator_conn, tenant_id: uuid.UUID, name: str, phone: str = "+700-000") -> int:
    """Возвращает id вставленного customer'а."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app.customers (tenant_id, full_name, phone) "
            "VALUES (%s, %s, %s) RETURNING id",
            (str(tenant_id), name, phone),
        )
        cust_id = cur.fetchone()[0]
    migrator_conn.commit()
    return cust_id


def _count_customers_in_txn(tenant_conn, tenant_id: uuid.UUID) -> int:
    with tenant_txn(tenant_conn, tenant_id) as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# SELECT isolation
# ---------------------------------------------------------------------------
def test_tenant_app_sees_zero_rows_without_set_local(tenant_conn, migrator_conn):
    _seed_customer(migrator_conn, TENANT_ALPHA, "Alpha")
    # Без BEGIN+SET LOCAL — current_tenant() = NULL → policy fail-closed.
    with tenant_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app.customers")
        assert cur.fetchone()[0] == 0


def test_alpha_sees_only_alpha_rows(tenant_conn, migrator_conn):
    _seed_customer(migrator_conn, TENANT_ALPHA, "Alpha-1")
    _seed_customer(migrator_conn, TENANT_ALPHA, "Alpha-2")
    _seed_customer(migrator_conn, TENANT_BETA, "Beta-1")
    assert _count_customers_in_txn(tenant_conn, TENANT_ALPHA) == 2
    assert _count_customers_in_txn(tenant_conn, TENANT_BETA) == 1


def test_alpha_cannot_see_beta_row_by_id(tenant_conn, migrator_conn):
    beta_id = _seed_customer(migrator_conn, TENANT_BETA, "Beta-secret")
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute("SELECT count(*) FROM app.customers WHERE id = %s", (beta_id,))
        assert cur.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# INSERT WITH CHECK
# ---------------------------------------------------------------------------
def test_insert_with_foreign_tenant_id_is_rejected(tenant_conn):
    # RLS WITH CHECK раньше думал что это CheckViolation, но Postgres
    # бросает SQLSTATE 42501 (insufficient_privilege) для row-level security.
    with pytest.raises(psycopg2.errors.InsufficientPrivilege) as exc:
        with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
            cur.execute(
                "INSERT INTO app.customers (tenant_id, full_name, phone) "
                "VALUES (%s, %s, %s)",
                (str(TENANT_BETA), "evil", "+700"),
            )
    assert "row-level security" in str(exc.value).lower()


def test_insert_with_own_tenant_id_works(tenant_conn):
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute(
            "INSERT INTO app.customers (tenant_id, full_name, phone) "
            "VALUES (%s, %s, %s)",
            (str(TENANT_ALPHA), "alpha-self", "+700"),
        )
    assert _count_customers_in_txn(tenant_conn, TENANT_ALPHA) == 1


def test_insert_without_set_local_is_rejected(tenant_conn):
    """current_tenant()=NULL → WITH CHECK не проходит (SQLSTATE 42501)."""
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        with tenant_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app.customers (tenant_id, full_name, phone) "
                "VALUES (%s, %s, %s)",
                (str(TENANT_ALPHA), "stranger", "+700"),
            )
            tenant_conn.commit()


# ---------------------------------------------------------------------------
# UPDATE / DELETE isolation
# ---------------------------------------------------------------------------
def test_alpha_cannot_update_beta_row(tenant_conn, migrator_conn):
    beta_id = _seed_customer(migrator_conn, TENANT_BETA, "Beta-untouchable")
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute(
            "UPDATE app.customers SET full_name='hacked' WHERE id=%s",
            (beta_id,),
        )
        assert cur.rowcount == 0  # RLS отфильтровал, UPDATE затронул 0 строк
    # Проверяем что строка не изменилась.
    with migrator_conn.cursor() as cur:
        cur.execute("SELECT full_name FROM app.customers WHERE id=%s", (beta_id,))
        assert cur.fetchone()[0] == "Beta-untouchable"


def test_alpha_cannot_change_tenant_id_to_beta(tenant_conn, migrator_conn):
    """UPDATE WITH CHECK защищает от смены tenant_id на чужой (SQLSTATE 42501)."""
    alpha_id = _seed_customer(migrator_conn, TENANT_ALPHA, "Alpha-trying-escape")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
            cur.execute(
                "UPDATE app.customers SET tenant_id=%s WHERE id=%s",
                (str(TENANT_BETA), alpha_id),
            )


def test_alpha_cannot_delete_beta_row(tenant_conn, migrator_conn):
    beta_id = _seed_customer(migrator_conn, TENANT_BETA, "Beta-undeletable")
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        cur.execute("DELETE FROM app.customers WHERE id=%s", (beta_id,))
        assert cur.rowcount == 0
    with migrator_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app.customers WHERE id=%s", (beta_id,))
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Composite FK = физическая защита от cross-tenant ссылок
# ---------------------------------------------------------------------------
def test_composite_fk_blocks_cross_tenant_reference(migrator_conn):
    """Vehicle Beta не может ссылаться на customer Alpha — composite FK
    требует совпадения tenant_id+customer_id, а такой строки в customers нет.
    Проверяем под migrator (BYPASSRLS), чтобы изолировать FK от RLS."""
    alpha_cust = _seed_customer(migrator_conn, TENANT_ALPHA, "Alpha-cust")

    # Бренды/модели нужны для FK vehicles — создаём в Beta.
    with migrator_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app.vehicle_brands (tenant_id, name) VALUES (%s, %s) RETURNING id",
            (str(TENANT_BETA), "TestBrand"),
        )
        brand_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO app.vehicle_models (tenant_id, brand_id, name) "
            "VALUES (%s, %s, %s) RETURNING id",
            (str(TENANT_BETA), brand_id, "TestModel"),
        )
        model_id = cur.fetchone()[0]
    migrator_conn.commit()

    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        with migrator_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app.vehicles "
                "(tenant_id, brand_id, model_id, customer_id) "
                "VALUES (%s, %s, %s, %s)",
                (str(TENANT_BETA), brand_id, model_id, alpha_cust),
            )
            migrator_conn.commit()
    migrator_conn.rollback()


def test_composite_fk_allows_same_tenant_reference(migrator_conn):
    cust = _seed_customer(migrator_conn, TENANT_ALPHA, "Alpha-cust2")
    with migrator_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app.vehicle_brands (tenant_id, name) VALUES (%s, %s) RETURNING id",
            (str(TENANT_ALPHA), "Brand-Alpha"),
        )
        brand_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO app.vehicle_models (tenant_id, brand_id, name) "
            "VALUES (%s, %s, %s) RETURNING id",
            (str(TENANT_ALPHA), brand_id, "Model-Alpha"),
        )
        model_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO app.vehicles "
            "(tenant_id, brand_id, model_id, customer_id, license_plate) "
            "VALUES (%s, %s, %s, %s, 'A001') RETURNING id",
            (str(TENANT_ALPHA), brand_id, model_id, cust),
        )
        assert cur.fetchone()[0] is not None
    migrator_conn.commit()


# ---------------------------------------------------------------------------
# search_path: tenant_app по умолчанию резолвит без префикса
# ---------------------------------------------------------------------------
def test_tenant_app_resolves_unqualified_table_name(tenant_conn, migrator_conn):
    _seed_customer(migrator_conn, TENANT_ALPHA, "schema-resolve")
    with tenant_txn(tenant_conn, TENANT_ALPHA) as cur:
        # Без префикса app. — должен сработать через search_path
        cur.execute("SELECT count(*) FROM customers")
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# UNIQUE per-tenant: одинаковые значения в разных тенантах допустимы
# ---------------------------------------------------------------------------
# NOT NULL колонки users (is_active, password_must_be_changed) в моделях
# имеют клиентский default через SQLAlchemy — для raw SQL передаём явно.
_USERS_INSERT = (
    "INSERT INTO app.users "
    "(tenant_id, username, email, password_hash, role, "
    " is_active, password_must_be_changed) "
    "VALUES (%s, %s, %s, %s, %s, true, false)"
)


def test_unique_email_is_per_tenant(migrator_conn):
    """Один и тот же email может быть у пользователя в Alpha и в Beta."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            _USERS_INSERT,
            (str(TENANT_ALPHA), "admin", "shared@example.com", "x", "admin"),
        )
        cur.execute(
            _USERS_INSERT,
            (str(TENANT_BETA), "admin", "shared@example.com", "x", "admin"),
        )
    migrator_conn.commit()


def test_unique_email_collision_within_same_tenant(migrator_conn):
    with migrator_conn.cursor() as cur:
        cur.execute(
            _USERS_INSERT,
            (str(TENANT_ALPHA), "u1", "dup@example.com", "x", "admin"),
        )
    migrator_conn.commit()
    with pytest.raises(psycopg2.errors.UniqueViolation):
        with migrator_conn.cursor() as cur:
            cur.execute(
                _USERS_INSERT,
                (str(TENANT_ALPHA), "u2", "dup@example.com", "x", "manager"),
            )
            migrator_conn.commit()
    migrator_conn.rollback()
