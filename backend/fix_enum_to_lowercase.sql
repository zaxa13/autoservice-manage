-- Преобразование значений enum в нижний регистр (значения Python enum)
-- Python enum использует: "new", "in_progress", "completed", "cancelled"

-- Выводим текущие статусы перед обновлением
SELECT '=== Статусы ДО обновления ===' as info;
SELECT status, COUNT(*) as count FROM orders GROUP BY status;

-- Обновляем статусы на значения Python enum (нижний регистр)
UPDATE orders SET status = 'in_progress' WHERE status = 'IN_PROGRESS';
SELECT '✓ Обновлено на in_progress: ' || changes() || ' записей' as result;

UPDATE orders SET status = 'new' WHERE status = 'NEW';
SELECT '✓ Обновлено на new: ' || changes() || ' записей' as result;

UPDATE orders SET status = 'completed' WHERE status = 'COMPLETED';
SELECT '✓ Обновлено на completed: ' || changes() || ' записей' as result;

UPDATE orders SET status = 'cancelled' WHERE status = 'CANCELLED';
SELECT '✓ Обновлено на cancelled: ' || changes() || ' записей' as result;

-- Выводим финальные статусы после обновления
SELECT '';
SELECT '=== Статусы ПОСЛЕ обновления ===' as info;
SELECT status, COUNT(*) as count FROM orders GROUP BY status;

SELECT '';
SELECT '✓ Готово! Все статусы приведены к значениям Python enum (нижний регистр)' as result;
