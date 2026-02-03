# API марок и моделей автомобилей — краткая шпаргалка для фронтенда

## Обзор

API для работы со справочником марок и моделей. Подходит для автодополнения при выборе марки/модели (например, при создании ТС).

**Базовый путь:** `/api/v1/vehicle-brands`

**Авторизация:** все запросы требуют заголовок `Authorization: Bearer <access_token>`.

---

## Эндпоинты

### 1. Импорт марок и моделей (для админа/менеджера)

```
POST /api/v1/vehicle-brands/import
```

**Тело запроса:**
```json
{
  "brands": [
    { "name": "Toyota", "models": ["Camry", "Corolla", "RAV4"] },
    { "name": "Lada", "models": ["Vesta", "Granta", "Niva Legend"] }
  ]
}
```

**Ответ:** `{ "message": "Данные успешно импортированы", "brands_count": 2 }`

**Когда вызывать:** при первоначальной настройке или обновлении справочника (страница настроек, админка).

---

### 2. Список всех марок

```
GET /api/v1/vehicle-brands/
```

**Ответ:**
```json
{
  "brands": [
    { "id": 1, "name": "Audi" },
    { "id": 2, "name": "BMW" },
    { "id": 3, "name": "Toyota" }
  ]
}
```

**Пример (axios):**
```javascript
const { data } = await api.get('/vehicle-brands/')
const brands = data.brands  // [{ id, name }, ...] — для select передавайте brand_id в заказ
```

**Когда вызывать:** при загрузке формы (выпадающий список марок).

---

### 3. Модели по выбранной марке

```
POST /api/v1/vehicle-brands/models
```

**Тело запроса** (один из вариантов):
```json
{ "brand": "Toyota" }
```
или (предпочтительно — по id):
```json
{ "brand_id": 3 }
```

**Ответ:**
```json
{
  "models": [
    { "id": 1, "name": "Camry" },
    { "id": 2, "name": "Corolla" },
    { "id": 3, "name": "RAV4" }
  ]
}
```

**Пример (axios):**
```javascript
const { data } = await api.post('/vehicle-brands/models', { brand_id: selectedBrandId })
const models = data.models  // [{ id, name }, ...] — для заказа передавайте model_id
```

**Когда вызывать:** после выбора пользователем марки (загрузить модели во второй выпадающий список).

---

## Сценарий для формы «Марка + модель»

1. При монтировании: `GET /vehicle-brands/` → `[{ id, name }, ...]` для select марок.
2. При выборе марки: `POST /vehicle-brands/models` с `{ brand_id: selectedBrand.id }` → `[{ id, name }, ...]` для select моделей.
3. В заказ-наряд передавать `brand_id` и `model_id` (не строки) — целостность данных и нормализация.

---

## Обработка ошибок

- `401` — нет или невалидный токен.
- `403` — нет прав (для import — нужны MANAGER или ADMIN).
- `404` — марка не найдена (только для `POST /models`).
