# Система управления автосервисом

Веб-приложение для управления бизнесом автосервиса с функциями оформления заказ-нарядов, управления складом, сотрудниками, расчета зарплаты и интеграциями с внешними сервисами.

## Технологический стек

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy (ORM)
- Alembic (миграции)
- PostgreSQL
- Redis
- Celery

### Frontend
- React 18+
- TypeScript
- Material-UI
- Zustand (state management)
- Vite

## Структура проекта

```
autoservice-management/
├── backend/          # FastAPI приложение
├── frontend/         # React приложение
└── docker-compose.yml
```

## Установка и запуск

### С использованием Docker Compose

1. Клонируйте репозиторий
2. Скопируйте `.env.example` в `.env` и настройте переменные окружения
3. Запустите:
```bash
docker-compose up -d
```

### Локальная разработка

#### Backend

**Важно:** По умолчанию приложение настроено на использование SQLite для локальной разработки. Это не требует установки и настройки PostgreSQL сервера. Подробную инструкцию по развёртыванию с SQLite см. в [docs/sqlite-setup.md](docs/sqlite-setup.md)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Настройте .env файл
cp .env.example .env

# Запустите миграции
alembic upgrade head

# Запустите сервер
uvicorn app.main:app --reload
```

**Использование SQLite (по умолчанию):**
- Простая настройка без необходимости запуска PostgreSQL
- Файл базы данных создаётся автоматически
- Подробная инструкция: [docs/sqlite-setup.md](docs/sqlite-setup.md)

**Использование PostgreSQL:**
- Настройте `DATABASE_URL` в `.env` файле на PostgreSQL подключение
- Убедитесь, что PostgreSQL сервер запущен

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Основные функции

- **Заказ-наряды**: Создание, редактирование, завершение заказ-нарядов
- **Склад**: Управление остатками, приходы и расходы
- **Сотрудники**: Управление сотрудниками и их данными
- **Зарплата**: Автоматический расчет зарплаты за период
- **Платежи**: Интеграция с ЮKassa для приема платежей
- **Интеграции**: 
  - ЮKassa (платежи)
  - SMS уведомления
  - Email уведомления
  - Поставщики автозапчастей
  - База ГИБДД

## Система ролей

- **Администратор**: Полный доступ
- **Менеджер**: Управление заказ-нарядами, складом
- **Механик**: Просмотр и выполнение назначенных заказ-нарядов
- **Бухгалтер**: Расчет зарплаты, финансовая отчетность

## API Документация

После запуска backend доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Лицензия

MIT

