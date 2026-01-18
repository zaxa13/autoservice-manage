# Инструкция по локальному запуску проекта

Эта инструкция поможет вам запустить бекенд и фронтенд на вашей локальной машине.

## Предварительные требования

- **Python 3.11+** (для бекенда)
- **Node.js 16+** и **npm** (для фронтенда)
- **Git** (для клонирования репозитория)

## Быстрый старт

### 1. Клонирование и подготовка

```bash
# Перейдите в директорию проекта
cd autoservice-management
```

### 2. Запуск Backend

#### Шаг 1: Установка зависимостей

```bash
cd backend

# Создайте виртуальное окружение (если ещё не создано)
python -m venv venv

# Активируйте виртуальное окружение
# Для macOS/Linux:
source venv/bin/activate
# Для Windows:
# venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

#### Шаг 2: Настройка переменных окружения

Создайте файл `.env` в директории `backend/`:

```bash
# В директории backend/
touch .env
```

Добавьте в файл `.env` следующие настройки (минимум для работы):

```env
# База данных SQLite (используется по умолчанию, не требует установки PostgreSQL)
DATABASE_URL=sqlite:///./autoservice.db

# Секретный ключ для JWT токенов
SECRET_KEY=your-secret-key-change-this-in-production-min-32-chars

# Окружение
ENVIRONMENT=development
DEBUG=True
```

> **Примечание**: По умолчанию используется SQLite, что не требует установки PostgreSQL. Файл базы данных создастся автоматически при запуске миграций.

#### Шаг 3: Выполнение миграций базы данных

```bash
# Убедитесь, что вы находитесь в директории backend и виртуальное окружение активировано
alembic upgrade head
```

Эта команда создаст файл `autoservice.db` со всеми необходимыми таблицами.

#### Шаг 4: Запуск сервера

```bash
# Запустите FastAPI сервер
uvicorn app.main:app --reload
```

Backend будет доступен на: **http://localhost:8000**

Проверить работу можно:
- **API документация (Swagger)**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

---

### 3. Запуск Frontend

Откройте **новый терминал** (backend должен продолжать работать):

#### Шаг 1: Установка зависимостей

```bash
cd frontend

# Установите зависимости
npm install
```

#### Шаг 2: Запуск сервера разработки

```bash
npm run dev
```

Frontend будет доступен на: **http://localhost:5173**

> **Примечание**: Frontend автоматически настроен на проксирование запросов к API через Vite proxy (`/api` → `http://localhost:8000`).

---

## Проверка работоспособности

1. **Backend работает**: Откройте http://localhost:8000/docs в браузере - должна открыться Swagger документация
2. **Frontend работает**: Откройте http://localhost:5173 - должна открыться главная страница приложения
3. **Связь между ними**: Попробуйте выполнить логин через фронтенд - запросы должны успешно доходить до бекенда

## Создание первого администратора

После запуска бекенда вы можете создать первого администратора:

```bash
cd backend
# Убедитесь, что виртуальное окружение активировано
python scripts/create_admin.py
```

Или создайте пользователя через API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-password",
    "full_name": "Admin User"
  }'
```

> Подробная инструкция по созданию первого администратора: [docs/first-admin-setup.md](first-admin-setup.md)

## Структура портов

- **Backend (FastAPI)**: `http://localhost:8000`
- **Frontend (Vite)**: `http://localhost:5173`
- **API документация (Swagger)**: `http://localhost:8000/docs`
- **API документация (ReDoc)**: `http://localhost:8000/redoc`

## Возможные проблемы и решения

### Backend не запускается

**Ошибка: "SECRET_KEY не установлен"**
- Создайте файл `.env` в директории `backend/` с указанием `SECRET_KEY`

**Ошибка: "no such table"**
- Выполните миграции: `alembic upgrade head`

**Ошибка: "database is locked"** (для SQLite)
- Убедитесь, что все соединения с БД закрыты
- Перезапустите сервер

### Frontend не может подключиться к Backend

**Проверьте:**
1. Backend запущен на порту 8000: `curl http://localhost:8000/health`
2. Настройки прокси в `vite.config.ts` указывают на правильный порт
3. Нет ошибок CORS (если проблема сохраняется, проверьте настройки CORS в `app/main.py`)

### Порты заняты

Если порты 8000 или 5173 заняты:

**Для Backend:**
```bash
uvicorn app.main:app --reload --port 8001
```
И обновите `vite.config.ts` в frontend, чтобы прокси указывал на порт 8001.

**Для Frontend:**
```bash
npm run dev -- --port 3000
```

## Дополнительные ресурсы

- [Настройка SQLite](sqlite-setup.md) - подробная информация о работе с SQLite
- [Документация API](api-documentation.md) - описание всех эндпоинтов API
- [Бизнес-процессы](business-processes.md) - описание функциональности системы

## Команды для разработки

### Backend

```bash
# Запуск с автоперезагрузкой (уже запущено с --reload)
uvicorn app.main:app --reload

# Создание новой миграции
alembic revision --autogenerate -m "Описание изменений"

# Применение миграций
alembic upgrade head

# Откат последней миграции
alembic downgrade -1
```

### Frontend

```bash
# Запуск dev сервера
npm run dev

# Сборка для production
npm run build

# Предпросмотр production сборки
npm run preview

# Проверка кода (lint)
npm run lint
```

## Остановка серверов

- В терминале с Backend: нажмите `Ctrl+C`
- В терминале с Frontend: нажмите `Ctrl+C`

---

**Готово!** Теперь вы можете разрабатывать приложение локально. 🚀
