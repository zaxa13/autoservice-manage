# Быстрый старт с SQLite

Краткая инструкция по развёртыванию FastAPI приложения с SQLite за 5 минут.

## Шаг 1: Установка зависимостей

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Шаг 2: Создание .env файла

Создайте файл `backend/.env` со следующим содержимым:

```env
DATABASE_URL=sqlite:///./autoservice.db
SECRET_KEY=your-secret-key-change-this
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ENVIRONMENT=development
DEBUG=True
```

## Шаг 3: Создание и выполнение миграций

Если миграций еще нет, создайте первую:

```bash
alembic revision --autogenerate -m "Initial migration"
```

Затем примените миграции:

```bash
alembic upgrade head
```

**Примечание:** Если вы видите ошибку "no such table", это означает, что миграции не были выполнены. Выполните команды выше.

## Шаг 4: Запуск сервера

```bash
uvicorn app.main:app --reload
```

Готово! API доступен на http://localhost:8000

## Проверка работы

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

**Подробная инструкция:** [sqlite-setup.md](sqlite-setup.md)

