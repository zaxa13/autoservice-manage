# Инструкция по развёртыванию локальной базы данных SQLite с FastAPI

Эта инструкция описывает, как настроить и запустить FastAPI приложение с локальной базой данных SQLite вместо PostgreSQL.

## Преимущества SQLite для разработки

- ✅ Не требует установки и настройки сервера БД
- ✅ Файл базы данных хранится локально
- ✅ Простая настройка и запуск
- ✅ Отлично подходит для разработки и тестирования
- ✅ Минимальные зависимости

## Предварительные требования

- Python 3.11 или выше
- pip (менеджер пакетов Python)

## Шаг 1: Установка зависимостей

Перейдите в директорию backend и установите зависимости:

```bash
cd backend
python -m venv venv

# Активация виртуального окружения
# Для macOS/Linux:
source venv/bin/activate
# Для Windows:
# venv\Scripts\activate

pip install -r requirements.txt
```

> **Примечание**: Для SQLite не нужен пакет `psycopg2-binary`, он используется только для PostgreSQL. Однако его можно оставить в requirements.txt для совместимости с PostgreSQL.

## Шаг 2: Настройка переменных окружения

Создайте файл `.env` в директории `backend/`:

```bash
cd backend
touch .env
```

Добавьте следующие настройки в файл `.env`:

```env
# База данных SQLite (по умолчанию используется sqlite:///./autoservice.db)
DATABASE_URL=sqlite:///./autoservice.db

# Секретный ключ для JWT токенов (обязательно измените на произвольную строку!)
SECRET_KEY=your-secret-key-change-this-in-production

# CORS - разрешённые источники для фронтенда
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Опционально: Redis URL (если не используется, можно оставить как есть)
REDIS_URL=redis://localhost:6379/0

# Настройки для интеграций (опционально, можно оставить пустыми для разработки)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
SMS_API_KEY=
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=
PARTS_SUPPLIER_API_KEY=
PARTS_SUPPLIER_API_URL=
GIBDD_API_KEY=
GIBDD_API_URL=

# Окружение
ENVIRONMENT=development
DEBUG=True
```

### Альтернативные варианты DATABASE_URL для SQLite:

- **Относительный путь** (рекомендуется): `sqlite:///./autoservice.db` - файл создастся в директории backend
- **Абсолютный путь**: `sqlite:////absolute/path/to/autoservice.db`
- **In-memory база** (для тестов): `sqlite:///:memory:` - данные не сохраняются после закрытия соединения

## Шаг 3: Выполнение миграций

После настройки переменных окружения выполните миграции Alembic для создания схемы базы данных:

```bash
# Убедитесь, что вы находитесь в директории backend
cd backend

# Активируйте виртуальное окружение, если ещё не активировано
source venv/bin/activate  # macOS/Linux
# или
# venv\Scripts\activate  # Windows

# Выполните миграции
alembic upgrade head
```

Эта команда создаст файл базы данных `autoservice.db` в директории `backend/` и применит все миграции.

Если вы хотите создать начальную миграцию с нуля (если её ещё нет):

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Шаг 4: Запуск FastAPI приложения

Запустите сервер разработки:

```bash
# Убедитесь, что виртуальное окружение активировано
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Или используйте более простую команду:

```bash
uvicorn app.main:app --reload
```

Сервер запустится на `http://localhost:8000`

## Шаг 5: Проверка работы

1. **Проверьте здоровье API:**
   ```bash
   curl http://localhost:8000/health
   ```
   Должен вернуться: `{"status": "ok"}`

2. **Откройте документацию API:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Проверьте наличие файла базы данных:**
   ```bash
   ls -la backend/autoservice.db
   ```

## Управление базой данных

### Просмотр данных через SQLite CLI

```bash
# Откройте базу данных в SQLite CLI
sqlite3 backend/autoservice.db

# Полезные команды в SQLite CLI:
.tables          # Показать все таблицы
.schema users    # Показать схему таблицы users
SELECT * FROM users;  # Выполнить SQL запрос
.quit            # Выйти из SQLite CLI
```

### Резервное копирование

```bash
# Создать резервную копию базы данных
cp backend/autoservice.db backend/autoservice.db.backup

# Или использовать SQLite команду для создания дампа
sqlite3 backend/autoservice.db .dump > backup.sql
```

### Восстановление из резервной копии

```bash
# Восстановить из файла базы данных
cp backend/autoservice.db.backup backend/autoservice.db

# Или из SQL дампа
sqlite3 backend/autoservice.db < backup.sql
```

## Создание новых миграций

При изменении моделей создавайте новые миграции:

```bash
# Автоматическое создание миграции на основе изменений в моделях
alembic revision --autogenerate -m "Описание изменений"

# Применить миграцию
alembic upgrade head
```

## Откат миграций

```bash
# Откатить последнюю миграцию
alembic downgrade -1

# Откатить все миграции до определённой версии
alembic downgrade <revision_id>
```

## Важные замечания

### Ограничения SQLite

1. **Нет поддержки одновременной записи**: SQLite поддерживает несколько читателей одновременно, но только один писатель. Для большинства приложений для разработки это не проблема.

2. **Ограничения типов данных**: Некоторые типы данных PostgreSQL (например, ARRAY, JSONB) могут работать по-другому в SQLite. Проверьте ваши модели на совместимость.

3. **Внешние ключи**: В SQLite внешние ключи по умолчанию отключены. В нашем коде они включены через `connect_args`, но убедитесь, что они работают корректно.

### Когда использовать SQLite vs PostgreSQL

**Используйте SQLite для:**
- Локальной разработки
- Тестирования
- Малых проектов с низкой нагрузкой
- Прототипирования

**Используйте PostgreSQL для:**
- Продакшн окружения
- Приложений с высокой нагрузкой
- Когда нужна одновременная запись из нескольких процессов
- Когда нужны продвинутые функции БД (JSONB, полнотекстовый поиск и т.д.)

## Устранение проблем

### Ошибка: "database is locked"

Эта ошибка возникает, когда другое соединение удерживает блокировку базы данных.

**Решение:**
- Убедитесь, что все соединения к БД закрыты
- Перезапустите FastAPI приложение
- Проверьте, нет ли других процессов, использующих базу данных

### Ошибка: "no such table"

Таблица не существует в базе данных.

**Решение:**
```bash
# Выполните миграции
alembic upgrade head
```

### Ошибка: "no module named 'app'"

Вы не находитесь в правильной директории или не активировали виртуальное окружение.

**Решение:**
```bash
cd backend
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

## Интеграция с IDE

### Visual Studio Code

Для удобной работы с SQLite в VS Code установите расширение:
- **SQLite Viewer** или **SQLite** - для просмотра и редактирования базы данных

### PyCharm

PyCharm имеет встроенную поддержку SQLite:
1. Откройте Database tool window (View → Tool Windows → Database)
2. Добавьте Data Source → SQLite
3. Укажите путь к файлу `autoservice.db`

## Дополнительные ресурсы

- [Документация SQLite](https://www.sqlite.org/docs.html)
- [Документация SQLAlchemy для SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Документация Alembic](https://alembic.sqlalchemy.org/)

## Быстрый старт (краткая версия)

```bash
# 1. Установка
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Настройка .env файла
echo "DATABASE_URL=sqlite:///./autoservice.db" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env

# 3. Миграции
alembic upgrade head

# 4. Запуск
uvicorn app.main:app --reload
```

Готово! Приложение должно быть доступно на http://localhost:8000

