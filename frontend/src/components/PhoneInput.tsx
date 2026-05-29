import { forwardRef } from 'react'
import { InputAdornment, TextField, type TextFieldProps } from '@mui/material'

import { digitsToStored, formatNationalMask, parsePhoneDigits } from '../utils/phone'

type Props = Omit<TextFieldProps, 'value' | 'onChange' | 'type'> & {
  /** Номер в формате хранения (`+7XXXXXXXXXX`) или любой legacy-формат. */
  value: string
  /** Эмитит номер в формате хранения (`+7XXXXXXXXXX`) либо `''` если поле пустое. */
  onChange: (stored: string) => void
  /** Включает подсветку ошибки и helperText до достижения 10 цифр. */
  validate?: boolean
}

/**
 * Поле ввода телефона с фиксированным префиксом `+7` и маской `XXX XXX XX XX`.
 * Префикс висит в InputAdornment — не редактируется, не подменяется.
 */
const PhoneInput = forwardRef<HTMLDivElement, Props>(function PhoneInput(
  { value, onChange, validate, error, helperText, InputProps, inputProps, ...rest },
  ref,
) {
  const digits = parsePhoneDigits(value)
  const masked = formatNationalMask(digits)
  const incomplete = digits.length > 0 && digits.length < 10

  return (
    <TextField
      ref={ref}
      value={masked}
      onChange={(e) => {
        const next = parsePhoneDigits(e.target.value)
        onChange(digitsToStored(next))
      }}
      placeholder="999 123 45 67"
      error={Boolean(error) || (validate ? incomplete : false)}
      helperText={
        helperText !== undefined
          ? helperText
          : validate && incomplete
            ? 'Нужно 10 цифр после +7'
            : undefined
      }
      InputProps={{
        ...InputProps,
        startAdornment: (
          <InputAdornment position="start" sx={{ mr: 0.5 }}>
            <span style={{ fontWeight: 700, color: '#0F172A', letterSpacing: '0.02em' }}>+7</span>
          </InputAdornment>
        ),
        sx: { fontVariantNumeric: 'tabular-nums', letterSpacing: '0.01em', ...(InputProps?.sx ?? {}) },
      }}
      inputProps={{
        inputMode: 'tel',
        autoComplete: 'tel-national',
        maxLength: 13, // "XXX XXX XX XX" = 13 символов
        ...inputProps,
      }}
      {...rest}
    />
  )
})

export default PhoneInput
