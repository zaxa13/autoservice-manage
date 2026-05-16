"""Глобализация vehicle_brands / vehicle_models + сид марок

vehicle_brands и vehicle_models перестают быть per-tenant и становятся
глобальным read-only справочником:
  - снимается RLS (DROP POLICY tenant_isolation, DISABLE RLS)
  - дропаются составные PK и FK через tenant_id
  - удаляется колонка tenant_id
  - новые одноколоночные PK / UNIQUE / FK
  - FK у app.vehicles на бренд/модель пересобираются на одноколоночные

Параллельно из brands_filtered.json вставляются 126 марок.

Таблицы на момент миграции пустые (Phase 7 ещё не наполняли данными),
поэтому DROP COLUMN tenant_id не требует backfill.

tenant_app: только SELECT (раньше у него было INSERT/UPDATE/DELETE через
ALTER DEFAULT PRIVILEGES — справочник теперь read-only).

Revision ID: 0003_global_vehicle_catalog
Revises: 0002_global_email_login_function
Create Date: 2026-05-16
"""
import sqlalchemy as sa
from alembic import op


revision = "0003_global_vehicle_catalog"
down_revision = "0002_global_email_login_function"
branch_labels = None
depends_on = None


BRANDS: list[str] = [
    "AC", "Acura", "AITO", "Alfa Romeo", "Alpina", "Alpine", "Aston Martin",
    "Audi", "Aurus", "Avatr", "BAIC", "Bajaj", "BAW", "Belgee", "Bentley",
    "BMW", "Bugatti", "Buick", "BYD", "Cadillac", "Changan", "Chery",
    "Chevrolet", "Chrysler", "Citroen", "Cupra", "Dacia", "Daewoo", "Daihatsu",
    "Datsun", "DeLorean", "Dodge", "Dongfeng", "Evolute", "EXEED", "FAW",
    "Ferrari", "Fiat", "Fisker", "Ford", "Foton", "GAC", "Geely", "Genesis",
    "GMC", "Great Wall", "Haval", "Honda", "Hongqi", "Huanghai", "Huazi",
    "Hummer", "Hyundai", "Infiniti", "Isuzu", "IVECO", "JAC", "Jaecoo",
    "Jaguar", "Jeep", "Jetour", "Jetta", "JMC", "Kaiyi", "KGM", "Kia",
    "Knewstar", "Lamborghini", "Lancia", "Land Rover", "Lexus", "Li", "Lifan",
    "Lincoln", "Livan", "Lotus", "Lynk & Co", "Marussia", "Maserati",
    "Maybach", "Mazda", "McLaren", "Mercedes-Benz", "MG", "MINI", "Mitsubishi",
    "Nissan", "OMODA", "Opel", "Peugeot", "Plymouth", "Polestar", "Pontiac",
    "Porsche", "RAM", "Ravon", "Renault", "Renault Samsung", "Rolls-Royce",
    "Rover", "Saab", "SEAT", "Skoda", "Smart", "Solaris", "Sollers",
    "SsangYong", "Subaru", "Suzuki", "SWM", "Tank", "TENET", "Tesla", "Toyota",
    "Vauxhall", "Volkswagen", "Volvo", "Vortex", "Voyah", "Xiaomi", "Zeekr",
    "ГАЗ", "Лада", "Москвич", "ТагАЗ", "УАЗ",
]


def upgrade() -> None:
    # 1. Снять RLS на бренд/модель.
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON app.vehicle_brands;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON app.vehicle_models;")
    op.execute("ALTER TABLE app.vehicle_brands NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE app.vehicle_models NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE app.vehicle_brands DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE app.vehicle_models DISABLE ROW LEVEL SECURITY;")

    # 2. Снести FK с/на vehicle_brands/models.
    op.execute(
        "ALTER TABLE app.vehicle_models "
        "DROP CONSTRAINT IF EXISTS fk_vehicle_models_brand;"
    )
    op.execute("ALTER TABLE app.vehicles DROP CONSTRAINT IF EXISTS fk_vehicles_brand;")
    op.execute("ALTER TABLE app.vehicles DROP CONSTRAINT IF EXISTS fk_vehicles_model;")

    # 3. Снести старые PK / UNIQUE / INDEX.
    op.execute(
        "ALTER TABLE app.vehicle_brands "
        "DROP CONSTRAINT IF EXISTS uq_vehicle_brands_tenant_name;"
    )
    op.execute(
        "ALTER TABLE app.vehicle_brands DROP CONSTRAINT IF EXISTS vehicle_brands_pkey;"
    )
    op.execute(
        "ALTER TABLE app.vehicle_models "
        "DROP CONSTRAINT IF EXISTS uq_vehicle_models_tenant_brand_name;"
    )
    op.execute(
        "ALTER TABLE app.vehicle_models DROP CONSTRAINT IF EXISTS vehicle_models_pkey;"
    )
    op.execute("DROP INDEX IF EXISTS app.ix_vehicle_models_tenant_brand;")

    # 4. Уронить tenant_id.
    op.execute("ALTER TABLE app.vehicle_brands DROP COLUMN IF EXISTS tenant_id;")
    op.execute("ALTER TABLE app.vehicle_models DROP COLUMN IF EXISTS tenant_id;")

    # 5. Новые PK / UNIQUE / INDEX / FK.
    op.execute(
        "ALTER TABLE app.vehicle_brands "
        "ADD CONSTRAINT vehicle_brands_pkey PRIMARY KEY (id);"
    )
    op.execute(
        "ALTER TABLE app.vehicle_brands "
        "ADD CONSTRAINT uq_vehicle_brands_name UNIQUE (name);"
    )
    op.execute(
        "ALTER TABLE app.vehicle_models "
        "ADD CONSTRAINT vehicle_models_pkey PRIMARY KEY (id);"
    )
    op.execute(
        "ALTER TABLE app.vehicle_models "
        "ADD CONSTRAINT uq_vehicle_models_brand_name UNIQUE (brand_id, name);"
    )
    op.execute(
        "CREATE INDEX ix_vehicle_models_brand ON app.vehicle_models(brand_id);"
    )
    op.execute(
        "ALTER TABLE app.vehicle_models ADD CONSTRAINT fk_vehicle_models_brand "
        "FOREIGN KEY (brand_id) REFERENCES app.vehicle_brands(id) ON DELETE CASCADE;"
    )
    op.execute(
        "ALTER TABLE app.vehicles ADD CONSTRAINT fk_vehicles_brand "
        "FOREIGN KEY (brand_id) REFERENCES app.vehicle_brands(id) ON DELETE RESTRICT;"
    )
    op.execute(
        "ALTER TABLE app.vehicles ADD CONSTRAINT fk_vehicles_model "
        "FOREIGN KEY (model_id) REFERENCES app.vehicle_models(id) ON DELETE RESTRICT;"
    )

    # 6. tenant_app — только чтение справочника.
    op.execute(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE "
        "ON app.vehicle_brands, app.vehicle_models FROM tenant_app;"
    )
    op.execute(
        "GRANT SELECT ON app.vehicle_brands, app.vehicle_models TO tenant_app;"
    )

    # 7. Сид марок.
    brands_table = sa.table(
        "vehicle_brands",
        sa.column("name", sa.String),
        schema="app",
    )
    op.bulk_insert(brands_table, [{"name": n} for n in BRANDS])


def downgrade() -> None:
    raise NotImplementedError("Глобализация vehicle catalog — one-way migration")
