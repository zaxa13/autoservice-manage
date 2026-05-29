/**
 * Утилиты телефона для российских мобильных номеров.
 *
 * Единый формат хранения: `+7XXXXXXXXXX` (12 символов, без пробелов).
 * Единый формат отображения: `+7 XXX XXX XX XX`.
 *
 * На вход принимаем что угодно (legacy `89...`, `7...`, +7 с пробелами,
 * скобками, дефисами) — парсер берёт только цифры и приводит к 10-значной
 * национальной части.
 */

const RUSSIAN_PHONE_DIGITS = 10

/** Извлечь до 10 цифр национальной части телефона из произвольного ввода. */
export function parsePhoneDigits(raw: string | null | undefined): string {
  if (!raw) return ''
  const s = String(raw).trim()
  // Каноничный формат хранения `+7XXXXXXXXXX`: национальная часть всегда после `+7`.
  // Это критично: без явной проверки префикса round-trip ломается, когда
  // пользователь стирает цифры — обратно прилетают всё новые ведущие `7`.
  if (s.startsWith('+7')) {
    return s.slice(2).replace(/\D/g, '').slice(0, RUSSIAN_PHONE_DIGITS)
  }
  // Свободный ввод: цифры и разделители. При полном номере с кодом страны
  // (7/8 + 10 цифр) сбрасываем ведущую цифру. Короткий ввод оставляем как есть.
  let digits = s.replace(/\D/g, '')
  if (digits.length > RUSSIAN_PHONE_DIGITS && (digits.startsWith('7') || digits.startsWith('8'))) {
    digits = digits.slice(1)
  }
  return digits.slice(0, RUSSIAN_PHONE_DIGITS)
}

/** Маска для редактируемой части после `+7 ` — `XXX XXX XX XX`. */
export function formatNationalMask(digits: string): string {
  const d = digits.replace(/\D/g, '').slice(0, RUSSIAN_PHONE_DIGITS)
  const p1 = d.slice(0, 3)
  const p2 = d.slice(3, 6)
  const p3 = d.slice(6, 8)
  const p4 = d.slice(8, 10)
  let out = p1
  if (d.length >= 4) out += ' ' + p2
  if (d.length >= 7) out += ' ' + p3
  if (d.length >= 9) out += ' ' + p4
  return out
}

/** Полное форматирование для отображения. Возвращает исходник для неполных/чужих номеров. */
export function formatPhoneDisplay(stored: string | null | undefined): string {
  if (!stored) return ''
  const digits = parsePhoneDigits(stored)
  if (digits.length !== RUSSIAN_PHONE_DIGITS) return String(stored)
  return `+7 ${formatNationalMask(digits)}`
}

/** Конвертация 10 цифр национальной части → формат хранения `+7XXXXXXXXXX`. */
export function digitsToStored(digits: string): string {
  const d = digits.replace(/\D/g, '').slice(0, RUSSIAN_PHONE_DIGITS)
  return d.length === 0 ? '' : `+7${d}`
}

/** Проверка валидности номера в формате хранения. */
export function isValidRussianPhone(stored: string | null | undefined): boolean {
  if (!stored) return false
  return /^\+7\d{10}$/.test(stored)
}
