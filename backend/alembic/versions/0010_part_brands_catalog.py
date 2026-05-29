"""part_brands: глобальный справочник + parts.brand_id FK

Аналогично vehicle_brands (миграция 0003): глобальная read-only таблица,
RLS не включаем, tenant_app получает только SELECT. На parts добавляем
nullable FK brand_id, существующий free-text parts.brand оставляем как
есть и бекфилим brand_id по совпадению имени без учёта регистра.

Revision ID: 0010_part_brands_catalog
Revises: 0009_perf_indexes
Create Date: 2026-05-29
"""
import sqlalchemy as sa
from alembic import op


revision = "0010_part_brands_catalog"
down_revision = "0009_perf_indexes"
branch_labels = None
depends_on = None


# Сид взят из практического разбора брендов запчастей (drive2 статья),
# дедуплицирован и нормализован под единое написание.
PART_BRANDS: list[str] = [
    "555",
    "ABS", "Airtex", "Ajusa", "AKG", "Alko", "Api", "Arvintesh", "Asashi",
    "ASVA", "Ate", "ATS", "Autofren", "AVA",
    "B-Tech", "Bando", "Behr", "Bendix", "Beru", "Bilstein", "Bodyparts",
    "Boge", "Bosal", "Bosch", "Brembo", "Bremi",
    "CarGo", "Champion", "ClimAIr", "Contitech", "Coreteco", "CS Germany",
    "CTR",
    "Dayco", "Delko", "Dello", "Delphi", "Delta Autotechnik", "Denso",
    "Depo", "Dolz",
    "EGR", "Eibach", "Elring", "EPS", "Ernst", "Eurocode", "Eyquem",
    "Fae", "FAG", "Febest", "Febi", "Fenox", "Ferodo", "Ferroz", "Filtron",
    "Flennor", "Flosser", "Fonos", "FRAM",
    "Gabriel", "Gates", "General Ricambi", "GKN", "Glaser", "GLO", "GMB",
    "Goetze", "Graf", "GSP",
    "Hansprise", "Heco", "Hella", "Hengst", "Hepu", "Herzog", "HP",
    "INA",
    "Jakoparts", "Johns", "JP Group", "Jurid",
    "K+F", "Kayaba", "Kilen", "Klokkerholm", "Knecht", "Kolbenschmidt",
    "Koni", "Koyo", "Kub", "KYB",
    "Lemforder", "LESJOFORS", "Lizarte", "Lmi", "Longho", "LPR", "Lucas",
    "LuK",
    "Magneti Marelli", "Mahle", "Mann", "Mapco", "Maruichi", "Masuma",
    "Matrix", "Mecafilter", "Metelli", "Meyle", "Mintex", "Monroe", "Moog",
    "Narva", "NGK", "Nipparts", "Nissens", "Nitto", "NK", "Nordglass",
    "NSK", "NTN", "Nural",
    "OBK", "Ocap", "Optimal", "Osram", "Otto Zimmermann",
    "Pagid", "Patron", "Payen", "Pentosin", "Pex", "Philips", "Pierburg",
    "Pilkington", "Purflux",
    "Qsten", "Quinton Hazell",
    "RBH", "RBI", "Remsa", "Remy", "ROLF", "Ruville",
    "Sachs", "Sakura", "Schlieckmann", "Schneider", "SCT", "Securit",
    "SFEC", "Sidem", "Sigma", "Signeda", "SIR", "SKF", "SM", "SNR",
    "Speedmate", "SPIDAN", "Splintex", "Stabilus", "SUN", "Suplex", "SWAG",
    "SWF",
    "Tesla", "Textar", "Topran", "Triscan", "TRW", "TYC", "Tyg",
    "Unipoint",
    "V-STAR", "Valeo", "Van Wezel", "VDO", "Victor Reinz", "VORON Glass",
    "Votex",
    "Wahler",
    "Zen", "ZF", "ZIC",
]


def upgrade() -> None:
    # 1. Таблица part_brands в схеме app, глобальная (без tenant_id и RLS).
    op.create_table(
        "part_brands",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="part_brands_pkey"),
        sa.UniqueConstraint("name", name="uq_part_brands_name"),
        schema="app",
    )

    # 2. tenant_app — только SELECT (как vehicle_brands после 0003).
    op.execute(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON app.part_brands FROM tenant_app;"
    )
    op.execute("GRANT SELECT ON app.part_brands TO tenant_app;")

    # 3. Сидим бренды.
    op.bulk_insert(
        sa.table("part_brands", sa.column("name", sa.String), schema="app"),
        [{"name": n} for n in PART_BRANDS],
    )

    # 4. parts.brand_id nullable FK → part_brands.id.
    op.add_column(
        "parts",
        sa.Column("brand_id", sa.BigInteger(), nullable=True),
        schema="app",
    )
    op.create_foreign_key(
        "fk_parts_brand",
        "parts",
        "part_brands",
        ["brand_id"],
        ["id"],
        ondelete="SET NULL",
        source_schema="app",
        referent_schema="app",
    )
    op.create_index(
        "ix_parts_brand_id",
        "parts",
        ["brand_id"],
        schema="app",
    )

    # 5. Бекфил brand_id из существующего free-text parts.brand —
    # case-insensitive по имени, пробелы по краям тримим. Кто не совпал
    # (опечатки, бренды вне сидированного списка) остаётся с brand_id=NULL,
    # текстовое поле parts.brand сохранено как было.
    op.execute(
        "UPDATE app.parts p "
        "SET brand_id = pb.id "
        "FROM app.part_brands pb "
        "WHERE p.brand IS NOT NULL "
        "  AND TRIM(p.brand) <> '' "
        "  AND LOWER(TRIM(p.brand)) = LOWER(pb.name);"
    )


def downgrade() -> None:
    op.drop_index("ix_parts_brand_id", table_name="parts", schema="app")
    op.drop_constraint("fk_parts_brand", "parts", type_="foreignkey", schema="app")
    op.drop_column("parts", "brand_id", schema="app")
    op.drop_table("part_brands", schema="app")
