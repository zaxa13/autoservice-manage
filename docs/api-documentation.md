# API Документация - Система управления автосервисом

## Содержание

1. [Общая информация](#общая-информация)
2. [Аутентификация](#аутентификация)
3. [Модули API](#модули-api)
   - [Auth - Аутентификация](#auth---аутентификация)
   - [Users - Пользователи](#users---пользователи)
   - [Vehicles - Транспортные средства](#vehicles---транспортные-средства)
   - [Orders - Заказ-наряды](#orders---заказ-наряды)
   - [Works - Виды работ](#works---виды-работ)
   - [Parts - Запчасти](#parts---запчасти)
   - [Warehouse - Склад](#warehouse---склад)
   - [Employees - Сотрудники](#employees---сотрудники)
   - [Salary - Зарплата](#salary---зарплата)
   - [Payments - Платежи](#payments---платежи)
   - [Integrations - Интеграции](#integrations---интеграции)

---

## Общая информация

### Базовый URL
```
/api/v1
```

### Аутентификация
API использует JWT (JSON Web Tokens) для аутентификации. Большинство endpoints требуют авторизации через Bearer токен в заголовке:
```
Authorization: Bearer <access_token>
```

### Роли пользователей
- **ADMIN** - Администратор (полный доступ)
- **MANAGER** - Менеджер (управление заказами, складом, сотрудниками)
- **MECHANIC** - Механик (работа с заказ-нарядами, просмотр данных)
- **ACCOUNTANT** - Бухгалтер (работа с зарплатой, платежами)

### Формат ответов
- Успешные запросы возвращают статус `200 OK` или `201 Created`
- Ошибки возвращают соответствующие HTTP статусы:
  - `400 Bad Request` - Неверные параметры запроса
  - `401 Unauthorized` - Требуется аутентификация
  - `403 Forbidden` - Недостаточно прав доступа
  - `404 Not Found` - Ресурс не найден
  - `500 Internal Server Error` - Внутренняя ошибка сервера

---

## Auth - Аутентификация

### POST `/api/v1/auth/login`
**Описание:** Вход в систему и получение JWT токенов

**Права доступа:** Публичный endpoint (не требует авторизации)

**Параметры запроса:**
- Форма данных (OAuth2PasswordRequestForm):
  - `username` (string, required) - Имя пользователя
  - `password` (string, required) - Пароль

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Пример запроса:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"
```

---

### POST `/api/v1/auth/refresh`
**Описание:** Обновление access токена с помощью refresh токена

**Права доступа:** Публичный endpoint (не требует авторизации)

**Параметры запроса (Body):**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Возможные ошибки:**
- `401 Unauthorized` - Неверный или истекший refresh токен

---

### GET `/api/v1/auth/me`
**Описание:** Получение информации о текущем авторизованном пользователе

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса:** Нет

**Ответ:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "employee_id": 1,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

---

### POST `/api/v1/auth/register`
**Описание:** Регистрация нового пользователя (только для администратора)

**Права доступа:** ADMIN

**Параметры запроса (Body):**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword",
  "role": "mechanic"
}
```

**Поля:**
- `username` (string, required) - Уникальное имя пользователя
- `email` (string, required) - Email адрес
- `password` (string, required) - Пароль
- `role` (enum, required) - Роль: `admin`, `manager`, `mechanic`, `accountant`

**Ответ:**
```json
{
  "id": 2,
  "username": "newuser",
  "email": "user@example.com",
  "role": "mechanic",
  "is_active": true,
  "employee_id": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

---

## Users - Пользователи

### GET `/api/v1/users/`
**Описание:** Получение списка всех пользователей

**Права доступа:** ADMIN

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска (пагинация)
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "employee_id": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": null
  }
]
```

---

### GET `/api/v1/users/{user_id}`
**Описание:** Получение пользователя по ID

**Права доступа:** ADMIN

**Параметры запроса (Path):**
- `user_id` (integer, required) - ID пользователя

**Ответ:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "employee_id": 1,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

**Возможные ошибки:**
- `404 Not Found` - Пользователь не найден

---

### PUT `/api/v1/users/{user_id}`
**Описание:** Обновление данных пользователя

**Права доступа:** ADMIN

**Параметры запроса (Path):**
- `user_id` (integer, required) - ID пользователя

**Параметры запроса (Body):**
```json
{
  "username": "updated_username",
  "email": "newemail@example.com",
  "role": "manager",
  "is_active": true,
  "password": "newpassword"
}
```

**Поля (все опциональны):**
- `username` (string) - Имя пользователя
- `email` (string) - Email адрес
- `role` (enum) - Роль пользователя
- `is_active` (boolean) - Активен ли пользователь
- `password` (string) - Новый пароль (будет захеширован)

**Ответ:**
```json
{
  "id": 1,
  "username": "updated_username",
  "email": "newemail@example.com",
  "role": "manager",
  "is_active": true,
  "employee_id": 1,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z"
}
```

---

## Vehicles - Транспортные средства

### GET `/api/v1/vehicles/`
**Описание:** Получение списка всех транспортных средств

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "vin": "1HGBH41JXMN109186",
    "license_plate": "А123БВ777",
    "brand": "Toyota",
    "model": "Camry",
    "year": 2020,
    "owner_name": "Иванов Иван Иванович",
    "owner_phone": "+79001234567",
    "owner_email": "ivanov@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### GET `/api/v1/vehicles/{vehicle_id}`
**Описание:** Получение транспортного средства по ID

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Path):**
- `vehicle_id` (integer, required) - ID транспортного средства

**Ответ:**
```json
{
  "id": 1,
  "vin": "1HGBH41JXMN109186",
  "license_plate": "А123БВ777",
  "brand": "Toyota",
  "model": "Camry",
  "year": 2020,
  "owner_name": "Иванов Иван Иванович",
  "owner_phone": "+79001234567",
  "owner_email": "ivanov@example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Возможные ошибки:**
- `404 Not Found` - Транспортное средство не найдено

---

### POST `/api/v1/vehicles/`
**Описание:** Создание нового транспортного средства

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "vin": "1HGBH41JXMN109186",
  "license_plate": "А123БВ777",
  "brand": "Toyota",
  "model": "Camry",
  "year": 2020,
  "owner_name": "Иванов Иван Иванович",
  "owner_phone": "+79001234567",
  "owner_email": "ivanov@example.com"
}
```

**Поля:**
- `vin` (string, optional) - VIN номер (уникальный)
- `license_plate` (string, optional) - Государственный номер
- `brand` (string, required) - Марка автомобиля
- `model` (string, required) - Модель автомобиля
- `year` (integer, optional) - Год выпуска
- `owner_name` (string, required) - ФИО владельца
- `owner_phone` (string, required) - Телефон владельца
- `owner_email` (string, optional) - Email владельца

**Ответ:**
```json
{
  "id": 1,
  "vin": "1HGBH41JXMN109186",
  "license_plate": "А123БВ777",
  "brand": "Toyota",
  "model": "Camry",
  "year": 2020,
  "owner_name": "Иванов Иван Иванович",
  "owner_phone": "+79001234567",
  "owner_email": "ivanov@example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### PUT `/api/v1/vehicles/{vehicle_id}`
**Описание:** Обновление данных транспортного средства

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `vehicle_id` (integer, required) - ID транспортного средства

**Параметры запроса (Body):**
```json
{
  "brand": "Honda",
  "model": "Accord",
  "owner_phone": "+79007654321"
}
```

**Поля (все опциональны):**
- `vin`, `license_plate`, `brand`, `model`, `year`, `owner_name`, `owner_phone`, `owner_email`

**Ответ:**
```json
{
  "id": 1,
  "vin": "1HGBH41JXMN109186",
  "license_plate": "А123БВ777",
  "brand": "Honda",
  "model": "Accord",
  "year": 2020,
  "owner_name": "Иванов Иван Иванович",
  "owner_phone": "+79007654321",
  "owner_email": "ivanov@example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Orders - Заказ-наряды

### GET `/api/v1/orders/`
**Описание:** Получение списка заказ-нарядов

**Права доступа:** Требуется авторизация (любая роль)

**Особенности:**
- Механики видят только свои заказ-наряды (где они назначены механиками)
- Менеджеры и администраторы видят все заказ-наряды

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей
- `status` (enum, optional) - Фильтр по статусу: `new`, `in_progress`, `completed`, `cancelled`

**Ответ:**
```json
[
  {
    "id": 1,
    "number": "ORD-20240101-0001",
    "vehicle_id": 1,
    "employee_id": 2,
    "mechanic_id": 3,
    "status": "in_progress",
    "total_amount": "15000.00",
    "paid_amount": "0.00",
    "created_at": "2024-01-01T10:00:00Z",
    "completed_at": null
  }
]
```

---

### GET `/api/v1/orders/{order_id}`
**Описание:** Получение детальной информации о заказ-наряде

**Права доступа:** Требуется авторизация (любая роль)

**Особенности:**
- Механики могут видеть только свои заказ-наряды

**Параметры запроса (Path):**
- `order_id` (integer, required) - ID заказ-наряда

**Ответ:**
```json
{
  "id": 1,
  "number": "ORD-20240101-0001",
  "vehicle_id": 1,
  "employee_id": 2,
  "mechanic_id": 3,
  "status": "in_progress",
  "total_amount": "15000.00",
  "paid_amount": "0.00",
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": null,
  "vehicle": {
    "id": 1,
    "vin": "1HGBH41JXMN109186",
    "license_plate": "А123БВ777",
    "brand": "Toyota",
    "model": "Camry",
    "year": 2020,
    "owner_name": "Иванов Иван Иванович",
    "owner_phone": "+79001234567",
    "owner_email": "ivanov@example.com",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "employee": {
    "id": 2,
    "full_name": "Петров Петр Петрович",
    "position": "Менеджер",
    "phone": "+79001111111",
    "email": "petrov@example.com",
    "hire_date": "2023-01-01",
    "salary_base": "50000.00",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": null
  },
  "mechanic": {
    "id": 3,
    "full_name": "Сидоров Сидор Сидорович",
    "position": "Механик",
    "phone": "+79002222222",
    "email": "sidorov@example.com",
    "hire_date": "2023-02-01",
    "salary_base": "60000.00",
    "is_active": true,
    "created_at": "2023-02-01T00:00:00Z",
    "updated_at": null
  },
  "order_works": [
    {
      "id": 1,
      "order_id": 1,
      "work_id": 1,
      "quantity": 2,
      "price": "5000.00",
      "total": "10000.00",
      "work": {
        "id": 1,
        "name": "Замена масла",
        "description": "Замена моторного масла и фильтра",
        "price": "5000.00",
        "duration_minutes": 60,
        "category": "maintenance"
      }
    }
  ],
  "order_parts": [
    {
      "id": 1,
      "order_id": 1,
      "part_id": 1,
      "quantity": 1,
      "price": "5000.00",
      "total": "5000.00",
      "part": {
        "id": 1,
        "name": "Моторное масло 5W-30",
        "part_number": "OIL-001",
        "brand": "Castrol",
        "price": "5000.00",
        "unit": "л",
        "category": "consumables"
      }
    }
  ]
}
```

**Возможные ошибки:**
- `403 Forbidden` - Механик пытается получить доступ к чужому заказ-наряду
- `404 Not Found` - Заказ-наряд не найден

---

### POST `/api/v1/orders/`
**Описание:** Создание нового заказ-наряда

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "vehicle_id": 1,
  "mechanic_id": 3,
  "order_works": [
    {
      "work_id": 1,
      "quantity": 2,
      "price": "5000.00"
    }
  ],
  "order_parts": [
    {
      "part_id": 1,
      "quantity": 1,
      "price": "5000.00"
    }
  ]
}
```

**Поля:**
- `vehicle_id` (integer, required) - ID транспортного средства
- `mechanic_id` (integer, optional) - ID механика, который будет выполнять работу
- `order_works` (array, optional) - Список работ
  - `work_id` (integer, required) - ID вида работы
  - `quantity` (integer, default: 1) - Количество
  - `price` (decimal, required) - Цена за единицу
- `order_parts` (array, optional) - Список запчастей
  - `part_id` (integer, required) - ID запчасти
  - `quantity` (integer, default: 1) - Количество
  - `price` (decimal, required) - Цена за единицу

**Особенности:**
- Номер заказ-наряда генерируется автоматически в формате `ORD-YYYYMMDD-NNNN`
- Общая сумма рассчитывается автоматически на основе работ и запчастей
- `employee_id` устанавливается автоматически из текущего пользователя

**Ответ:**
```json
{
  "id": 1,
  "number": "ORD-20240101-0001",
  "vehicle_id": 1,
  "employee_id": 2,
  "mechanic_id": 3,
  "status": "new",
  "total_amount": "15000.00",
  "paid_amount": "0.00",
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": null
}
```

**Возможные ошибки:**
- `400 Bad Request` - У пользователя не привязан сотрудник

---

### PUT `/api/v1/orders/{order_id}`
**Описание:** Обновление заказ-наряда

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `order_id` (integer, required) - ID заказ-наряда

**Параметры запроса (Body):**
```json
{
  "mechanic_id": 4,
  "status": "in_progress",
  "order_works": [
    {
      "work_id": 1,
      "quantity": 1,
      "price": "5000.00"
    }
  ],
  "order_parts": [
    {
      "part_id": 1,
      "quantity": 2,
      "price": "5000.00"
    }
  ]
}
```

**Поля (все опциональны):**
- `mechanic_id` (integer) - ID механика
- `status` (enum) - Статус: `new`, `in_progress`, `completed`, `cancelled`
- `order_works` (array) - Список работ (при обновлении заменяет все существующие)
- `order_parts` (array) - Список запчастей (при обновлении заменяет все существующие)

**Особенности:**
- При установке статуса `completed` автоматически устанавливается `completed_at`
- При обновлении работ или запчастей общая сумма пересчитывается автоматически

**Ответ:**
```json
{
  "id": 1,
  "number": "ORD-20240101-0001",
  "vehicle_id": 1,
  "employee_id": 2,
  "mechanic_id": 4,
  "status": "in_progress",
  "total_amount": "15000.00",
  "paid_amount": "0.00",
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": null
}
```

---

### POST `/api/v1/orders/{order_id}/complete`
**Описание:** Завершение заказ-наряда и списание запчастей со склада

**Права доступа:** Требуется авторизация (любая роль)

**Особенности:**
- При завершении автоматически списываются запчасти со склада
- Создаются транзакции расхода для каждой запчасти
- Статус заказ-наряда меняется на `completed`

**Параметры запроса (Path):**
- `order_id` (integer, required) - ID заказ-наряда

**Ответ:**
```json
{
  "id": 1,
  "number": "ORD-20240101-0001",
  "vehicle_id": 1,
  "employee_id": 2,
  "mechanic_id": 3,
  "status": "completed",
  "total_amount": "15000.00",
  "paid_amount": "0.00",
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": "2024-01-01T15:00:00Z"
}
```

**Возможные ошибки:**
- `400 Bad Request` - Заказ-наряд уже завершен или недостаточно запчастей на складе
- `404 Not Found` - Заказ-наряд не найден
- `400 Bad Request` - У пользователя не привязан сотрудник

---

### POST `/api/v1/orders/{order_id}/cancel`
**Описание:** Отмена заказ-наряда

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `order_id` (integer, required) - ID заказ-наряда

**Ответ:**
```json
{
  "id": 1,
  "number": "ORD-20240101-0001",
  "vehicle_id": 1,
  "employee_id": 2,
  "mechanic_id": 3,
  "status": "cancelled",
  "total_amount": "15000.00",
  "paid_amount": "0.00",
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": null
}
```

---

## Works - Виды работ

### GET `/api/v1/works/`
**Описание:** Получение списка всех видов работ

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Замена масла",
    "description": "Замена моторного масла и фильтра",
    "price": "5000.00",
    "duration_minutes": 60,
    "category": "maintenance"
  }
]
```

**Категории работ:**
- `diagnostics` - Диагностика
- `repair` - Ремонт
- `maintenance` - Обслуживание
- `body_work` - Кузовные работы
- `painting` - Покраска
- `other` - Прочее

---

### GET `/api/v1/works/{work_id}`
**Описание:** Получение вида работы по ID

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Path):**
- `work_id` (integer, required) - ID вида работы

**Ответ:**
```json
{
  "id": 1,
  "name": "Замена масла",
  "description": "Замена моторного масла и фильтра",
  "price": "5000.00",
  "duration_minutes": 60,
  "category": "maintenance"
}
```

---

### POST `/api/v1/works/`
**Описание:** Создание нового вида работы

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "name": "Замена масла",
  "description": "Замена моторного масла и фильтра",
  "price": "5000.00",
  "duration_minutes": 60,
  "category": "maintenance"
}
```

**Поля:**
- `name` (string, required) - Название работы
- `description` (string, optional) - Описание
- `price` (decimal, required) - Цена
- `duration_minutes` (integer, default: 60) - Продолжительность в минутах
- `category` (enum, default: "other") - Категория работы

**Ответ:**
```json
{
  "id": 1,
  "name": "Замена масла",
  "description": "Замена моторного масла и фильтра",
  "price": "5000.00",
  "duration_minutes": 60,
  "category": "maintenance"
}
```

---

### PUT `/api/v1/works/{work_id}`
**Описание:** Обновление вида работы

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `work_id` (integer, required) - ID вида работы

**Параметры запроса (Body):**
```json
{
  "price": "5500.00",
  "duration_minutes": 45
}
```

**Поля (все опциональны):**
- `name`, `description`, `price`, `duration_minutes`, `category`

**Ответ:**
```json
{
  "id": 1,
  "name": "Замена масла",
  "description": "Замена моторного масла и фильтра",
  "price": "5500.00",
  "duration_minutes": 45,
  "category": "maintenance"
}
```

---

## Parts - Запчасти

### GET `/api/v1/parts/`
**Описание:** Получение списка всех запчастей

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Моторное масло 5W-30",
    "part_number": "OIL-001",
    "brand": "Castrol",
    "price": "5000.00",
    "unit": "л",
    "category": "consumables"
  }
]
```

**Категории запчастей:**
- `engine` - Двигатель
- `transmission` - Трансмиссия
- `suspension` - Подвеска
- `brakes` - Тормоза
- `electrical` - Электрика
- `body` - Кузов
- `consumables` - Расходники
- `other` - Прочее

---

### GET `/api/v1/parts/{part_id}`
**Описание:** Получение запчасти по ID

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Path):**
- `part_id` (integer, required) - ID запчасти

**Ответ:**
```json
{
  "id": 1,
  "name": "Моторное масло 5W-30",
  "part_number": "OIL-001",
  "brand": "Castrol",
  "price": "5000.00",
  "unit": "л",
  "category": "consumables"
}
```

---

### POST `/api/v1/parts/`
**Описание:** Создание новой запчасти

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "name": "Моторное масло 5W-30",
  "part_number": "OIL-001",
  "brand": "Castrol",
  "price": "5000.00",
  "unit": "л",
  "category": "consumables"
}
```

**Поля:**
- `name` (string, required) - Название запчасти
- `part_number` (string, optional) - Артикул/номер запчасти
- `brand` (string, optional) - Бренд
- `price` (decimal, required) - Цена
- `unit` (string, default: "шт") - Единица измерения
- `category` (enum, default: "other") - Категория

**Ответ:**
```json
{
  "id": 1,
  "name": "Моторное масло 5W-30",
  "part_number": "OIL-001",
  "brand": "Castrol",
  "price": "5000.00",
  "unit": "л",
  "category": "consumables"
}
```

---

### PUT `/api/v1/parts/{part_id}`
**Описание:** Обновление запчасти

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `part_id` (integer, required) - ID запчасти

**Параметры запроса (Body):**
```json
{
  "price": "5200.00",
  "brand": "Mobil"
}
```

**Поля (все опциональны):**
- `name`, `part_number`, `brand`, `price`, `unit`, `category`

**Ответ:**
```json
{
  "id": 1,
  "name": "Моторное масло 5W-30",
  "part_number": "OIL-001",
  "brand": "Mobil",
  "price": "5200.00",
  "unit": "л",
  "category": "consumables"
}
```

---

## Warehouse - Склад

### GET `/api/v1/warehouse/items`
**Описание:** Получение списка позиций склада

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "part_id": 1,
    "quantity": "50.00",
    "min_quantity": "10.00",
    "location": "Стеллаж А-1",
    "last_updated": "2024-01-01T12:00:00Z",
    "part": {
      "id": 1,
      "name": "Моторное масло 5W-30",
      "part_number": "OIL-001",
      "brand": "Castrol",
      "price": "5000.00",
      "unit": "л",
      "category": "consumables"
    }
  }
]
```

---

### GET `/api/v1/warehouse/items/{item_id}`
**Описание:** Получение позиции склада по ID

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Path):**
- `item_id` (integer, required) - ID позиции склада

**Ответ:**
```json
{
  "id": 1,
  "part_id": 1,
  "quantity": "50.00",
  "min_quantity": "10.00",
  "location": "Стеллаж А-1",
  "last_updated": "2024-01-01T12:00:00Z",
  "part": {
    "id": 1,
    "name": "Моторное масло 5W-30",
    "part_number": "OIL-001",
    "brand": "Castrol",
    "price": "5000.00",
    "unit": "л",
    "category": "consumables"
  }
}
```

---

### POST `/api/v1/warehouse/items`
**Описание:** Создание позиции на складе

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "part_id": 1,
  "quantity": "100.00",
  "min_quantity": "10.00",
  "location": "Стеллаж А-1"
}
```

**Поля:**
- `part_id` (integer, required) - ID запчасти (уникальная связь)
- `quantity` (decimal, required) - Текущее количество
- `min_quantity` (decimal, default: 0) - Минимальное количество (для уведомлений)
- `location` (string, optional) - Местоположение на складе

**Особенности:**
- Для каждой запчасти может быть только одна позиция на складе
- При создании проверяется существование запчасти

**Ответ:**
```json
{
  "id": 1,
  "part_id": 1,
  "quantity": "100.00",
  "min_quantity": "10.00",
  "location": "Стеллаж А-1",
  "last_updated": "2024-01-01T12:00:00Z",
  "part": {
    "id": 1,
    "name": "Моторное масло 5W-30",
    "part_number": "OIL-001",
    "brand": "Castrol",
    "price": "5000.00",
    "unit": "л",
    "category": "consumables"
  }
}
```

**Возможные ошибки:**
- `400 Bad Request` - Позиция для этой запчасти уже существует
- `404 Not Found` - Запчасть не найдена

---

### POST `/api/v1/warehouse/transactions/incoming`
**Описание:** Приход товара на склад (увеличение количества)

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "warehouse_item_id": 1,
  "transaction_type": "incoming",
  "quantity": "50.00",
  "price": "4800.00",
  "order_id": null
}
```

**Поля:**
- `warehouse_item_id` (integer, required) - ID позиции склада
- `transaction_type` (enum, required) - Должен быть `incoming`
- `quantity` (decimal, required) - Количество для прихода
- `price` (decimal, optional) - Цена за единицу
- `order_id` (integer, optional) - ID заказа поставщика (если есть)

**Особенности:**
- Автоматически увеличивает количество на складе
- Создает запись транзакции
- `employee_id` устанавливается автоматически из текущего пользователя

**Ответ:**
```json
{
  "id": 1,
  "warehouse_item_id": 1,
  "transaction_type": "incoming",
  "quantity": "50.00",
  "price": "4800.00",
  "order_id": null,
  "employee_id": 2,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Возможные ошибки:**
- `400 Bad Request` - Тип транзакции должен быть `incoming`
- `400 Bad Request` - У пользователя не привязан сотрудник
- `404 Not Found` - Позиция склада не найдена

---

### GET `/api/v1/warehouse/low-stock`
**Описание:** Получение позиций с низким остатком (количество <= минимального)

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса:** Нет

**Ответ:**
```json
[
  {
    "id": 1,
    "part_id": 1,
    "quantity": "5.00",
    "min_quantity": "10.00",
    "location": "Стеллаж А-1",
    "last_updated": "2024-01-01T12:00:00Z",
    "part": {
      "id": 1,
      "name": "Моторное масло 5W-30",
      "part_number": "OIL-001",
      "brand": "Castrol",
      "price": "5000.00",
      "unit": "л",
      "category": "consumables"
    }
  }
]
```

---

## Employees - Сотрудники

### GET `/api/v1/employees/`
**Описание:** Получение списка всех сотрудников

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "full_name": "Иванов Иван Иванович",
    "position": "Механик",
    "phone": "+79001234567",
    "email": "ivanov@example.com",
    "hire_date": "2023-01-01",
    "salary_base": "60000.00",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": null
  }
]
```

---

### GET `/api/v1/employees/{employee_id}`
**Описание:** Получение сотрудника по ID

**Права доступа:** Требуется авторизация (любая роль)

**Параметры запроса (Path):**
- `employee_id` (integer, required) - ID сотрудника

**Ответ:**
```json
{
  "id": 1,
  "full_name": "Иванов Иван Иванович",
  "position": "Механик",
  "phone": "+79001234567",
  "email": "ivanov@example.com",
  "hire_date": "2023-01-01",
  "salary_base": "60000.00",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": null
}
```

---

### POST `/api/v1/employees/`
**Описание:** Создание нового сотрудника

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "full_name": "Иванов Иван Иванович",
  "position": "Механик",
  "phone": "+79001234567",
  "email": "ivanov@example.com",
  "hire_date": "2023-01-01",
  "salary_base": "60000.00"
}
```

**Поля:**
- `full_name` (string, required) - ФИО сотрудника
- `position` (string, required) - Должность
- `phone` (string, optional) - Телефон
- `email` (string, optional) - Email
- `hire_date` (date, required) - Дата приема на работу
- `salary_base` (decimal, required) - Базовая зарплата

**Ответ:**
```json
{
  "id": 1,
  "full_name": "Иванов Иван Иванович",
  "position": "Механик",
  "phone": "+79001234567",
  "email": "ivanov@example.com",
  "hire_date": "2023-01-01",
  "salary_base": "60000.00",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": null
}
```

---

### PUT `/api/v1/employees/{employee_id}`
**Описание:** Обновление данных сотрудника

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `employee_id` (integer, required) - ID сотрудника

**Параметры запроса (Body):**
```json
{
  "position": "Старший механик",
  "salary_base": "70000.00",
  "is_active": true
}
```

**Поля (все опциональны):**
- `full_name`, `position`, `phone`, `email`, `salary_base`, `is_active`

**Ответ:**
```json
{
  "id": 1,
  "full_name": "Иванов Иван Иванович",
  "position": "Старший механик",
  "phone": "+79001234567",
  "email": "ivanov@example.com",
  "hire_date": "2023-01-01",
  "salary_base": "70000.00",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Salary - Зарплата

### GET `/api/v1/salary/`
**Описание:** Получение списка всех расчетов зарплаты

**Права доступа:** ACCOUNTANT, ADMIN

**Параметры запроса (Query):**
- `skip` (integer, default: 0) - Количество записей для пропуска
- `limit` (integer, default: 100) - Максимальное количество записей

**Ответ:**
```json
[
  {
    "id": 1,
    "employee_id": 1,
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "base_salary": "60000.00",
    "bonus": "15000.00",
    "penalty": "0.00",
    "total": "75000.00",
    "status": "calculated",
    "created_at": "2024-02-01T00:00:00Z",
    "paid_at": null
  }
]
```

**Статусы зарплаты:**
- `draft` - Черновик
- `calculated` - Рассчитана
- `paid` - Выплачена

---

### GET `/api/v1/salary/{salary_id}`
**Описание:** Получение расчета зарплаты по ID

**Права доступа:** ACCOUNTANT, ADMIN

**Параметры запроса (Path):**
- `salary_id` (integer, required) - ID расчета зарплаты

**Ответ:**
```json
{
  "id": 1,
  "employee_id": 1,
  "period_start": "2024-01-01",
  "period_end": "2024-01-31",
  "base_salary": "60000.00",
  "bonus": "15000.00",
  "penalty": "0.00",
  "total": "75000.00",
  "status": "calculated",
  "created_at": "2024-02-01T00:00:00Z",
  "paid_at": null
}
```

---

### POST `/api/v1/salary/calculate`
**Описание:** Расчет зарплаты сотрудника за период

**Права доступа:** ACCOUNTANT, ADMIN

**Параметры запроса (Body):**
```json
{
  "employee_id": 1,
  "period_start": "2024-01-01",
  "period_end": "2024-01-31"
}
```

**Поля:**
- `employee_id` (integer, required) - ID сотрудника
- `period_start` (date, required) - Начало периода
- `period_end` (date, required) - Конец периода

**Особенности:**
- Базовая зарплата берется из данных сотрудника
- Бонус рассчитывается как 5% от базовой зарплаты за каждый выполненный заказ-наряд за период
- Штрафы пока не реализованы (0)
- Итоговая сумма = базовая + бонус - штраф
- Нельзя создать два расчета за один период для одного сотрудника

**Ответ:**
```json
{
  "id": 1,
  "employee_id": 1,
  "period_start": "2024-01-01",
  "period_end": "2024-01-31",
  "base_salary": "60000.00",
  "bonus": "15000.00",
  "penalty": "0.00",
  "total": "75000.00",
  "status": "calculated",
  "created_at": "2024-02-01T00:00:00Z",
  "paid_at": null
}
```

**Возможные ошибки:**
- `400 Bad Request` - Расчет зарплаты за этот период уже существует
- `404 Not Found` - Сотрудник не найден

---

### POST `/api/v1/salary/{salary_id}/pay`
**Описание:** Отметка о выплате зарплаты

**Права доступа:** ACCOUNTANT, ADMIN

**Параметры запроса (Path):**
- `salary_id` (integer, required) - ID расчета зарплаты

**Особенности:**
- Устанавливает статус `paid`
- Устанавливает `paid_at` на текущее время

**Ответ:**
```json
{
  "id": 1,
  "employee_id": 1,
  "period_start": "2024-01-01",
  "period_end": "2024-01-31",
  "base_salary": "60000.00",
  "bonus": "15000.00",
  "penalty": "0.00",
  "total": "75000.00",
  "status": "paid",
  "created_at": "2024-02-01T00:00:00Z",
  "paid_at": "2024-02-05T10:00:00Z"
}
```

**Возможные ошибки:**
- `404 Not Found` - Расчет зарплаты не найден

---

## Payments - Платежи

### POST `/api/v1/payments/yookassa/create`
**Описание:** Создание платежа через ЮKassa

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "order_id": 1,
  "amount": "15000.00",
  "return_url": "https://example.com/payment/return"
}
```

**Поля:**
- `order_id` (integer, required) - ID заказ-наряда
- `amount` (decimal, required) - Сумма платежа
- `return_url` (string, optional) - URL для возврата после оплаты

**Ответ:**
```json
{
  "id": "payment_id_from_yookassa",
  "status": "pending",
  "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/..."
}
```

---

### POST `/api/v1/payments/yookassa/webhook`
**Описание:** Webhook для обработки уведомлений от ЮKassa

**Права доступа:** Публичный endpoint (не требует авторизации, но должен проверять подпись от ЮKassa)

**Параметры запроса (Body):**
```json
{
  "event": "payment.succeeded",
  "object": {
    "id": "payment_id",
    "status": "succeeded",
    "amount": {
      "value": "15000.00",
      "currency": "RUB"
    },
    "metadata": {
      "order_id": "1"
    }
  }
}
```

**Особенности:**
- Используется для получения уведомлений о статусе платежа
- Обновляет статус платежа в системе
- Обновляет `paid_amount` в заказ-наряде

**Ответ:**
```json
{
  "status": "ok"
}
```

---

## Integrations - Интеграции

### GET `/api/v1/integrations/gibdd/vehicle/{vin}`
**Описание:** Проверка транспортного средства в базе ГИБДД

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Path):**
- `vin` (string, required) - VIN номер транспортного средства

**Ответ:**
```json
{
  "vin": "1HGBH41JXMN109186",
  "status": "ok",
  "data": {
    "brand": "Toyota",
    "model": "Camry",
    "year": 2020,
    "registration_date": "2020-01-15"
  }
}
```

**Примечание:** Реализация зависит от конкретного API ГИБДД

---

### GET `/api/v1/integrations/suppliers/search`
**Описание:** Поиск запчастей у поставщиков

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Query):**
- `query` (string, required) - Поисковый запрос (название или артикул запчасти)

**Ответ:**
```json
[
  {
    "supplier": "Поставщик 1",
    "name": "Моторное масло 5W-30",
    "part_number": "OIL-001",
    "price": "4800.00",
    "availability": true,
    "delivery_days": 3
  }
]
```

---

### POST `/api/v1/integrations/suppliers/order`
**Описание:** Создание заказа у поставщика

**Права доступа:** MANAGER, ADMIN

**Параметры запроса (Body):**
```json
{
  "supplier_id": 1,
  "items": [
    {
      "part_id": 1,
      "quantity": 10,
      "price": "4800.00"
    }
  ],
  "delivery_address": "г. Москва, ул. Примерная, д. 1"
}
```

**Ответ:**
```json
{
  "order_id": "SUP-20240101-001",
  "status": "created",
  "estimated_delivery": "2024-01-04"
}
```

---

## Общие примечания

### Пагинация
Большинство endpoints для получения списков поддерживают пагинацию через параметры `skip` и `limit`:
- `skip` - количество записей для пропуска (по умолчанию 0)
- `limit` - максимальное количество записей в ответе (по умолчанию 100)

### Формат дат и времени
- Даты: `YYYY-MM-DD` (например, `2024-01-01`)
- Дата и время: ISO 8601 формат `YYYY-MM-DDTHH:MM:SSZ` (например, `2024-01-01T10:00:00Z`)

### Формат денежных сумм
Все денежные суммы передаются в формате строки с двумя знаками после запятой (например, `"15000.00"`)

### Обработка ошибок
При возникновении ошибки API возвращает JSON объект с описанием:
```json
{
  "detail": "Описание ошибки"
}
```

### Версионирование API
Текущая версия API: `v1`
Базовый путь: `/api/v1`



