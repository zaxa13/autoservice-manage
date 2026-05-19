import { useRef, useState } from 'react'
import {
  Box, ButtonBase, IconButton, Popover, Typography,
} from '@mui/material'
import {
  CalendarMonthRounded,
  ChevronLeftRounded,
  ChevronRightRounded,
  CloseRounded,
} from '@mui/icons-material'
import {
  addDays, addMonths, eachDayOfInterval, endOfWeek,
  format, isSameDay, isSameMonth, parseISO, startOfMonth, startOfWeek,
} from 'date-fns'
import { ru } from 'date-fns/locale'


// ─── Месячный календарь-сетка ────────────────────────────────────────────────

export function MonthCalendar({
  selectedDate,
  onPick,
}: {
  selectedDate: Date | null
  onPick: (d: Date) => void
}) {
  const [viewMonth, setViewMonth] = useState(() => startOfMonth(selectedDate ?? new Date()))
  const today = new Date()

  const gridStart = startOfWeek(startOfMonth(viewMonth), { weekStartsOn: 1 })
  const gridEnd = endOfWeek(addDays(gridStart, 41), { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: gridStart, end: gridEnd }).slice(0, 42)

  const weekdayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

  return (
    <Box sx={{ p: 2, width: 320 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <IconButton size="small" onClick={() => setViewMonth(addMonths(viewMonth, -1))}>
          <ChevronLeftRounded />
        </IconButton>
        <Typography sx={{ fontWeight: 800, fontSize: '0.95rem', textTransform: 'capitalize' }}>
          {format(viewMonth, 'LLLL yyyy', { locale: ru })}
        </Typography>
        <IconButton size="small" onClick={() => setViewMonth(addMonths(viewMonth, 1))}>
          <ChevronRightRounded />
        </IconButton>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5, mb: 0.5 }}>
        {weekdayLabels.map((wd, i) => (
          <Typography
            key={wd}
            variant="caption"
            sx={{
              textAlign: 'center',
              fontWeight: 700,
              color: i >= 5 ? 'error.light' : 'text.secondary',
              fontSize: '0.72rem',
            }}
          >
            {wd}
          </Typography>
        ))}
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5 }}>
        {days.map((d) => {
          const inMonth = isSameMonth(d, viewMonth)
          const isToday = isSameDay(d, today)
          const isSelected = selectedDate ? isSameDay(d, selectedDate) : false
          const dayOfWeek = (d.getDay() + 6) % 7
          const isWeekend = dayOfWeek >= 5
          return (
            <ButtonBase
              key={d.toISOString()}
              onClick={() => onPick(d)}
              sx={{
                aspectRatio: '1 / 1',
                borderRadius: 1.5,
                fontWeight: isToday || isSelected ? 800 : 600,
                fontSize: '0.85rem',
                color: isSelected
                  ? 'primary.contrastText'
                  : !inMonth
                    ? 'text.disabled'
                    : isWeekend
                      ? 'error.main'
                      : 'text.primary',
                bgcolor: isSelected ? 'primary.main' : 'transparent',
                border: isToday && !isSelected ? 2 : 0,
                borderColor: 'primary.main',
                transition: 'background-color 0.15s',
                '&:hover': {
                  bgcolor: isSelected ? 'primary.dark' : 'action.hover',
                },
              }}
            >
              {format(d, 'd')}
            </ButtonBase>
          )
        })}
      </Box>
    </Box>
  )
}


// ─── Кнопка-поле даты в стиле приложения ─────────────────────────────────────

export interface DateFieldProps {
  /** Дата в формате yyyy-MM-dd либо '' если не выбрана. */
  value: string
  onChange: (value: string) => void
  label?: string
  placeholder?: string
  /** Можно ли очистить (показывает «крестик»). По умолчанию true. */
  clearable?: boolean
  size?: 'small' | 'medium'
  minWidth?: number
}

export function DateField({
  value, onChange,
  label,
  placeholder = 'Выберите дату',
  clearable = true,
  size = 'medium',
  minWidth = 200,
}: DateFieldProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const ref = useRef<HTMLButtonElement>(null)

  const dateObj = value ? parseISO(value + 'T00:00:00') : null
  const displayLabel = dateObj
    ? format(dateObj, 'd MMMM yyyy', { locale: ru })
    : placeholder
  const weekday = dateObj ? format(dateObj, 'EEEE', { locale: ru }) : null

  const py = size === 'small' ? 0.85 : 1.1
  const fontSize = size === 'small' ? '0.85rem' : '0.95rem'

  return (
    <Box sx={{ minWidth }}>
      {label && (
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            color: 'text.secondary',
            fontWeight: 700,
            mb: 0.5,
            ml: 0.5,
            fontSize: '0.72rem',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          {label}
        </Typography>
      )}
      <ButtonBase
        ref={ref}
        onClick={(e) => setAnchorEl(e.currentTarget)}
        sx={(t) => ({
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1.5,
          py,
          borderRadius: 2,
          border: '1px solid',
          borderColor: anchorEl ? 'primary.main' : 'divider',
          bgcolor: 'background.paper',
          transition: 'border-color 0.15s, box-shadow 0.15s',
          '&:hover': {
            borderColor: 'primary.main',
            boxShadow: `0 0 0 4px ${t.palette.action.hover}`,
          },
        })}
      >
        <CalendarMonthRounded color="primary" fontSize={size === 'small' ? 'small' : 'medium'} />
        <Box sx={{ flex: 1, textAlign: 'left', lineHeight: 1.15, minWidth: 0 }}>
          <Typography
            sx={{
              fontWeight: 700,
              fontSize,
              color: dateObj ? 'text.primary' : 'text.disabled',
              textTransform: 'none',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {displayLabel}
          </Typography>
          {weekday && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ textTransform: 'capitalize', display: 'block' }}
            >
              {weekday}
            </Typography>
          )}
        </Box>
        {clearable && dateObj && (
          <IconButton
            size="small"
            component="span"
            onClick={(e) => { e.stopPropagation(); onChange('') }}
            sx={{ ml: 0.5 }}
          >
            <CloseRounded fontSize="small" />
          </IconButton>
        )}
      </ButtonBase>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        slotProps={{ paper: { sx: { borderRadius: 3, mt: 1, boxShadow: 6 } } }}
      >
        <MonthCalendar
          selectedDate={dateObj}
          onPick={(d) => {
            onChange(format(d, 'yyyy-MM-dd'))
            setAnchorEl(null)
          }}
        />
      </Popover>
    </Box>
  )
}
