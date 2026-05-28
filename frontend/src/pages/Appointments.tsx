import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Stack,
  Card,
  CardContent,
  alpha,
  Chip,
  Menu,
  MenuItem,
  Tooltip,
  Divider,
  InputAdornment,
  Collapse,
  Popover,
  ButtonBase,
} from '@mui/material'
import {
  AddRounded,
  DeleteOutlineRounded,
  CalendarMonthRounded,
  PersonOutlineRounded,
  PhoneEnabledRounded,
  AddCircleOutlineRounded,
  EditRounded,
  DeleteRounded,
  ReceiptLongRounded,
  DirectionsCarRounded,
  SearchRounded,
  CheckCircleRounded,
  ArrowForwardIosRounded,
  ArrowBackIosNewRounded,
  ExpandMoreRounded,
  OpenInNewRounded,
  ChevronLeftRounded,
  ChevronRightRounded,
} from '@mui/icons-material'
import {
  DndContext,
  DragOverlay,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import api from '../services/api'
import {
  Appointment,
  AppointmentCreate,
  AppointmentPost,
  AppointmentPostCreate,
  AppointmentStatus,
  Customer,
  Vehicle,
  OrderCreate,
} from '../types'
import {
  addDays, addMonths, eachDayOfInterval, endOfWeek,
  format, isSameDay, isSameMonth, parseISO, startOfMonth, startOfWeek, subDays,
} from 'date-fns'
import { ru } from 'date-fns/locale'

// ─── Статусы ──────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<AppointmentStatus, { label: string; color: string }> = {
  scheduled: { label: 'Записан',      color: '#3B82F6' },
  confirmed: { label: 'Подтверждён',  color: '#14B8A6' },
  waiting:   { label: 'Ожидаем авто', color: '#F59E0B' },
  arrived:   { label: 'Авто на СТО',  color: '#10B981' },
  in_work:   { label: 'В работе',     color: '#8B5CF6' },
  ready:     { label: 'Готов',        color: '#22C55E' },
  completed: { label: 'Завершён',     color: '#94A3B8' },
  no_show:   { label: 'Не явился',    color: '#F97316' },
  cancelled: { label: 'Отменён',      color: '#EF4444' },
}

// Следующий логический статус (для быстрого продвижения)
const STATUS_NEXT: Partial<Record<AppointmentStatus, AppointmentStatus>> = {
  scheduled: 'confirmed',
  confirmed: 'waiting',
  waiting:   'arrived',
  arrived:   'in_work',
  in_work:   'ready',
  ready:     'completed',
}

const ALL_STATUSES = Object.keys(STATUS_CONFIG) as AppointmentStatus[]

// ─── Цвета постов (для шапки колонки) ─────────────────────────────────────────

const POST_COLORS = ['#6366F1', '#22C55E', '#F59E0B', '#EC4899', '#14B8A6', '#8B5CF6']

const DEFAULT_SLOT_HOURS = '9, 11, 13, 15, 17'

function parseSlotTimes(input: string): string[] {
  return input
    .split(/[,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((h) => {
      const n = parseInt(h, 10)
      if (Number.isNaN(n) || n < 0 || n > 23) return null
      return `${String(n).padStart(2, '0')}:00`
    })
    .filter((t): t is string => t !== null)
}

function formatSlotTimesForInput(slotTimes: string[] | undefined): string {
  if (!slotTimes?.length) return ''
  return slotTimes
    .map((t) => {
      const n = parseInt(t.substring(0, 2), 10)
      return Number.isNaN(n) ? t : String(n)
    })
    .join(', ')
}

function getPostColor(post: AppointmentPost, index: number): string {
  return post.color || POST_COLORS[index % POST_COLORS.length]
}

function timeToHHMM(t: string | undefined): string {
  if (!t) return ''
  const s = t.toString().trim()
  if (s.length >= 5) return s.substring(0, 5)
  return s
}

function vehicleLabel(v?: Vehicle): string {
  if (!v) return ''
  const brand = v.brand?.name ?? ''
  const model = v.model?.name ?? ''
  const plate = v.license_plate ? ` · ${v.license_plate}` : ''
  return `${brand} ${model}${plate}`.trim()
}

// ─── Месячный календарь-popover ──────────────────────────────────────────────

function MonthCalendar({
  selectedDate,
  onPick,
}: {
  selectedDate: Date
  onPick: (d: Date) => void
}) {
  const [viewMonth, setViewMonth] = useState(() => startOfMonth(selectedDate))
  const today = new Date()

  // 6 недель = 42 дня — сетка фиксированной высоты, без скачков
  const gridStart = startOfWeek(startOfMonth(viewMonth), { weekStartsOn: 1 })
  const gridEnd = endOfWeek(addDays(gridStart, 41), { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: gridStart, end: gridEnd }).slice(0, 42)

  const weekdayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

  return (
    <Box sx={{ p: 2, width: 320 }}>
      {/* Заголовок: ‹ Месяц Год › */}
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

      {/* Заголовки дней недели */}
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

      {/* Сетка дней 6×7 */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5 }}>
        {days.map((d) => {
          const inMonth = isSameMonth(d, viewMonth)
          const isToday = isSameDay(d, today)
          const isSelected = isSameDay(d, selectedDate)
          const dayOfWeek = (d.getDay() + 6) % 7 // 0=Пн … 6=Вс
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


// ─── Панель навигации по дате ────────────────────────────────────────────────

function DatePanel({
  selectedDate,
  onChange,
}: {
  selectedDate: string
  onChange: (d: string) => void
}) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const todayStr = format(new Date(), 'yyyy-MM-dd')
  const yesterdayStr = format(subDays(new Date(), 1), 'yyyy-MM-dd')
  const tomorrowStr = format(addDays(new Date(), 1), 'yyyy-MM-dd')
  const dateObj = parseISO(selectedDate + 'T00:00:00')
  const weekday = format(dateObj, 'EEEE', { locale: ru })
  const human = format(dateObj, 'd MMMM yyyy', { locale: ru })
  const monthYear = format(dateObj, 'LLLL yyyy', { locale: ru })

  const shift = (days: number) => {
    onChange(format(addDays(dateObj, days), 'yyyy-MM-dd'))
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const tag = target?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return
      if (anchorEl) return
      if (e.key === 'ArrowLeft') { e.preventDefault(); shift(-1) }
      else if (e.key === 'ArrowRight') { e.preventDefault(); shift(1) }
      else if (e.key.toLowerCase() === 't') { e.preventDefault(); onChange(todayStr) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, anchorEl])

  const quickChip = (label: string, value: string, key: string) => {
    const active = selectedDate === value
    return (
      <Chip
        key={key}
        label={label}
        clickable
        onClick={() => onChange(value)}
        color={active ? 'primary' : 'default'}
        variant={active ? 'filled' : 'outlined'}
        sx={{
          fontWeight: 700,
          borderRadius: 2,
          height: 36,
          px: 0.5,
          fontSize: '0.85rem',
        }}
      />
    )
  }

  return (
    <Paper
      sx={{
        p: 1.5,
        borderRadius: 3,
        mb: 2,
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        flexWrap: 'wrap',
      }}
    >
      {/* Стрелка влево */}
      <Tooltip title="Предыдущий день (←)">
        <IconButton
          onClick={() => shift(-1)}
          sx={{
            bgcolor: 'action.hover',
            borderRadius: 2,
            width: 44, height: 44,
            '&:hover': { bgcolor: 'action.selected' },
          }}
        >
          <ArrowBackIosNewRounded fontSize="small" />
        </IconButton>
      </Tooltip>

      {/* Чипы быстрого выбора */}
      <Stack direction="row" spacing={0.75}>
        {quickChip('Вчера', yesterdayStr, 'y')}
        {quickChip('Сегодня', todayStr, 't')}
        {quickChip('Завтра', tomorrowStr, 'tm')}
      </Stack>

      <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />

      {/* Текущая дата — крупно, как визуальный якорь */}
      <Box sx={{ flex: '1 1 auto', minWidth: 180, lineHeight: 1.15 }}>
        <Typography sx={{ fontWeight: 800, fontSize: '1.15rem', color: 'text.primary' }}>
          {human}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
          {weekday}
        </Typography>
      </Box>

      {/* Большая явная CTA «Календарь» */}
      <Tooltip title="Открыть календарь">
        <Button
          variant="contained"
          color="primary"
          size="large"
          startIcon={<CalendarMonthRounded />}
          onClick={(e) => setAnchorEl(e.currentTarget)}
          sx={{
            borderRadius: 2,
            fontWeight: 700,
            textTransform: 'none',
            px: 2,
            py: 1.1,
            fontSize: '0.95rem',
            boxShadow: 2,
          }}
        >
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', lineHeight: 1.1 }}>
            <Typography component="span" sx={{ fontWeight: 800, fontSize: '0.95rem', color: 'inherit' }}>
              Календарь
            </Typography>
            <Typography component="span" sx={{ fontSize: '0.7rem', opacity: 0.85, textTransform: 'capitalize' }}>
              {monthYear}
            </Typography>
          </Box>
        </Button>
      </Tooltip>

      {/* Стрелка вправо */}
      <Tooltip title="Следующий день (→)">
        <IconButton
          onClick={() => shift(1)}
          sx={{
            bgcolor: 'action.hover',
            borderRadius: 2,
            width: 44, height: 44,
            '&:hover': { bgcolor: 'action.selected' },
          }}
        >
          <ArrowForwardIosRounded fontSize="small" />
        </IconButton>
      </Tooltip>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
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
    </Paper>
  )
}

// ─── Чип статуса ─────────────────────────────────────────────────────────────

function StatusChip({
  status,
  onChange,
  size = 'small',
}: {
  status: AppointmentStatus
  onChange?: (s: AppointmentStatus) => void
  size?: 'small' | 'medium'
}) {
  const [anchor, setAnchor] = useState<null | HTMLElement>(null)
  const cfg = STATUS_CONFIG[status]

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation()
    if (onChange) setAnchor(e.currentTarget)
  }

  return (
    <>
      <Chip
        label={cfg.label}
        size={size}
        onClick={onChange ? handleClick : undefined}
        sx={{
          bgcolor: alpha(cfg.color, 0.15),
          color: cfg.color,
          fontWeight: 700,
          fontSize: '0.68rem',
          height: 20,
          cursor: onChange ? 'pointer' : 'default',
          '& .MuiChip-label': { px: 1 },
        }}
      />
      {onChange && (
        <Menu
          anchorEl={anchor}
          open={Boolean(anchor)}
          onClose={() => setAnchor(null)}
          onClick={(e) => e.stopPropagation()}
          PaperProps={{ sx: { borderRadius: 2, minWidth: 180 } }}
        >
          {ALL_STATUSES.map((s) => {
            const c = STATUS_CONFIG[s]
            return (
              <MenuItem
                key={s}
                selected={s === status}
                onClick={() => { onChange(s); setAnchor(null) }}
                sx={{ gap: 1.5 }}
              >
                <Box
                  sx={{
                    width: 10, height: 10, borderRadius: '50%',
                    bgcolor: c.color, flexShrink: 0,
                  }}
                />
                <Typography variant="body2">{c.label}</Typography>
                {s === status && <CheckCircleRounded sx={{ ml: 'auto', fontSize: 16, color: c.color }} />}
              </MenuItem>
            )
          })}
        </Menu>
      )}
    </>
  )
}

// ─── Карточка записи ──────────────────────────────────────────────────────────

function AppointmentCard({
  item,
  onDelete,
  postColor,
  isDragging,
  onStatusChange,
  onCreateOrder,
}: {
  item: Appointment
  onDelete: (id: number) => void
  postColor: string
  isDragging?: boolean
  onStatusChange?: (id: number, status: AppointmentStatus) => void
  onCreateOrder?: (item: Appointment) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const statusCfg = STATUS_CONFIG[item.status ?? 'scheduled']
  const nextStatus = STATUS_NEXT[item.status ?? 'scheduled']
  const vLabel = vehicleLabel(item.vehicle)
  const hasOrder = Boolean(item.order_id)

  const createOrderTooltip = hasOrder
    ? `Заказ-наряд #${item.order?.number ?? item.order_id} уже создан`
    : item.vehicle_id
      ? 'Создать заказ-наряд'
      : 'Привяжите автомобиль для создания наряда'

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: `4px solid ${statusCfg.color}`,
        bgcolor: alpha(statusCfg.color, 0.04),
        opacity: isDragging ? 0.6 : 1,
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 3 },
      }}
    >
      <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1 } }}>
        {/* Строка 1: время + статус + кнопки */}
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={0.5} sx={{ mb: 0.5 }}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, color: postColor, minWidth: 36 }}>
              {timeToHHMM(item.time)}
            </Typography>
            <StatusChip
              status={item.status ?? 'scheduled'}
              onChange={onStatusChange ? (s) => onStatusChange(item.id, s) : undefined}
            />
          </Stack>
          <Stack direction="row" spacing={0} sx={{ mr: -0.5 }}>
            {nextStatus && onStatusChange && (
              <Tooltip title={`→ ${STATUS_CONFIG[nextStatus].label}`}>
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); onStatusChange(item.id, nextStatus) }}
                  sx={{ color: STATUS_CONFIG[nextStatus].color, p: 0.5 }}
                >
                  <ArrowForwardIosRounded sx={{ fontSize: 13 }} />
                </IconButton>
              </Tooltip>
            )}
            {onCreateOrder && (
              <Tooltip title={createOrderTooltip}>
                <span>
                  <IconButton
                    size="small"
                    disabled={!item.vehicle_id || hasOrder}
                    onClick={(e) => { e.stopPropagation(); onCreateOrder(item) }}
                    sx={{ color: hasOrder ? 'success.main' : 'primary.main', p: 0.5 }}
                  >
                    <ReceiptLongRounded sx={{ fontSize: 16 }} />
                  </IconButton>
                </span>
              </Tooltip>
            )}
            <IconButton
              size="small"
              color="error"
              onClick={(e) => { e.stopPropagation(); onDelete(item.id) }}
              sx={{ p: 0.5 }}
            >
              <DeleteOutlineRounded sx={{ fontSize: 16 }} />
            </IconButton>
          </Stack>
        </Stack>

        {/* Строка 2: имя клиента + кнопка разворота */}
        <Box
          onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v) }}
          sx={{ cursor: 'pointer', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 0.5 }}
        >
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
              {item.customer_name}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
              {item.customer_phone}
            </Typography>
          </Box>
          <ExpandMoreRounded
            sx={{
              fontSize: 18,
              color: 'text.secondary',
              flexShrink: 0,
              mt: 0.25,
              transition: 'transform 0.2s',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          />
        </Box>

        {/* Автомобиль — всегда видно */}
        {vLabel && (
          <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mt: 0.5 }}>
            <DirectionsCarRounded sx={{ fontSize: 13, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary">
              {vLabel}
            </Typography>
          </Stack>
        )}

        {/* Разворачиваемая секция */}
        <Collapse in={expanded} timeout="auto">
          <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid', borderColor: 'divider' }}>

            {/* Комментарий */}
            {item.description && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: 'block', mb: 0.5, fontStyle: 'italic' }}
              >
                {item.description}
              </Typography>
            )}

            {/* Заказ-наряд */}
            {item.order ? (
              <Box
                component="a"
                href={`/orders?open=${item.order.id}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 0.5,
                  mt: 0.5,
                  px: 1,
                  py: 0.4,
                  borderRadius: 1.5,
                  bgcolor: alpha('#22C55E', 0.1),
                  border: '1px solid',
                  borderColor: alpha('#22C55E', 0.3),
                  color: '#16A34A',
                  textDecoration: 'none',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: alpha('#22C55E', 0.18) },
                }}
              >
                <ReceiptLongRounded sx={{ fontSize: 13 }} />
                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                  Наряд #{item.order.number}
                </Typography>
                <OpenInNewRounded sx={{ fontSize: 11 }} />
              </Box>
            ) : (
              !item.vehicle_id && (
                <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5 }}>
                  Нет автомобиля — наряд недоступен
                </Typography>
              )
            )}
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  )
}

// ─── Draggable обёртка ────────────────────────────────────────────────────────

function DraggableCard({
  item,
  postColor,
  onDelete,
  onStatusChange,
  onCreateOrder,
}: {
  item: Appointment
  postColor: string
  onDelete: (id: number) => void
  onStatusChange: (id: number, status: AppointmentStatus) => void
  onCreateOrder: (item: Appointment) => void
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `appointment-${item.id}`,
    data: { appointment: item },
  })
  return (
    <Box ref={setNodeRef} {...listeners} {...attributes} sx={{ mb: 1 }}>
      <AppointmentCard
        item={item}
        onDelete={onDelete}
        postColor={postColor}
        isDragging={isDragging}
        onStatusChange={onStatusChange}
        onCreateOrder={onCreateOrder}
      />
    </Box>
  )
}

// ─── Ячейка слота ─────────────────────────────────────────────────────────────

function SlotCell({
  postId,
  slotTime,
  postColor,
  children,
}: {
  postId: number
  slotTime: string
  postColor: string
  children: React.ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `slot-${postId}-${slotTime}`,
    data: { postId, slotTime },
  })
  return (
    <Box
      ref={setNodeRef}
      sx={{
        mb: 0.5,
        minHeight: 0,
        borderRadius: 1,
        border: '2px dashed',
        borderColor: isOver ? postColor : 'transparent',
        bgcolor: isOver ? alpha(postColor, 0.08) : 'transparent',
        transition: 'border-color 0.2s, background-color 0.2s',
        p: 0,
      }}
    >
      {children}
    </Box>
  )
}

// ─── Колонка поста ────────────────────────────────────────────────────────────

function PostColumn({
  post,
  appointments,
  postColor,
  onAddRecord,
  onAddRecordForSlot,
  onEditPost,
  onDeletePost,
  onDelete,
  onStatusChange,
  onCreateOrder,
}: {
  post: AppointmentPost
  appointments: Appointment[]
  postColor: string
  onAddRecord: () => void
  onAddRecordForSlot?: (slotTime: string) => void
  onEditPost?: (post: AppointmentPost) => void
  onDeletePost?: (post: AppointmentPost) => void
  onDelete: (id: number) => void
  onStatusChange: (id: number, status: AppointmentStatus) => void
  onCreateOrder: (item: Appointment) => void
}) {
  const slotTimes = post.slot_times && post.slot_times.length > 0 ? post.slot_times : null
  const canAdd = appointments.length < post.max_slots
  const canEditDelete = post.id > 0
  const hasSlotDroppables = Boolean(slotTimes && post.id > 0)
  const { setNodeRef, isOver } = useDroppable({
    id: `post-${post.id}`,
    data: hasSlotDroppables ? undefined : { postId: post.id },
  })

  return (
    <Paper
      ref={hasSlotDroppables ? undefined : setNodeRef}
      variant="outlined"
      sx={{
        minWidth: 290,
        maxWidth: 290,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 2,
        overflow: 'hidden',
        borderWidth: 2,
        borderColor: !hasSlotDroppables && isOver ? postColor : 'divider',
        bgcolor: !hasSlotDroppables && isOver ? alpha(postColor, 0.06) : 'background.paper',
        transition: 'border-color 0.2s, background-color 0.2s',
      }}
    >
      {/* Шапка поста */}
      <Box
        sx={{
          py: 1.5,
          px: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: alpha(postColor, 0.12),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 0.5,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            {post.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {appointments.length} / {post.max_slots} записей
          </Typography>
        </Box>
        {canEditDelete && (
          <Stack direction="row" spacing={0}>
            <IconButton size="small" onClick={() => onEditPost?.(post)} title="Редактировать пост">
              <EditRounded fontSize="small" />
            </IconButton>
            <IconButton size="small" color="error" onClick={() => onDeletePost?.(post)} title="Удалить пост">
              <DeleteRounded fontSize="small" />
            </IconButton>
          </Stack>
        )}
      </Box>

      {/* Тело колонки */}
      <Box sx={{ p: 1.5, flex: 1, minHeight: 120 }}>
        {slotTimes ? (
          <>
            {slotTimes.map((slotTime) => {
              const appointmentAtSlot = appointments.find(
                (a) => timeToHHMM(a.time) === slotTime
              )
              return (
                <SlotCell key={slotTime} postId={post.id} slotTime={slotTime} postColor={postColor}>
                  {appointmentAtSlot ? (
                    <DraggableCard
                      item={appointmentAtSlot}
                      postColor={postColor}
                      onDelete={onDelete}
                      onStatusChange={onStatusChange}
                      onCreateOrder={onCreateOrder}
                    />
                  ) : post.id > 0 && onAddRecordForSlot ? (
                    <Button
                      fullWidth
                      size="small"
                      startIcon={<AddCircleOutlineRounded />}
                      onClick={() => onAddRecordForSlot(slotTime)}
                      sx={{ borderStyle: 'dashed', justifyContent: 'flex-start', fontWeight: 600 }}
                      variant="outlined"
                    >
                      {slotTime} · Добавить
                    </Button>
                  ) : null}
                </SlotCell>
              )
            })}
            {/* Записи не попавшие ни в один слот */}
            {(() => {
              const matchedIds = new Set(
                slotTimes
                  .map((slotTime) => appointments.find((a) => timeToHHMM(a.time) === slotTime)?.id)
                  .filter((id): id is number => id != null)
              )
              const unmatched = appointments.filter((a) => !matchedIds.has(a.id))
              if (unmatched.length === 0) return null
              return (
                <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px dashed', borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                    Другие записи
                  </Typography>
                  {unmatched.map((item) => (
                    <DraggableCard
                      key={item.id}
                      item={item}
                      postColor={postColor}
                      onDelete={onDelete}
                      onStatusChange={onStatusChange}
                      onCreateOrder={onCreateOrder}
                    />
                  ))}
                </Box>
              )
            })()}
          </>
        ) : (
          <>
            {appointments.map((item) => (
              <DraggableCard
                key={item.id}
                item={item}
                postColor={postColor}
                onDelete={onDelete}
                onStatusChange={onStatusChange}
                onCreateOrder={onCreateOrder}
              />
            ))}
            {canAdd && post.id > 0 && (
              <Button
                fullWidth
                size="small"
                startIcon={<AddCircleOutlineRounded />}
                onClick={onAddRecord}
                sx={{ mt: 1, borderStyle: 'dashed' }}
                variant="outlined"
              >
                Добавить запись
              </Button>
            )}
          </>
        )}
      </Box>
    </Paper>
  )
}

// ─── Поиск клиента/авто в диалоге ─────────────────────────────────────────────

type SearchResult =
  | { type: 'customer'; customer: Customer; vehicles: Vehicle[] }
  | { type: 'vehicle'; vehicle: Vehicle; customer: Customer }
  | null

function ClientSearchField({
  onFound,
}: {
  onFound: (result: SearchResult) => void
}) {
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [result, setResult] = useState<SearchResult>(null)
  const [notFound, setNotFound] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const search = useCallback(async (q: string) => {
    const trimmed = q.trim()
    if (trimmed.length < 3) {
      setResult(null)
      setNotFound(false)
      return
    }
    setSearching(true)
    setNotFound(false)

    // Определяем тип поиска: гос.номер (буквы+цифры) или телефон
    const isPlate = /[а-яА-ЯёЁa-zA-Z]/.test(trimmed) && /\d/.test(trimmed) && !trimmed.startsWith('+') && !trimmed.startsWith('7') && !trimmed.startsWith('8')

    try {
      if (isPlate) {
        const res = await api.get('/vehicles/search/by-license-plate', { params: { license_plate: trimmed } })
        const vehicle: Vehicle = res.data
        const customer = vehicle.customer!
        setResult({ type: 'vehicle', vehicle, customer })
      } else {
        const res = await api.get<Customer[]>('/customers/search/by-phone', { params: { phone: trimmed } })
        if (res.data.length === 0) {
          setNotFound(true)
          setResult(null)
        } else {
          const customer = res.data[0]
          const vehiclesRes = await api.get<Vehicle[]>('/vehicles/', { params: { customer_id: customer.id } })
          setResult({ type: 'customer', customer, vehicles: vehiclesRes.data })
        }
      }
    } catch {
      setNotFound(true)
      setResult(null)
    } finally {
      setSearching(false)
    }
  }, [])

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => search(query), 600)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [query, search])

  const handleUse = () => {
    if (result) {
      onFound(result)
      setResult(null)
      setQuery('')
    }
  }

  return (
    <Box>
      <TextField
        fullWidth
        size="small"
        label="Поиск по телефону или гос. номеру"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="+7 999 … или А123ВС"
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchRounded sx={{ color: 'text.secondary', fontSize: 18 }} />
            </InputAdornment>
          ),
          endAdornment: searching ? (
            <InputAdornment position="end">
              <CircularProgress size={16} />
            </InputAdornment>
          ) : undefined,
        }}
      />
      <Collapse in={Boolean(result) || notFound}>
        <Box sx={{ mt: 1 }}>
          {notFound && (
            <Typography variant="caption" color="text.secondary">
              Клиент не найден — можно заполнить вручную
            </Typography>
          )}
          {result && (
            <Paper
              variant="outlined"
              sx={{ p: 1.5, borderRadius: 2, bgcolor: alpha('#10B981', 0.06), borderColor: '#10B981' }}
            >
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Box>
                  {result.type === 'customer' && (
                    <>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {result.customer.full_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {result.customer.phone}
                        {result.vehicles.length > 0
                          ? ` · ${result.vehicles.map(v => vehicleLabel(v)).join(', ')}`
                          : ' · нет автомобилей'}
                      </Typography>
                    </>
                  )}
                  {result.type === 'vehicle' && (
                    <>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {vehicleLabel(result.vehicle)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {result.customer.full_name} · {result.customer.phone}
                      </Typography>
                    </>
                  )}
                </Box>
                <Button size="small" variant="contained" onClick={handleUse} sx={{ ml: 1, flexShrink: 0 }}>
                  Использовать
                </Button>
              </Stack>
            </Paper>
          )}
        </Box>
      </Collapse>
    </Box>
  )
}

// ─── Диалог новой записи ──────────────────────────────────────────────────────

function AppointmentDialog({
  open,
  onClose,
  initialForm,
  onSave,
  saving,
}: {
  open: boolean
  onClose: () => void
  initialForm: AppointmentCreate
  onSave: (form: AppointmentCreate) => void
  saving: boolean
}) {
  const [form, setForm] = useState<AppointmentCreate>(initialForm)
  const [customerVehicles, setCustomerVehicles] = useState<Vehicle[]>([])

  useEffect(() => {
    setForm(initialForm)
    setCustomerVehicles([])
  }, [open, initialForm])

  const handleSearchFound = (result: SearchResult) => {
    if (!result) return
    if (result.type === 'customer') {
      setForm((f) => ({
        ...f,
        customer_name: result.customer.full_name,
        customer_phone: result.customer.phone,
        vehicle_id: result.vehicles.length === 1 ? result.vehicles[0].id : f.vehicle_id,
      }))
      setCustomerVehicles(result.vehicles)
    } else if (result.type === 'vehicle') {
      setForm((f) => ({
        ...f,
        customer_name: result.customer.full_name,
        customer_phone: result.customer.phone,
        vehicle_id: result.vehicle.id,
      }))
      setCustomerVehicles([result.vehicle])
    }
  }

  const canSave = Boolean(form.customer_name?.trim() && form.customer_phone?.trim())

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: 2 } }}>
      <DialogTitle>Новая запись</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {/* Поиск клиента */}
          <ClientSearchField onFound={handleSearchFound} />

          <Divider />

          {/* Время */}
          <TextField
            fullWidth
            label="Время"
            type="time"
            value={form.time}
            onChange={(e) => setForm((f) => ({ ...f, time: e.target.value }))}
            InputLabelProps={{ shrink: true }}
            size="small"
          />

          {/* Имя */}
          <TextField
            fullWidth
            label="Имя клиента *"
            value={form.customer_name}
            onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
            size="small"
            InputProps={{
              startAdornment: <InputAdornment position="start"><PersonOutlineRounded sx={{ color: 'text.secondary', fontSize: 18 }} /></InputAdornment>,
            }}
          />

          {/* Телефон */}
          <TextField
            fullWidth
            label="Телефон *"
            value={form.customer_phone}
            onChange={(e) => setForm((f) => ({ ...f, customer_phone: e.target.value }))}
            size="small"
            InputProps={{
              startAdornment: <InputAdornment position="start"><PhoneEnabledRounded sx={{ color: 'text.secondary', fontSize: 18 }} /></InputAdornment>,
            }}
          />

          {/* Автомобиль */}
          {customerVehicles.length > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                Автомобили клиента
              </Typography>
              <Stack direction="row" flexWrap="wrap" gap={0.75}>
                {customerVehicles.map((v) => (
                  <Chip
                    key={v.id}
                    label={vehicleLabel(v) || `Авто #${v.id}`}
                    size="small"
                    variant={form.vehicle_id === v.id ? 'filled' : 'outlined'}
                    color={form.vehicle_id === v.id ? 'primary' : 'default'}
                    icon={<DirectionsCarRounded />}
                    onClick={() => setForm((f) => ({ ...f, vehicle_id: v.id }))}
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Stack>
            </Box>
          )}

          {/* Статус */}
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              Статус
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={0.75}>
              {ALL_STATUSES.map((s) => {
                const c = STATUS_CONFIG[s]
                return (
                  <Chip
                    key={s}
                    label={c.label}
                    size="small"
                    onClick={() => setForm((f) => ({ ...f, status: s }))}
                    sx={{
                      bgcolor: form.status === s ? alpha(c.color, 0.2) : undefined,
                      color: form.status === s ? c.color : 'text.secondary',
                      fontWeight: form.status === s ? 700 : 400,
                      border: '1px solid',
                      borderColor: form.status === s ? c.color : 'divider',
                      cursor: 'pointer',
                    }}
                  />
                )
              })}
            </Stack>
          </Box>

          {/* Комментарий */}
          <TextField
            fullWidth
            label="Комментарий"
            multiline
            rows={2}
            value={form.description || ''}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            size="small"
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Отмена</Button>
        <Button variant="contained" onClick={() => onSave(form)} disabled={saving || !canSave}>
          {saving ? <CircularProgress size={24} /> : 'Записать'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ─── Панель статистики по статусам ────────────────────────────────────────────

const STATS_STATUSES: AppointmentStatus[] = ['scheduled', 'confirmed', 'waiting', 'arrived', 'in_work', 'ready']

function StatusStatsBar({
  appointments,
  filter,
  onFilter,
}: {
  appointments: Appointment[]
  filter: AppointmentStatus | null
  onFilter: (s: AppointmentStatus | null) => void
}) {
  const total = appointments.length

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2 }}>
      <Chip
        label={`Все (${total})`}
        size="small"
        variant={filter === null ? 'filled' : 'outlined'}
        onClick={() => onFilter(null)}
        sx={{ fontWeight: filter === null ? 700 : 400 }}
      />
      {STATS_STATUSES.map((s) => {
        const count = appointments.filter((a) => a.status === s).length
        const c = STATUS_CONFIG[s]
        if (count === 0 && filter !== s) return null
        return (
          <Chip
            key={s}
            label={`${c.label} (${count})`}
            size="small"
            onClick={() => onFilter(filter === s ? null : s)}
            sx={{
              bgcolor: filter === s ? alpha(c.color, 0.2) : undefined,
              color: filter === s ? c.color : count > 0 ? c.color : 'text.disabled',
              fontWeight: filter === s ? 700 : 400,
              border: '1px solid',
              borderColor: filter === s ? c.color : count > 0 ? alpha(c.color, 0.4) : 'divider',
              cursor: 'pointer',
            }}
          />
        )
      })}
    </Stack>
  )
}

// ─── Главная страница ─────────────────────────────────────────────────────────

export default function Appointments() {
  const [selectedDate, setSelectedDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'))
  const [posts, setPosts] = useState<AppointmentPost[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState<AppointmentStatus | null>(null)

  const [openRecordDialog, setOpenRecordDialog] = useState(false)
  const [openPostDialog, setOpenPostDialog] = useState(false)
  const [activeAppointment, setActiveAppointment] = useState<Appointment | null>(null)

  const [recordForm, setRecordForm] = useState<AppointmentCreate>({
    date: selectedDate,
    time: '09:00',
    customer_name: '',
    customer_phone: '',
    description: '',
    status: 'scheduled',
  })
  const [savingRecord, setSavingRecord] = useState(false)

  const [postForm, setPostForm] = useState<AppointmentPostCreate>({
    name: 'Пост 1',
    max_slots: 5,
    sort_order: 0,
  })
  const [postFormSlotTimesInput, setPostFormSlotTimesInput] = useState(DEFAULT_SLOT_HOURS)
  const [editingPostId, setEditingPostId] = useState<number | null>(null)
  const [deletePostConfirm, setDeletePostConfirm] = useState<AppointmentPost | null>(null)
  const [deletingPost, setDeletingPost] = useState(false)
  const [deleteRecordConfirm, setDeleteRecordConfirm] = useState<number | null>(null)
  const [deletingRecord, setDeletingRecord] = useState(false)
  const [savingPost, setSavingPost] = useState(false)

  const [creatingOrder, setCreatingOrder] = useState(false)

  // ─── Загрузка данных ───────────────────────────────────────────────────────

  const fetchPosts = useCallback(async () => {
    try {
      const res = await api.get<AppointmentPost[]>('/appointment-posts/')
      setPosts(res.data)
    } catch {
      setError('Не удалось загрузить посты')
    }
  }, [])

  const fetchAppointments = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get<Appointment[]>('/appointments/', { params: { date: selectedDate } })
      setAppointments(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки записей')
    } finally {
      setLoading(false)
    }
  }, [selectedDate])

  useEffect(() => { fetchPosts() }, [fetchPosts])
  useEffect(() => { fetchAppointments() }, [fetchAppointments])

  // ─── Фильтрация ───────────────────────────────────────────────────────────

  const filteredAppointments = statusFilter
    ? appointments.filter((a) => a.status === statusFilter)
    : appointments

  const appointmentsByPost = (postId: number | null) =>
    filteredAppointments
      .filter((a) => (a.post_id ?? null) === postId)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

  // ─── Статус ───────────────────────────────────────────────────────────────

  const handleStatusChange = async (id: number, status: AppointmentStatus) => {
    // Оптимистичное обновление
    setAppointments((prev) => prev.map((a) => a.id === id ? { ...a, status } : a))
    try {
      await api.put(`/appointments/${id}`, { status })
    } catch {
      setError('Ошибка смены статуса')
      fetchAppointments()
    }
  }

  // ─── Создание заказ-наряда ────────────────────────────────────────────────

  const handleCreateOrder = async (item: Appointment) => {
    if (!item.vehicle_id || item.order_id) return
    setCreatingOrder(true)
    try {
      const payload: OrderCreate = { vehicle_id: item.vehicle_id, order_works: [], order_parts: [] }
      const res = await api.post('/orders/', payload)
      await api.put(`/appointments/${item.id}`, { order_id: res.data.id })
      fetchAppointments()
      window.open(`/orders?open=${res.data.id}`, '_blank')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка создания заказ-наряда')
    } finally {
      setCreatingOrder(false)
    }
  }

  // ─── Управление постами ───────────────────────────────────────────────────

  const handleOpenEditPost = (post: AppointmentPost) => {
    setEditingPostId(post.id)
    setPostForm({ name: post.name, max_slots: post.max_slots, sort_order: post.sort_order })
    setPostFormSlotTimesInput(formatSlotTimesForInput(post.slot_times ?? []))
    setOpenPostDialog(true)
  }

  const handleSavePost = async () => {
    if (!postForm.name.trim()) return
    setSavingPost(true)
    try {
      const slot_times = parseSlotTimes(postFormSlotTimesInput)
      const payload = { ...postForm, slot_times: slot_times.length > 0 ? slot_times : undefined }
      if (editingPostId !== null) {
        await api.put(`/appointment-posts/${editingPostId}`, payload)
      } else {
        await api.post('/appointment-posts/', { ...payload, sort_order: posts.length })
      }
      await fetchPosts()
      setOpenPostDialog(false)
      setEditingPostId(null)
      setPostForm({ name: `Пост ${posts.length + 1}`, max_slots: 5, sort_order: posts.length })
      setPostFormSlotTimesInput(DEFAULT_SLOT_HOURS)
    } catch {
      setError(editingPostId !== null ? 'Ошибка сохранения поста' : 'Ошибка создания поста')
    } finally {
      setSavingPost(false)
    }
  }

  const handleDeletePostConfirm = async () => {
    if (!deletePostConfirm) return
    setDeletingPost(true)
    try {
      await api.delete(`/appointment-posts/${deletePostConfirm.id}`)
      setDeletePostConfirm(null)
      await fetchPosts()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка удаления поста')
    } finally {
      setDeletingPost(false)
    }
  }

  // ─── Управление записями ──────────────────────────────────────────────────

  const handleOpenAddRecord = (postId: number, slotTime?: string) => {
    const post = posts.find((p) => p.id === postId)
    const slotIndex = slotTime && post?.slot_times ? post.slot_times.indexOf(slotTime) : appointmentsByPost(postId).length
    setRecordForm({
      date: selectedDate,
      time: slotTime ?? '09:00',
      customer_name: '',
      customer_phone: '',
      description: '',
      status: 'scheduled',
      post_id: postId,
      sort_order: slotIndex,
    })
    setOpenRecordDialog(true)
  }

  const handleSaveRecord = async (form: AppointmentCreate) => {
    setSavingRecord(true)
    try {
      await api.post('/appointments/', form)
      setOpenRecordDialog(false)
      fetchAppointments()
    } catch {
      setError('Ошибка при сохранении записи')
    } finally {
      setSavingRecord(false)
    }
  }

  const handleDeleteRecord = (id: number) => {
    setDeleteRecordConfirm(id)
  }

  const handleDeleteRecordConfirm = async () => {
    if (deleteRecordConfirm === null) return
    setDeletingRecord(true)
    try {
      await api.delete(`/appointments/${deleteRecordConfirm}`)
      setDeleteRecordConfirm(null)
      fetchAppointments()
    } catch {
      setError('Ошибка при удалении')
    } finally {
      setDeletingRecord(false)
    }
  }

  // ─── Drag & Drop ──────────────────────────────────────────────────────────

  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current
    if (data?.appointment) setActiveAppointment(data.appointment)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveAppointment(null)
    const { active, over } = event
    if (!over?.data.current || !active.data.current?.appointment) return
    const appointment = active.data.current.appointment as Appointment
    const targetPostId = over.data.current.postId as number | undefined
    const targetSlotTime = over.data.current.slotTime as string | undefined
    if (targetPostId === undefined) return
    if (appointment.post_id === targetPostId && targetSlotTime && timeToHHMM(appointment.time) === targetSlotTime) return
    const targetPost = targetPostId === 0 ? null : posts.find((p) => p.id === targetPostId)
    const targetPosts = appointmentsByPost(targetPostId === 0 ? null : targetPostId)
    if (targetPost && !targetSlotTime && targetPosts.length >= targetPost.max_slots) return
    const slotIndex = targetSlotTime && targetPost
      ? targetPost.slot_times?.indexOf(targetSlotTime) ?? 0
      : targetPosts.length
    const displaced = targetSlotTime && targetPost
      ? appointmentsByPost(targetPostId).find((a) => timeToHHMM(a.time) === targetSlotTime)
      : null
    try {
      if (displaced && displaced.id !== appointment.id) {
        const oldTime = timeToHHMM(appointment.time)
        await api.put(`/appointments/${displaced.id}`, {
          post_id: appointment.post_id ?? null,
          time: oldTime.length === 5 ? oldTime : `${oldTime.padStart(2, '0')}:00`,
          sort_order: appointment.sort_order ?? 0,
        })
      }
      await api.put(`/appointments/${appointment.id}`, {
        post_id: targetPostId === 0 ? null : targetPostId,
        time: targetSlotTime ?? undefined,
        sort_order: slotIndex,
      })
      fetchAppointments()
    } catch {
      setError('Не удалось переместить запись')
    }
  }

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  // ─── Рендер ───────────────────────────────────────────────────────────────

  return (
    <Container maxWidth={false} sx={{ maxWidth: 1600 }}>
      {/* Заголовок */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Записи
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddRounded />}
          onClick={() => {
            setEditingPostId(null)
            setPostForm({ name: `Пост ${posts.length + 1}`, max_slots: 5, sort_order: posts.length })
            setPostFormSlotTimesInput(DEFAULT_SLOT_HOURS)
            setOpenPostDialog(true)
          }}
        >
          Создать пост
        </Button>
      </Stack>

      <DatePanel selectedDate={selectedDate} onChange={setSelectedDate} />

      {/* Статистика по статусам */}
      {appointments.length > 0 && (
        <StatusStatsBar
          appointments={appointments}
          filter={statusFilter}
          onFilter={setStatusFilter}
        />
      )}

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading && appointments.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : posts.length === 0 ? (
        <Paper variant="outlined" sx={{ py: 8, textAlign: 'center', borderStyle: 'dashed' }}>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Нет ни одного поста. Создайте пост — появится колонка с кнопкой «Добавить запись».
          </Typography>
          <Button variant="outlined" startIcon={<AddRounded />} onClick={() => setOpenPostDialog(true)}>
            Создать пост
          </Button>
        </Paper>
      ) : (
        <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <Box sx={{ display: 'flex', gap: 2, overflowX: 'auto', pb: 2 }}>
            {posts.map((post, idx) => (
              <PostColumn
                key={post.id}
                post={post}
                appointments={appointmentsByPost(post.id)}
                postColor={getPostColor(post, idx)}
                onAddRecord={() => handleOpenAddRecord(post.id)}
                onAddRecordForSlot={
                  post.slot_times?.length
                    ? (slotTime) => handleOpenAddRecord(post.id, slotTime)
                    : undefined
                }
                onEditPost={handleOpenEditPost}
                onDeletePost={(p) => setDeletePostConfirm(p)}
                onDelete={handleDeleteRecord}
                onStatusChange={handleStatusChange}
                onCreateOrder={handleCreateOrder}
              />
            ))}
          </Box>

          <DragOverlay>
            {activeAppointment ? (
              <Box sx={{ width: 282 }}>
                <AppointmentCard
                  item={activeAppointment}
                  onDelete={() => {}}
                  postColor={(() => {
                    const p = posts.find((x) => x.id === activeAppointment.post_id)
                    return p ? getPostColor(p, posts.indexOf(p)) : '#6366F1'
                  })()}
                  isDragging
                />
              </Box>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      {/* ─── Диалог новой записи ─────────────────────────────────────────── */}
      <AppointmentDialog
        open={openRecordDialog}
        onClose={() => setOpenRecordDialog(false)}
        initialForm={recordForm}
        onSave={handleSaveRecord}
        saving={savingRecord}
      />

      {/* ─── Диалог создания/редактирования поста ────────────────────────── */}
      <Dialog
        open={openPostDialog}
        onClose={() => { setOpenPostDialog(false); setEditingPostId(null) }}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2 } }}
      >
        <DialogTitle>{editingPostId !== null ? 'Редактировать пост' : 'Новый пост'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Название"
              value={postForm.name}
              onChange={(e) => setPostForm((p) => ({ ...p, name: e.target.value }))}
              placeholder="Пост 1"
            />
            <TextField
              fullWidth
              type="number"
              label="Максимум записей на посту"
              value={postForm.max_slots}
              onChange={(e) => setPostForm((p) => ({ ...p, max_slots: Math.max(1, parseInt(e.target.value, 10) || 1) }))}
              inputProps={{ min: 1 }}
            />
            <TextField
              fullWidth
              label="Слоты по времени (часы через запятую)"
              value={postFormSlotTimesInput}
              onChange={(e) => setPostFormSlotTimesInput(e.target.value)}
              placeholder="9, 11, 13, 15, 17"
              helperText="На каждом слоте будет своя ячейка с кнопкой «Добавить запись»"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setOpenPostDialog(false); setEditingPostId(null) }}>Отмена</Button>
          <Button variant="contained" onClick={handleSavePost} disabled={savingPost || !postForm.name.trim()}>
            {savingPost ? <CircularProgress size={24} /> : editingPostId !== null ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ─── Подтверждение удаления поста ────────────────────────────────── */}
      <Dialog open={deletePostConfirm !== null} onClose={() => !deletingPost && setDeletePostConfirm(null)}>
        <DialogTitle>Удалить пост?</DialogTitle>
        <DialogContent>
          {deletePostConfirm && (
            <Stack spacing={1}>
              <Typography>
                Пост «{deletePostConfirm.name}» будет удалён без возможности восстановления.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Если на посту есть активные записи — удаление не выполнится. Сначала перетяните их на другой пост.
              </Typography>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeletePostConfirm(null)} disabled={deletingPost}>Отмена</Button>
          <Button variant="contained" color="error" onClick={handleDeletePostConfirm} disabled={deletingPost}>
            {deletingPost ? <CircularProgress size={24} /> : 'Удалить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ─── Подтверждение удаления записи ───────────────────────────────── */}
      <Dialog
        open={deleteRecordConfirm !== null}
        onClose={() => !deletingRecord && setDeleteRecordConfirm(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2 } }}
      >
        <DialogTitle>Удалить запись?</DialogTitle>
        <DialogContent>
          <Typography>
            Запись будет удалена без возможности восстановления.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteRecordConfirm(null)} disabled={deletingRecord}>
            Отмена
          </Button>
          <Button variant="contained" color="error" onClick={handleDeleteRecordConfirm} disabled={deletingRecord}>
            {deletingRecord ? <CircularProgress size={24} /> : 'Удалить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ─── Индикатор создания наряда ───────────────────────────────────── */}
      {creatingOrder && (
        <Box
          sx={{
            position: 'fixed', bottom: 24, right: 24,
            bgcolor: 'background.paper', borderRadius: 2,
            boxShadow: 4, px: 3, py: 2,
            display: 'flex', alignItems: 'center', gap: 1.5,
          }}
        >
          <CircularProgress size={20} />
          <Typography variant="body2">Создаём заказ-наряд…</Typography>
        </Box>
      )}
    </Container>
  )
}
