"""add customers table and update vehicles

Revision ID: a1b2c3d4e5f6
Revises: cc8be3474d98
Create Date: 2026-01-17 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'cc8be3474d98'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование таблицы customers перед созданием
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    # Удаляем временные таблицы Alembic, если они остались после прерванной миграции
    for table_name in tables:
        if table_name.startswith('_alembic_tmp_'):
            try:
                connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
            except Exception:
                pass
    connection.commit()
    
    # Создаем таблицу customers только если её еще нет
    if 'customers' not in tables:
        op.create_table('customers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('full_name', sa.String(), nullable=False),
            sa.Column('phone', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('address', sa.String(), nullable=True),
            sa.Column('notes', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('customers', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_customers_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_customers_phone'), ['phone'], unique=False)

    # Создаем временную таблицу для миграции данных
    
    # Создаем таблицу для работы с данными
    vehicles_temp = table('vehicles',
        column('id', sa.Integer),
        column('owner_name', sa.String),
        column('owner_phone', sa.String),
        column('owner_email', sa.String)
    )
    
    customers_temp = table('customers',
        column('id', sa.Integer),
        column('full_name', sa.String),
        column('phone', sa.String),
        column('email', sa.String)
    )

    # Получаем все уникальные комбинации owner_name, owner_phone, owner_email из vehicles
    # Используем GROUP BY для получения одного email на комбинацию (берем первый не-NULL)
    result = connection.execute(sa.text("""
        SELECT 
            owner_name, 
            owner_phone, 
            MIN(owner_email) as owner_email,
            COUNT(*) as vehicle_count
        FROM vehicles
        WHERE owner_name IS NOT NULL AND owner_name != '' 
          AND owner_phone IS NOT NULL AND owner_phone != ''
        GROUP BY owner_name, owner_phone
    """)).fetchall()

    # Создаем customers для каждой уникальной комбинации
    customers_map = {}  # Маппинг (owner_name, owner_phone) -> customer_id
    for row in result:
        owner_name, owner_phone, owner_email, vehicle_count = row
        
        # Проверяем, существует ли уже такой клиент
        existing = connection.execute(sa.text("""
            SELECT id FROM customers 
            WHERE full_name = :name AND phone = :phone
        """), {"name": owner_name, "phone": owner_phone}).fetchone()
        
        if not existing:
            # Создаем нового клиента
            connection.execute(sa.text("""
                INSERT INTO customers (full_name, phone, email, created_at)
                VALUES (:name, :phone, :email, CURRENT_TIMESTAMP)
            """), {"name": owner_name, "phone": owner_phone, "email": owner_email})
            connection.commit()
            
            # Получаем ID созданного клиента
            customer_id = connection.execute(sa.text("""
                SELECT last_insert_rowid()
            """)).scalar()
        else:
            customer_id = existing[0]
        
        customers_map[(owner_name, owner_phone)] = customer_id

    # Проверяем существование колонки customer_id перед добавлением
    vehicles_columns = [col['name'] for col in inspector.get_columns('vehicles')]
    vehicles_has_customer_id = 'customer_id' in vehicles_columns
    
    if not vehicles_has_customer_id:
        # Добавляем колонку customer_id в vehicles
        with op.batch_alter_table('vehicles', schema=None) as batch_op:
            batch_op.add_column(sa.Column('customer_id', sa.Integer(), nullable=True))

        # Обновляем customer_id для всех vehicles
        # Это важно: обновляем каждую запись по её уникальной комбинации owner_name + owner_phone
        for (owner_name, owner_phone), customer_id in customers_map.items():
            connection.execute(sa.text("""
                UPDATE vehicles 
                SET customer_id = :customer_id 
                WHERE owner_name = :name AND owner_phone = :phone
                  AND (customer_id IS NULL OR customer_id = 0)
            """), {"customer_id": customer_id, "name": owner_name, "phone": owner_phone})
        
        connection.commit()

        # Проверяем, что все vehicles получили customer_id
        # Если есть vehicles без customer_id, это ошибка миграции
        vehicles_without_customer = connection.execute(sa.text("""
            SELECT COUNT(*) FROM vehicles 
            WHERE customer_id IS NULL 
              AND owner_name IS NOT NULL 
              AND owner_name != ''
              AND owner_phone IS NOT NULL 
              AND owner_phone != ''
        """)).scalar()
        
        if vehicles_without_customer > 0:
            raise Exception(
                f"Ошибка миграции: {vehicles_without_customer} транспортных средств "
                f"не получили customer_id. Проверьте данные."
            )

        # Делаем customer_id обязательным и добавляем внешний ключ
        with op.batch_alter_table('vehicles', schema=None) as batch_op:
            batch_op.alter_column('customer_id', nullable=False)
            # Проверяем существование foreign key перед созданием
            try:
                batch_op.create_foreign_key('fk_vehicles_customer_id', 'customers', ['customer_id'], ['id'])
            except Exception:
                # Foreign key может уже существовать, пропускаем
                pass

    # Удаляем старые колонки owner_name, owner_phone, owner_email (если они существуют)
    vehicles_columns = [col['name'] for col in inspector.get_columns('vehicles')]
    
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        if 'owner_name' in vehicles_columns:
            batch_op.drop_column('owner_name')
        if 'owner_phone' in vehicles_columns:
            batch_op.drop_column('owner_phone')
        if 'owner_email' in vehicles_columns:
            batch_op.drop_column('owner_email')


def downgrade() -> None:
    # Возвращаем старые колонки в vehicles
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('owner_phone', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('owner_email', sa.String(), nullable=True))

    # Восстанавливаем данные из customers
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT v.id, c.full_name, c.phone, c.email
        FROM vehicles v
        JOIN customers c ON v.customer_id = c.id
    """)).fetchall()
    
    for vehicle_id, full_name, phone, email in result:
        connection.execute(sa.text("""
            UPDATE vehicles 
            SET owner_name = :name, owner_phone = :phone, owner_email = :email
            WHERE id = :vehicle_id
        """), {"name": full_name, "phone": phone, "email": email, "vehicle_id": vehicle_id})
    connection.commit()

    # Удаляем foreign key и колонку customer_id
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.drop_constraint('fk_vehicles_customer_id', type_='foreignkey')
        batch_op.drop_column('customer_id')
        # Делаем поля обязательными (если нужно)
        batch_op.alter_column('owner_name', nullable=False)
        batch_op.alter_column('owner_phone', nullable=False)

    # Удаляем таблицу customers
    op.drop_table('customers')
