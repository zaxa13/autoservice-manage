-- Исправление значений enum в базе данных
-- Enum в миграции определен как: 'NEW', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'

-- Выводим текущие статусы перед обновлением
SELECT 'Статусы ДО обновления:' as info;
SELECT status, COUNT(*) as count FROM orders GROUP BY status;

-- Обновляем статусы
UPDATE orders SET status = 'IN_PROGRESS' WHERE status IN ('in_progress', 'in_work', 'IN_WORK');
SELECT 'Обновлено на IN_PROGRESS: ' || changes() as result;

UPDATE orders SET status = 'NEW' WHERE status = 'new';
SELECT 'Обновлено на NEW: ' || changes() as result;

UPDATE orders SET status = 'COMPLETED' WHERE status = 'completed';
SELECT 'Обновлено на COMPLETED: ' || changes() as result;

UPDATE orders SET status = 'CANCELLED' WHERE status = 'cancelled';
SELECT 'Обновлено на CANCELLED: ' || changes() as result;-- Выводим финальные статусы после обновления
SELECT '';
SELECT 'Статусы ПОСЛЕ обновления:' as info;
SELECT status, COUNT(*) as count FROM orders GROUP BY status;SELECT 'Готово! Все статусы приведены к формату enum (верхний регистр)' as result;