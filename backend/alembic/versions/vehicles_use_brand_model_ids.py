"""vehicles: replace brand/model strings with brand_id/model_id FKs

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    if 'vehicles' not in tables or 'vehicle_brands' not in tables or 'vehicle_models' not in tables:
        # Нужны vehicle_brands и vehicle_models — если их нет, пропускаем (первый запуск)
        return

    cols = {c['name']: c for c in inspector.get_columns('vehicles')}
    if 'brand_id' in cols and 'model_id' in cols:
        # Уже мигрировано
        return

    # Добавляем новые колонки (nullable пока)
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        if 'brand_id' not in cols:
            batch_op.add_column(sa.Column('brand_id', sa.Integer(), nullable=True))
        if 'model_id' not in cols:
            batch_op.add_column(sa.Column('model_id', sa.Integer(), nullable=True))

    # Миграция данных: для каждой vehicle ищем/создаём brand и model
    vehicles = connection.execute(sa.text(
        "SELECT id, brand, model FROM vehicles"
    )).fetchall()

    for vid, brand_name, model_name in vehicles:
        brand_name = (brand_name or "").strip() or "Не указано"
        model_name = (model_name or "").strip() or "Не указано"
        # Найти или создать brand
        brand = connection.execute(sa.text(
            "SELECT id FROM vehicle_brands WHERE LOWER(TRIM(name)) = LOWER(TRIM(:n))"
        ), {"n": brand_name}).fetchone()
        if not brand:
            connection.execute(sa.text(
                "INSERT INTO vehicle_brands (name) VALUES (:n)"
            ), {"n": brand_name.strip()})
            connection.commit()
            brand_id = connection.execute(sa.text("SELECT last_insert_rowid()")).scalar()
        else:
            brand_id = brand[0]
        # Найти или создать model
        model = connection.execute(sa.text(
            "SELECT id FROM vehicle_models WHERE brand_id = :bid AND LOWER(TRIM(name)) = LOWER(TRIM(:n))"
        ), {"bid": brand_id, "n": model_name}).fetchone()
        if not model:
            connection.execute(sa.text(
                "INSERT INTO vehicle_models (brand_id, name) VALUES (:bid, :n)"
            ), {"bid": brand_id, "n": model_name.strip()})
            connection.commit()
            model_id = connection.execute(sa.text("SELECT last_insert_rowid()")).scalar()
        else:
            model_id = model[0]
        connection.execute(sa.text(
            "UPDATE vehicles SET brand_id = :bid, model_id = :mid WHERE id = :vid"
        ), {"bid": brand_id, "mid": model_id, "vid": vid})
    connection.commit()

    # Удаляем старые колонки, делаем новые NOT NULL
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        if 'brand' in cols:
            batch_op.drop_column('brand')
        if 'model' in cols:
            batch_op.drop_column('model')
        batch_op.alter_column('brand_id', nullable=False)
        batch_op.alter_column('model_id', nullable=False)
        batch_op.create_foreign_key('fk_vehicles_brand_id', 'vehicle_brands', ['brand_id'], ['id'], ondelete='RESTRICT')
        batch_op.create_foreign_key('fk_vehicles_model_id', 'vehicle_models', ['model_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    connection = op.get_bind()
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        try:
            batch_op.drop_constraint('fk_vehicles_brand_id', type_='foreignkey')
        except Exception:
            pass
        try:
            batch_op.drop_constraint('fk_vehicles_model_id', type_='foreignkey')
        except Exception:
            pass
        batch_op.add_column(sa.Column('brand', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('model', sa.String(), nullable=True))

    # Восстановить brand/model из справочников
    rows = connection.execute(sa.text("""
        SELECT v.id, vb.name as brand, vm.name as model
        FROM vehicles v
        JOIN vehicle_brands vb ON v.brand_id = vb.id
        JOIN vehicle_models vm ON v.model_id = vm.id
    """)).fetchall()
    for vid, brand, model in rows:
        connection.execute(sa.text(
            "UPDATE vehicles SET brand = :b, model = :m WHERE id = :vid"
        ), {"b": brand, "m": model, "vid": vid})
    connection.commit()

    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.alter_column('brand', nullable=False)
        batch_op.alter_column('model', nullable=False)
        batch_op.drop_column('brand_id')
        batch_op.drop_column('model_id')
