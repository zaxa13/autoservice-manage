# ИНСТРУКЦИЯ: КАК ИСПОЛЬЗОВАТЬ ТОКЕН В SWAGGER UI

## ✅ ПРАВИЛЬНЫЙ СПОСОБ

### Шаг 1: Получите токен через `/auth/login`

1. Откройте эндпоинт `POST /api/v1/auth/login`
2. Нажмите "Try it out"
3. Заполните форму:
   - `username`: ваш username
   - `password`: ваш пароль
4. Нажмите "Execute"
5. **ВАЖНО**: Скопируйте **ТОЛЬКО значение** из поля `access_token` в ответе

**Пример ответа:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImV4cCI6MTcx...",
  "token_type": "bearer"
}
```

**СКОПИРУЙТЕ ТОЛЬКО:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImV4cCI6MTcx...
```

**НЕ КОПИРУЙТЕ:**
- ❌ `"access_token": "..."` (с кавычками)
- ❌ `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (с префиксом Bearer)
- ❌ Весь JSON объект

### Шаг 2: Вставьте токен в Swagger Authorize

1. Нажмите кнопку **"Authorize"** (🔒 замок) в правом верхнем углу Swagger UI
2. В модальном окне вы увидите **"HTTPBearer (http, Bearer)"**
3. В поле **"Value:"** вставьте **ТОЛЬКО токен** (без "Bearer", без кавычек, без пробелов)
4. Нажмите **"Authorize"**
5. Нажмите **"Close"**

**Пример того, что должно быть в поле:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImV4cCI6MTcxMjM0NTY3OH0.abc123def456...
```

### Шаг 3: Используйте защищенные эндпоинты

Теперь все защищенные эндпоинты будут автоматически использовать ваш токен.

## ❌ ЧАСТЫЕ ОШИБКИ

### Ошибка 1: Добавление "Bearer" вручную
**НЕПРАВИЛЬНО:**
```
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**ПРАВИЛЬНО:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Почему:** FastAPI `HTTPBearer` автоматически добавляет "Bearer " при формировании заголовка. Если вы добавите его вручную, получится "Bearer Bearer token", что неправильно.

### Ошибка 2: Копирование с кавычками
**НЕПРАВИЛЬНО:**
```
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**ПРАВИЛЬНО:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Ошибка 3: Копирование всего поля access_token
**НЕПРАВИЛЬНО:**
```
"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**ПРАВИЛЬНО:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Ошибка 4: Пробелы в начале или конце
**НЕПРАВИЛЬНО:**
```
 eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... 
```

**ПРАВИЛЬНО:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 🔍 ПРОВЕРКА

После авторизации в Swagger:

1. Откройте любой защищенный эндпоинт (например, `GET /api/v1/auth/me`)
2. Нажмите "Try it out"
3. Нажмите "Execute"
4. Если все правильно, вы увидите данные пользователя
5. Если видите ошибку 401 "Неверный токен", проверьте:
   - Правильно ли скопирован токен (без "Bearer", без кавычек)
   - Не истек ли токен (время жизни 30 минут)
   - Получили ли вы новый токен после перезапуска backend

## 🐛 ДИАГНОСТИКА

Если токен не работает, проверьте логи backend. В логах вы увидите:
- Длину токена
- Превью токена (первые и последние символы)
- Конкретную ошибку декодирования

**Пример успешного лога:**
```
Token received (length: 200, preview: eyJhbGciOi...xyz123456)
User authenticated successfully: user_id=1, username=admin
```

**Пример ошибки:**
```
Failed to decode token. Token length: 50, preview: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 💡 СОВЕТЫ

1. **Копируйте токен из поля `access_token`** - это чистое значение без кавычек
2. **Используйте новый токен** после перезапуска backend или изменения SECRET_KEY
3. **Проверяйте срок действия** - токены действуют 30 минут
4. **Используйте кнопку "Authorize"** - не вставляйте токен вручную в заголовки запросов

