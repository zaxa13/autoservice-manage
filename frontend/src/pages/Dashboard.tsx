import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Container, Typography, Box, Grid, Paper, Button, Stack,
  alpha, Chip, CircularProgress, Tooltip, LinearProgress,
  Table, TableBody, TableRow, TableCell, TableHead,
  ToggleButton, ToggleButtonGroup, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, IconButton,
  Popover, Divider,
} from '@mui/material'
import {
  AssignmentRounded, EventAvailableRounded, Inventory2Rounded,
  PeopleAltRounded, AddRounded, ArrowForwardRounded,
  TrendingUpRounded, TrendingDownRounded, TrendingFlatRounded,
  WarningAmberRounded, AccountBalanceWalletRounded,
  EngineeringRounded, DirectionsCarRounded, PersonOffRounded,
  AccessTimeRounded, AttachMoneyRounded, ReceiptLongRounded,
  BuildRounded, EditRounded, CalendarTodayRounded, CheckRounded,
  DateRangeRounded, ChevronLeftRounded, ChevronRightRounded,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { getRoleFromToken } from '../store/authStore'

// ── Types ─────────────────────────────────────────────────────────────────────

type Period = 'day' | 'week' | 'month' | 'quarter' | 'year' | 'custom'

interface StuckOrder {
  id: number
  number: string
  mechanic_name: string | null
  days_in_work: number
}

interface MechanicStat {
  id: number
  name: string
  orders_count: number
  revenue: number
  avg_check: number
  vs_team_pct: number | null
}

interface ChartDay {
  label: string
  date: string
  current: number
  previous: number
  is_today: boolean
  is_future?: boolean
}

interface PipelineDay {
  date: string
  day_name: string
  day_label: string
  appointments_count: number
  load_pct: number | null
  is_today: boolean
}

interface DashboardStats {
  period: Period
  period_label: string
  revenue: {
    value: number
    prev_value: number
    change_pct: number | null
    plan: number | null
    plan_pct: number | null
  }
  avg_check: { value: number; prev_value: number; change_pct: number | null }
  orders_count: { value: number; prev_value: number; change_pct: number | null }
  wip_amount: number
  post_load_today_pct: number | null
  post_load_tomorrow_pct: number | null
  pipeline_7d: PipelineDay[]
  revenue_chart: ChartDay[]
  mechanics_stats: MechanicStat[]
  alerts: {
    unpaid_orders_count: number
    unpaid_orders_sum: number
    stuck_orders: StuckOrder[]
    orders_without_mechanic_count: number
    no_shows_today: number
    no_shows_pct: number
  }
  nav_ref: string
  can_go_next: boolean
}

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtMoney(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} млн ₽`
  if (v >= 1_000) return `${Math.round(v / 1_000)} тыс ₽`
  return `${Math.round(v)} ₽`
}

function fmtMoneyFull(v: number): string {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0,
  }).format(v)
}

// ── TrendBadge ────────────────────────────────────────────────────────────────

function TrendBadge({ pct, invertColor }: { pct: number | null; invertColor?: boolean }) {
  if (pct === null) return (
    <Typography variant="caption" color="text.disabled" sx={{ fontSize: 11 }}>нет данных</Typography>
  )
  const up = pct > 0
  const flat = Math.abs(pct) < 0.5
  let color = 'text.secondary'
  if (!flat) color = (up !== (invertColor ?? false)) ? 'success.main' : 'error.main'
  const Icon = flat ? TrendingFlatRounded : (up ? TrendingUpRounded : TrendingDownRounded)
  return (
    <Stack direction="row" alignItems="center" spacing={0.3} sx={{ color }}>
      <Icon sx={{ fontSize: 13 }} />
      <Typography variant="caption" sx={{ fontWeight: 700, fontSize: 11 }}>
        {up && !flat ? '+' : ''}{pct}%
      </Typography>
    </Stack>
  )
}

// ── KpiCard ────────────────────────────────────────────────────────────────────

function KpiCard({
  title, value, subtitle, trend, icon, color, loading, invertColor, extra,
}: {
  title: string
  value: string
  subtitle: string
  trend: number | null
  icon: React.ReactNode
  color: string
  loading: boolean
  invertColor?: boolean
  extra?: React.ReactNode
}) {
  return (
    <Paper sx={{ p: 2.5, height: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
        <Box sx={{ p: 1.2, borderRadius: '10px', bgcolor: alpha(color, 0.12), color, display: 'flex' }}>
          {icon}
        </Box>
        <TrendBadge pct={trend} invertColor={invertColor} />
      </Stack>
      {loading ? (
        <CircularProgress size={22} sx={{ mt: 0.5 }} />
      ) : (
        <Typography variant="h5" sx={{ fontWeight: 800, lineHeight: 1.1 }}>{value}</Typography>
      )}
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.3, fontSize: 11 }}>
        {subtitle}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{
        display: 'block', mt: 1, textTransform: 'uppercase', fontWeight: 700, fontSize: 10, letterSpacing: '0.05em',
      }}>
        {title}
      </Typography>
      {extra}
    </Paper>
  )
}

// ── RevenueCard (с планом) ────────────────────────────────────────────────────

function RevenueCard({
  revenue, periodLabel, loading, isAdmin, onEditPlan,
}: {
  revenue: DashboardStats['revenue']
  periodLabel: string
  loading: boolean
  isAdmin: boolean
  onEditPlan: () => void
}) {
  const color = '#10B981'
  const planPct = revenue.plan_pct

  return (
    <Paper sx={{ p: 2.5, height: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
        <Box sx={{ p: 1.2, borderRadius: '10px', bgcolor: alpha(color, 0.12), color, display: 'flex' }}>
          <AttachMoneyRounded />
        </Box>
        <Stack direction="row" alignItems="center" spacing={1}>
          <TrendBadge pct={revenue.change_pct} />
          {isAdmin && (
            <Tooltip title="Установить план месяца">
              <IconButton size="small" onClick={onEditPlan} sx={{ p: 0.4, color: 'text.disabled', '&:hover': { color: 'primary.main' } }}>
                <EditRounded sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </Stack>

      {loading ? (
        <CircularProgress size={22} sx={{ mt: 0.5 }} />
      ) : (
        <Typography variant="h5" sx={{ fontWeight: 800, lineHeight: 1.1 }}>
          {fmtMoney(revenue.value)}
        </Typography>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.3, fontSize: 11 }}>
        {revenue.prev_value > 0
          ? `пред. период: ${fmtMoney(revenue.prev_value)}`
          : 'нет данных за пред. период'}
      </Typography>

      {/* Plan progress */}
      {revenue.plan && !loading && (
        <Box sx={{ mt: 1.5 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="caption" sx={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', color: 'text.secondary' }}>
              План: {fmtMoney(revenue.plan)}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: 11, fontWeight: 800, color: planPct && planPct >= 100 ? 'success.main' : color }}>
              {planPct}%
            </Typography>
          </Stack>
          <LinearProgress
            variant="determinate"
            value={Math.min(planPct ?? 0, 100)}
            sx={{
              height: 5, borderRadius: 3,
              bgcolor: alpha(color, 0.15),
              '& .MuiLinearProgress-bar': {
                bgcolor: planPct && planPct >= 100 ? 'success.main' : color,
                borderRadius: 3,
              },
            }}
          />
        </Box>
      )}

      {!revenue.plan && !loading && (
        <Box sx={{ mt: 1.5 }}>
          <LinearProgress
            variant="determinate"
            value={0}
            sx={{
              height: 5, borderRadius: 3,
              bgcolor: alpha(color, 0.10),
              '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 3 },
            }}
          />
          {isAdmin && (
            <Typography
              variant="caption"
              onClick={onEditPlan}
              sx={{ fontSize: 10, color: 'text.disabled', cursor: 'pointer', mt: 0.3, display: 'block', '&:hover': { color: 'primary.main' } }}
            >
              + Задать план на месяц
            </Typography>
          )}
        </Box>
      )}

      <Typography variant="caption" color="text.secondary" sx={{
        display: 'block', mt: 1, textTransform: 'uppercase', fontWeight: 700, fontSize: 10, letterSpacing: '0.05em',
      }}>
        Выручка · {periodLabel}
      </Typography>
    </Paper>
  )
}

// ── LoadCard ───────────────────────────────────────────────────────────────────

function LoadCard({ title, pct, subtitle, loading }: {
  title: string; pct: number | null; subtitle: string; loading: boolean
}) {
  const color = pct === null ? '#94A3B8' : pct >= 70 ? '#10B981' : pct >= 45 ? '#F59E0B' : '#EF4444'
  const label = pct === null ? null : pct >= 70 ? 'Хорошо' : pct >= 45 ? 'Средне' : 'Мало'
  return (
    <Paper sx={{ p: 2.5, height: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1.5 }}>
        <Box sx={{ p: 1.2, borderRadius: '10px', bgcolor: alpha(color, 0.12), color, display: 'flex' }}>
          <DirectionsCarRounded />
        </Box>
        {label && (
          <Chip label={label} size="small" sx={{ bgcolor: alpha(color, 0.12), color, fontSize: 10, height: 20, fontWeight: 700 }} />
        )}
      </Stack>
      {loading ? (
        <CircularProgress size={22} sx={{ mt: 0.5 }} />
      ) : (
        <>
          <Typography variant="h5" sx={{ fontWeight: 800, color, lineHeight: 1.1 }}>
            {pct === null ? '—' : `${pct}%`}
          </Typography>
          {pct !== null && (
            <LinearProgress
              variant="determinate"
              value={pct}
              sx={{
                mt: 1, height: 4, borderRadius: 2,
                bgcolor: alpha(color, 0.15),
                '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 2 },
              }}
            />
          )}
        </>
      )}
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, fontSize: 11 }}>
        {subtitle}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{
        display: 'block', mt: 0.5, textTransform: 'uppercase', fontWeight: 700, fontSize: 10, letterSpacing: '0.05em',
      }}>
        {title}
      </Typography>
    </Paper>
  )
}

// ── AlertsBlock ───────────────────────────────────────────────────────────────

function AlertsBlock({ alerts, onNavigate }: {
  alerts: DashboardStats['alerts']
  onNavigate: (p: string) => void
}) {
  const hasAlerts =
    alerts.unpaid_orders_count > 0 ||
    alerts.stuck_orders.length > 0 ||
    alerts.orders_without_mechanic_count > 0 ||
    alerts.no_shows_today > 0

  if (!hasAlerts) return null

  return (
    <Paper sx={{
      p: 2.5, mb: 3,
      border: '1px solid', borderColor: alpha('#F59E0B', 0.4),
      bgcolor: alpha('#F59E0B', 0.02),
    }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <WarningAmberRounded sx={{ color: 'warning.main', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Требует внимания</Typography>
      </Stack>
      <Grid container spacing={1.5}>

        {alerts.unpaid_orders_count > 0 && (
          <Grid item xs={12} sm={6} md={3}>
            <AlertCard
              color="#EF4444"
              icon={<AccountBalanceWalletRounded sx={{ fontSize: 15 }} />}
              label="Не оплачено"
              onClick={() => onNavigate('/orders')}
            >
              <Typography variant="h6" sx={{ fontWeight: 800, color: '#EF4444', lineHeight: 1.2 }}>
                {alerts.unpaid_orders_count} заказ{alerts.unpaid_orders_count > 1 ? 'а' : ''}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {fmtMoneyFull(alerts.unpaid_orders_sum)} к получению
              </Typography>
            </AlertCard>
          </Grid>
        )}

        {alerts.stuck_orders.length > 0 && (
          <Grid item xs={12} sm={6} md={4}>
            <AlertCard
              color="#F59E0B"
              icon={<AccessTimeRounded sx={{ fontSize: 15 }} />}
              label="Зависли в работе"
              onClick={() => onNavigate('/orders')}
            >
              {alerts.stuck_orders.slice(0, 3).map(o => (
                <Box key={o.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600 }}>{o.number}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {o.mechanic_name ? o.mechanic_name.split(' ')[0] : '—'} · {o.days_in_work}д
                  </Typography>
                </Box>
              ))}
              {alerts.stuck_orders.length > 3 && (
                <Typography variant="caption" color="text.secondary">+ ещё {alerts.stuck_orders.length - 3}</Typography>
              )}
            </AlertCard>
          </Grid>
        )}

        {alerts.orders_without_mechanic_count > 0 && (
          <Grid item xs={12} sm={6} md={3}>
            <AlertCard
              color="#6366F1"
              icon={<EngineeringRounded sx={{ fontSize: 15 }} />}
              label="Без механика"
              onClick={() => onNavigate('/orders')}
            >
              <Typography variant="h6" sx={{ fontWeight: 800, color: '#6366F1', lineHeight: 1.2 }}>
                {alerts.orders_without_mechanic_count} заказ{alerts.orders_without_mechanic_count > 1 ? 'а' : ''}
              </Typography>
              <Typography variant="caption" color="text.secondary">Назначьте исполнителя</Typography>
            </AlertCard>
          </Grid>
        )}

        {alerts.no_shows_today > 0 && (
          <Grid item xs={12} sm={6} md={2}>
            <AlertCard
              color="#94A3B8"
              icon={<PersonOffRounded sx={{ fontSize: 15 }} />}
              label="Не явились"
              onClick={() => onNavigate('/appointments')}
            >
              <Typography variant="h6" sx={{ fontWeight: 800, color: '#64748B', lineHeight: 1.2 }}>
                {alerts.no_shows_today}
                {alerts.no_shows_pct > 0 && (
                  <Typography component="span" variant="caption" sx={{ ml: 0.5, color: '#94A3B8', fontWeight: 400 }}>
                    ({alerts.no_shows_pct}%)
                  </Typography>
                )}
              </Typography>
              <Typography variant="caption" color="text.secondary">от записей сегодня</Typography>
            </AlertCard>
          </Grid>
        )}
      </Grid>
    </Paper>
  )
}

function AlertCard({ color, icon, label, onClick, children }: {
  color: string; icon: React.ReactNode; label: string
  onClick: () => void; children: React.ReactNode
}) {
  return (
    <Box
      onClick={onClick}
      sx={{
        p: 1.5, borderRadius: '10px', height: '100%',
        bgcolor: alpha(color, 0.06),
        border: '1px solid', borderColor: alpha(color, 0.2),
        cursor: 'pointer',
        '&:hover': { bgcolor: alpha(color, 0.10) },
      }}
    >
      <Stack direction="row" alignItems="center" spacing={0.75} sx={{ mb: 0.75 }}>
        <Box sx={{ color }}>{icon}</Box>
        <Typography variant="caption" sx={{ color, fontWeight: 700, textTransform: 'uppercase', fontSize: 10 }}>
          {label}
        </Typography>
      </Stack>
      {children}
    </Box>
  )
}

// ── Pipeline ───────────────────────────────────────────────────────────────────

function PipelineBlock({ data }: { data: PipelineDay[] }) {
  const maxAppts = Math.max(...data.map(d => d.appointments_count), 1)
  const BAR_H = 52

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: '6px', alignItems: 'flex-end', height: BAR_H + 44 }}>
        {data.map((d) => {
          const barH = Math.max((d.appointments_count / maxAppts) * BAR_H, d.appointments_count > 0 ? 4 : 0)
          const loadColor = d.load_pct === null ? '#CBD5E1'
            : d.load_pct >= 70 ? '#10B981'
              : d.load_pct >= 45 ? '#F59E0B'
                : '#EF4444'

          return (
            <Tooltip
              key={d.date}
              title={
                <Box sx={{ fontSize: 12 }}>
                  <Box sx={{ fontWeight: 700 }}>{d.day_label}</Box>
                  <Box>Записей: {d.appointments_count}</Box>
                  <Box sx={{ opacity: 0.8 }}>
                    Загрузка: {d.load_pct !== null ? `${d.load_pct}%` : '—'}
                  </Box>
                </Box>
              }
              arrow
            >
              <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'default' }}>
                {/* Load badge */}
                <Box sx={{
                  fontSize: 9, fontWeight: 700, color: loadColor,
                  mb: 0.5, lineHeight: 1,
                }}>
                  {d.load_pct !== null ? `${d.load_pct}%` : '—'}
                </Box>

                {/* Bar */}
                <Box sx={{ height: BAR_H, display: 'flex', alignItems: 'flex-end' }}>
                  <Box sx={{
                    width: '100%', minWidth: 16, height: barH || 2,
                    bgcolor: d.is_today ? loadColor : alpha(loadColor, 0.5),
                    borderRadius: '3px 3px 0 0',
                    border: d.is_today ? `1.5px solid ${loadColor}` : 'none',
                    transition: 'height 0.3s ease',
                  }} />
                </Box>

                {/* Appointments count */}
                <Typography variant="caption" sx={{
                  fontSize: 10, mt: 0.3,
                  fontWeight: d.is_today ? 800 : 400,
                  color: d.is_today ? 'text.primary' : 'text.secondary',
                }}>
                  {d.appointments_count || '—'}
                </Typography>

                {/* Day name */}
                <Typography variant="caption" sx={{
                  fontSize: 9, mt: 0.2,
                  color: d.is_today ? 'primary.main' : 'text.disabled',
                  fontWeight: d.is_today ? 700 : 400,
                }}>
                  {d.day_name}
                </Typography>

                {d.is_today && (
                  <Box sx={{ width: 4, height: 4, borderRadius: '50%', bgcolor: 'primary.main', mt: 0.3 }} />
                )}
              </Box>
            </Tooltip>
          )
        })}
      </Box>

      {/* Legend */}
      <Stack direction="row" spacing={2} sx={{ mt: 1.5, flexWrap: 'wrap', gap: 1 }}>
        {[
          { color: '#10B981', label: '≥70% — норма' },
          { color: '#F59E0B', label: '45–69% — средне' },
          { color: '#EF4444', label: '<45% — мало' },
        ].map(l => (
          <Stack key={l.label} direction="row" alignItems="center" spacing={0.5}>
            <Box sx={{ width: 8, height: 8, borderRadius: 1, bgcolor: l.color }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>{l.label}</Typography>
          </Stack>
        ))}
      </Stack>
    </Box>
  )
}

// ── RevenueChart ───────────────────────────────────────────────────────────────

function RevenueChart({ data, period }: { data: ChartDay[]; period: Period }) {
  if (!data.length) return null
  const maxVal = Math.max(...data.flatMap(d => [d.current, d.previous]), 1)
  const CHART_H = 90

  const prevLabel = period === 'day' ? 'Вчера'
    : period === 'week' ? 'Прошлая неделя'
      : period === 'month' ? 'Прошлый месяц'
        : period === 'year' ? 'Прошлый год'
          : 'Прошлый квартал'

  return (
    <Box>
      <Stack direction="row" spacing={2} sx={{ mb: 1.5 }}>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: '2px', bgcolor: 'primary.main' }} />
          <Typography variant="caption" color="text.secondary">Текущий период</Typography>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Box sx={{ width: 10, height: 10, borderRadius: '2px', bgcolor: 'action.disabledBackground' }} />
          <Typography variant="caption" color="text.secondary">{prevLabel}</Typography>
        </Stack>
      </Stack>

      <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: CHART_H + 24, overflowX: 'auto' }}>
        {data.map((d) => {
          const curH = Math.max((d.current / maxVal) * CHART_H, d.current > 0 ? 3 : 0)
          const prevH = Math.max((d.previous / maxVal) * CHART_H, d.previous > 0 ? 3 : 0)
          return (
            <Tooltip
              key={d.date}
              title={
                <Box sx={{ fontSize: 12 }}>
                  <Box sx={{ fontWeight: 700 }}>{d.label}</Box>
                  <Box>Факт: {fmtMoneyFull(d.current)}</Box>
                  <Box sx={{ opacity: 0.75 }}>{prevLabel}: {fmtMoneyFull(d.previous)}</Box>
                </Box>
              }
              arrow
            >
              <Box sx={{ flex: '0 0 auto', minWidth: 14, display: 'flex', flexDirection: 'column', alignItems: 'center', cursor: 'default' }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: CHART_H }}>
                  <Box sx={{
                    width: 7, height: prevH || 2,
                    bgcolor: 'action.disabledBackground',
                    borderRadius: '2px 2px 0 0',
                  }} />
                  <Box sx={{
                    width: 7, height: curH || 2,
                    bgcolor: d.is_future ? alpha('#6366F1', 0.4) : d.is_today ? 'success.main' : 'primary.main',
                    borderRadius: '2px 2px 0 0',
                    opacity: d.is_future ? 0.5 : d.is_today ? 1 : 0.8,
                    border: d.is_future ? '1px dashed' : 'none',
                    borderColor: 'primary.main',
                  }} />
                </Box>
                {data.length <= 14 && (
                  <Typography variant="caption" sx={{
                    fontSize: 8, mt: 0.5,
                    color: d.is_today ? 'primary.main' : 'text.disabled',
                    fontWeight: d.is_today ? 700 : 400,
                    whiteSpace: 'nowrap',
                  }}>
                    {d.label.split(' ')[0]}
                  </Typography>
                )}
              </Box>
            </Tooltip>
          )
        })}
      </Box>

      <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider', display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 600 }}>
            Период (факт)
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.1 }}>
            {fmtMoneyFull(data.reduce((s, d) => s + d.current, 0))}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 600 }}>
            {prevLabel}
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.1, color: 'text.secondary' }}>
            {fmtMoneyFull(data.reduce((s, d) => s + d.previous, 0))}
          </Typography>
        </Box>
      </Box>
    </Box>
  )
}

// ── MechanicsTable ─────────────────────────────────────────────────────────────

function MechanicsTable({ mechanics }: { mechanics: MechanicStat[] }) {
  if (!mechanics.length) return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 120 }}>
      <Typography color="text.secondary" variant="body2">Нет данных за период</Typography>
    </Box>
  )
  const maxRev = mechanics[0]?.revenue || 1

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell sx={{ fontSize: 10, fontWeight: 700, color: 'text.secondary', py: 0.5, pl: 0 }}>Мастер</TableCell>
          <TableCell align="center" sx={{ fontSize: 10, fontWeight: 700, color: 'text.secondary', py: 0.5 }}>Нарядов</TableCell>
          <TableCell align="right" sx={{ fontSize: 10, fontWeight: 700, color: 'text.secondary', py: 0.5 }}>Ср. чек</TableCell>
          <TableCell align="right" sx={{ fontSize: 10, fontWeight: 700, color: 'text.secondary', py: 0.5, pr: 0 }}>Выработка</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {mechanics.slice(0, 8).map((m, idx) => {
          const barPct = (m.revenue / maxRev) * 100
          const vsTeam = m.vs_team_pct
          const vsColor = vsTeam === null ? 'text.secondary'
            : vsTeam >= 5 ? '#10B981' : vsTeam <= -5 ? '#EF4444' : 'text.secondary'

          return (
            <TableRow key={m.id} sx={{ '&:last-child td': { border: 0 } }}>
              <TableCell sx={{ py: 0.8, pl: 0, pr: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: idx === 0 ? 700 : 400, fontSize: 13 }}>
                  {m.name.split(' ').slice(0, 2).join(' ')}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={barPct}
                  sx={{
                    height: 2, borderRadius: 1, mt: 0.3,
                    bgcolor: 'action.disabledBackground',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: idx === 0 ? 'success.main' : 'primary.main',
                      opacity: idx === 0 ? 1 : 0.6,
                      borderRadius: 1,
                    },
                  }}
                />
              </TableCell>
              <TableCell align="center" sx={{ py: 0.8 }}>
                <Chip label={m.orders_count} size="small" sx={{ height: 18, fontSize: 11, fontWeight: 700 }} />
              </TableCell>
              <TableCell align="right" sx={{ py: 0.8 }}>
                <Stack alignItems="flex-end">
                  <Typography variant="body2" sx={{ fontSize: 12 }}>{fmtMoney(m.avg_check)}</Typography>
                  {vsTeam !== null && (
                    <Typography variant="caption" sx={{ fontSize: 10, color: vsColor, fontWeight: 700 }}>
                      {vsTeam > 0 ? '+' : ''}{vsTeam}% vs команда
                    </Typography>
                  )}
                </Stack>
              </TableCell>
              <TableCell align="right" sx={{ py: 0.8, pr: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 700, fontSize: 13 }}>
                  {fmtMoney(m.revenue)}
                </Typography>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

// ── Plan Edit Dialog ───────────────────────────────────────────────────────────

function PlanDialog({
  open, onClose, onSave, currentPlan, year, month,
}: {
  open: boolean
  onClose: () => void
  onSave: (amount: number) => Promise<void>
  currentPlan: number | null
  year: number
  month: number
}) {
  const monthNames = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
  ]
  const [value, setValue] = useState(currentPlan ? String(currentPlan) : '')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) setValue(currentPlan ? String(Math.round(currentPlan)) : '')
  }, [open, currentPlan])

  const handleSave = async () => {
    const amount = parseFloat(value.replace(/\s/g, '').replace(',', '.'))
    if (!amount || amount <= 0) return
    setSaving(true)
    try {
      await onSave(amount)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ fontWeight: 700 }}>
        План выручки — {monthNames[month - 1]} {year}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Укажите целевую выручку за месяц. На дашборде будет отображаться прогресс выполнения плана.
        </Typography>
        <TextField
          label="Сумма плана, ₽"
          fullWidth
          autoFocus
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
          placeholder="500 000"
          InputProps={{ sx: { fontWeight: 700, fontSize: 18 } }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} color="inherit">Отмена</Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={saving || !value}
          startIcon={saving ? <CircularProgress size={14} color="inherit" /> : <CheckRounded />}
        >
          Сохранить
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

const PERIOD_LABELS: Record<Period, string> = {
  day: 'День',
  week: 'Неделя',
  month: 'Месяц',
  quarter: 'Квартал',
  year: 'Год',
  custom: 'Период',
}

// ── Custom Date Range Picker ──────────────────────────────────────────────────

function CustomRangePicker({
  anchorEl, onClose, onApply,
}: {
  anchorEl: HTMLElement | null
  onClose: () => void
  onApply: (from: string, to: string) => void
}) {
  const today = new Date().toISOString().split('T')[0]
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [error, setError] = useState('')

  const handleApply = () => {
    if (!from || !to) { setError('Укажите обе даты'); return }
    if (from > to) { setError('Начало не может быть позже конца'); return }
    const days = (new Date(to).getTime() - new Date(from).getTime()) / 86400000
    if (days > 366) { setError('Период не может превышать 366 дней'); return }
    onApply(from, to)
    onClose()
  }

  return (
    <Popover
      open={Boolean(anchorEl)}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      PaperProps={{ sx: { p: 2.5, width: 300, mt: 0.5 } }}
    >
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 2 }}>
        Произвольный период
      </Typography>
      <Stack spacing={1.5}>
        <TextField
          label="Начало"
          type="date"
          size="small"
          fullWidth
          value={from}
          onChange={e => { setFrom(e.target.value); setError('') }}
          inputProps={{ max: to || today }}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Конец"
          type="date"
          size="small"
          fullWidth
          value={to}
          onChange={e => { setTo(e.target.value); setError('') }}
          inputProps={{ min: from, max: today }}
          InputLabelProps={{ shrink: true }}
        />
        {error && (
          <Typography variant="caption" color="error">{error}</Typography>
        )}
      </Stack>
      <Divider sx={{ my: 2 }} />
      <Stack direction="row" spacing={1} justifyContent="flex-end">
        <Button size="small" onClick={onClose} color="inherit">Отмена</Button>
        <Button size="small" variant="contained" onClick={handleApply} startIcon={<CheckRounded />}>
          Применить
        </Button>
      </Stack>
    </Popover>
  )
}

// ── MonthGridPicker ───────────────────────────────────────────────────────────

const MONTH_NAMES = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']

function MonthGridPicker({
  anchorEl, onClose, onApply, initialYear,
}: {
  anchorEl: HTMLElement | null
  onClose: () => void
  onApply: (dateStr: string) => void
  initialYear: number
}) {
  const [pickerYear, setPickerYear] = useState(initialYear)
  const today = new Date()

  return (
    <Popover
      open={Boolean(anchorEl)}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      transformOrigin={{ vertical: 'top', horizontal: 'center' }}
      PaperProps={{ sx: { p: 2, width: 260, mt: 0.5 } }}
    >
      {/* Year navigation */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.5 }}>
        <IconButton size="small" onClick={() => setPickerYear(y => y - 1)}>
          <ChevronLeftRounded />
        </IconButton>
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{pickerYear}</Typography>
        <IconButton
          size="small"
          onClick={() => setPickerYear(y => y + 1)}
          disabled={pickerYear >= today.getFullYear()}
        >
          <ChevronRightRounded />
        </IconButton>
      </Stack>

      {/* Month grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0.75 }}>
        {MONTH_NAMES.map((name, idx) => {
          const isFuture = pickerYear > today.getFullYear() ||
            (pickerYear === today.getFullYear() && idx > today.getMonth())
          return (
            <Button
              key={name}
              size="small"
              disabled={isFuture}
              onClick={() => {
                onApply(`${pickerYear}-${String(idx + 1).padStart(2, '0')}-01`)
                onClose()
              }}
              sx={{
                fontSize: 12, fontWeight: 600, py: 0.75,
                bgcolor: 'action.hover',
                '&:hover': { bgcolor: 'primary.main', color: 'white' },
              }}
            >
              {name}
            </Button>
          )
        })}
      </Box>
    </Popover>
  )
}

// ── PeriodNav ─────────────────────────────────────────────────────────────────

function PeriodNav({
  period, label, canGoNext, onPrev, onNext, onLabelClick,
}: {
  period: Period
  label: string
  canGoNext: boolean
  onPrev: () => void
  onNext: () => void
  onLabelClick: (el: HTMLElement) => void
}) {
  const clickable = period === 'month' || period === 'year'
  const btnRef = useRef<HTMLSpanElement>(null)

  return (
    <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 2 }}>
      <IconButton size="small" onClick={onPrev} sx={{ color: 'text.secondary' }}>
        <ChevronLeftRounded />
      </IconButton>
      <Typography
        ref={btnRef}
        variant="body2"
        onClick={clickable ? () => btnRef.current && onLabelClick(btnRef.current) : undefined}
        sx={{
          fontWeight: 600,
          minWidth: 140,
          textAlign: 'center',
          cursor: clickable ? 'pointer' : 'default',
          color: clickable ? 'primary.main' : 'text.primary',
          borderRadius: 1,
          px: 1, py: 0.25,
          '&:hover': clickable ? { bgcolor: 'action.hover' } : undefined,
        }}
      >
        {label}
      </Typography>
      <IconButton size="small" onClick={onNext} disabled={!canGoNext} sx={{ color: 'text.secondary' }}>
        <ChevronRightRounded />
      </IconButton>
    </Stack>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('month')
  const [customFrom, setCustomFrom] = useState<string | null>(null)
  const [customTo, setCustomTo] = useState<string | null>(null)
  const [refDate, setRefDate] = useState<string | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [planDialogOpen, setPlanDialogOpen] = useState(false)
  const [rangePickerAnchor, setRangePickerAnchor] = useState<HTMLElement | null>(null)
  const [monthPickerAnchor, setMonthPickerAnchor] = useState<HTMLElement | null>(null)
  const isAdmin = getRoleFromToken() === 'admin'
  const customBtnRef = useRef<HTMLButtonElement>(null)

  const load = useCallback((p: Period, from?: string | null, to?: string | null, ref?: string | null) => {
    setLoading(true)
    const params: Record<string, string> = { period: p }
    if (p === 'custom' && from && to) {
      params.date_from = from
      params.date_to = to
    } else if (p !== 'custom' && ref) {
      params.ref_date = ref
    }
    api.get('/dashboard/stats', { params })
      .then(r => { setStats(r.data); setError('') })
      .catch(() => setError('Не удалось загрузить данные дашборда'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (period === 'custom' && (!customFrom || !customTo)) return
    load(period, customFrom, customTo, refDate)
  }, [period, customFrom, customTo, refDate, load])

  const handlePeriodChange = (_: React.MouseEvent, val: Period | null) => {
    if (!val) return
    if (val === 'custom') {
      setRangePickerAnchor(customBtnRef.current)
      return
    }
    setRefDate(null)
    setPeriod(val)
  }

  const navigatePeriod = (dir: -1 | 1) => {
    if (!stats) return
    const base = new Date((stats.nav_ref || new Date().toISOString().split('T')[0]) + 'T00:00:00')
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    let newDate = new Date(base)
    if (period === 'day') {
      newDate.setDate(newDate.getDate() + dir)
    } else if (period === 'week') {
      newDate.setDate(newDate.getDate() + dir * 7)
    } else if (period === 'month') {
      newDate.setMonth(newDate.getMonth() + dir)
      newDate.setDate(1)
    } else if (period === 'quarter') {
      newDate.setMonth(newDate.getMonth() + dir * 3)
      newDate.setDate(1)
    } else if (period === 'year') {
      newDate = new Date(base.getFullYear() + dir, 0, 1)
    }

    if (newDate > today) newDate = today
    setRefDate(newDate.toISOString().split('T')[0])
  }

  const handleCustomApply = (from: string, to: string) => {
    setCustomFrom(from)
    setCustomTo(to)
    setPeriod('custom')
  }

  // Определяем год/месяц для плана исходя из просматриваемого периода
  const getPlanYearMonth = (): { year: number; month: number } => {
    // custom: берём месяц начала диапазона
    if (period === 'custom' && customFrom) {
      const d = new Date(customFrom + 'T00:00:00')
      return { year: d.getFullYear(), month: d.getMonth() + 1 }
    }
    // year: берём год из refDate или сегодня, месяц = текущий
    if (period === 'year') {
      const base = refDate ? new Date(refDate + 'T00:00:00') : new Date()
      const now = new Date()
      return { year: base.getFullYear(), month: now.getMonth() + 1 }
    }
    // month с refDate: берём год/месяц из refDate
    if (period === 'month' && refDate) {
      const d = new Date(refDate + 'T00:00:00')
      return { year: d.getFullYear(), month: d.getMonth() + 1 }
    }
    // month: берём месяц из period_label через stats.revenue, или из today
    if (period === 'month' && s?.period_label) {
      // period_label для month = "Март 2026" — парсим год из него
      const parts = s.period_label.split(' ')
      const yr = parseInt(parts[parts.length - 1])
      if (!isNaN(yr)) {
        const now = new Date()
        return { year: yr, month: now.getMonth() + 1 }
      }
    }
    // day / week / quarter: используем текущий месяц
    const now = new Date()
    return { year: now.getFullYear(), month: now.getMonth() + 1 }
  }

  const handleSavePlan = async (amount: number) => {
    const { year, month } = getPlanYearMonth()
    await api.put('/settings/revenue-plan', { year, month, amount })
    load(period, customFrom, customTo, refDate)
  }

  const s = stats

  const mainActions = [
    { title: 'Календарь записей', desc: 'Планирование визитов клиентов', icon: <EventAvailableRounded sx={{ fontSize: 28 }} />, path: '/appointments', color: '#4F46E5' },
    { title: 'Заказ-наряды', desc: 'Управление активными работами', icon: <AssignmentRounded sx={{ fontSize: 28 }} />, path: '/orders', color: '#10B981' },
    { title: 'Склад', desc: 'Запчасти и расходные материалы', icon: <Inventory2Rounded sx={{ fontSize: 28 }} />, path: '/warehouse', color: '#F59E0B' },
    { title: 'Сотрудники', desc: 'Штат и эффективность мастеров', icon: <PeopleAltRounded sx={{ fontSize: 28 }} />, path: '/employees', color: '#6366F1' },
  ]

  return (
    <Container maxWidth="xl">
      {/* ── Header ────────────────────────────────────────────── */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Панель управления</Typography>
          <Typography variant="body1" color="text.secondary">
            {new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}
            {s && ` · ${s.period_label}`}
          </Typography>
        </Box>
        <Stack direction="row" spacing={2} alignItems="center">
          {/* Period selector */}
          <ToggleButtonGroup
            value={period}
            exclusive
            onChange={handlePeriodChange}
            size="small"
            sx={{
              bgcolor: 'background.paper',
              '& .MuiToggleButton-root': {
                px: 1.75, py: 0.6, fontSize: 12, fontWeight: 600, textTransform: 'none', border: '1px solid',
                borderColor: 'divider',
                '&.Mui-selected': { bgcolor: 'primary.main', color: 'white', borderColor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } },
              },
            }}
          >
            {(['day', 'week', 'month', 'quarter', 'year'] as Period[]).map(p => (
              <ToggleButton key={p} value={p}>{PERIOD_LABELS[p]}</ToggleButton>
            ))}
            <ToggleButton
              value="custom"
              ref={customBtnRef}
              onClick={() => setRangePickerAnchor(customBtnRef.current)}
            >
              <DateRangeRounded sx={{ fontSize: 15, mr: period === 'custom' && customFrom ? 0.5 : 0 }} />
              {period === 'custom' && customFrom && customTo
                ? `${customFrom.slice(5)} – ${customTo.slice(5)}`
                : null}
            </ToggleButton>
          </ToggleButtonGroup>

          <CustomRangePicker
            anchorEl={rangePickerAnchor}
            onClose={() => setRangePickerAnchor(null)}
            onApply={handleCustomApply}
          />

          <Button
            variant="contained"
            startIcon={<AddRounded />}
            onClick={() => navigate('/orders')}
            sx={{ borderRadius: '10px', px: 3, whiteSpace: 'nowrap' }}
          >
            Новый заказ
          </Button>
        </Stack>
      </Box>

      {error && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: alpha('#EF4444', 0.05), border: '1px solid', borderColor: alpha('#EF4444', 0.2) }}>
          <Typography color="error">{error}</Typography>
        </Paper>
      )}

      {/* ── Period navigation ─────────────────────────────────── */}
      {period !== 'custom' && s && (
        <PeriodNav
          period={period}
          label={s.period_label}
          canGoNext={s.can_go_next}
          onPrev={() => navigatePeriod(-1)}
          onNext={() => navigatePeriod(1)}
          onLabelClick={(el) => setMonthPickerAnchor(el)}
        />
      )}

      <MonthGridPicker
        anchorEl={monthPickerAnchor}
        onClose={() => setMonthPickerAnchor(null)}
        onApply={(dateStr) => { setRefDate(dateStr); setMonthPickerAnchor(null) }}
        initialYear={refDate ? new Date(refDate + 'T00:00:00').getFullYear() : new Date().getFullYear()}
      />

      {/* ── KPI Row ─────────────────────────────────────────── */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {/* Revenue + plan */}
        <Grid item xs={12} sm={6} md={3}>
          <RevenueCard
            revenue={s?.revenue ?? { value: 0, prev_value: 0, change_pct: null, plan: null, plan_pct: null }}
            periodLabel={s?.period_label ?? ''}
            loading={loading}
            isAdmin={isAdmin}
            onEditPlan={() => setPlanDialogOpen(true)}
          />
        </Grid>

        {/* Avg check */}
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Средний чек"
            value={s ? fmtMoney(s.avg_check.value) : '—'}
            subtitle={s?.avg_check.prev_value ? `пред. период: ${fmtMoney(s.avg_check.prev_value)}` : 'нет данных за пред. период'}
            trend={s?.avg_check.change_pct ?? null}
            icon={<ReceiptLongRounded />}
            color="#4F46E5"
            loading={loading}
          />
        </Grid>

        {/* Orders count */}
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Закрыто заказов"
            value={s ? String(s.orders_count.value) : '—'}
            subtitle={s?.orders_count.prev_value ? `пред. период: ${s.orders_count.prev_value}` : 'нет данных за пред. период'}
            trend={s?.orders_count.change_pct ?? null}
            icon={<BuildRounded />}
            color="#F59E0B"
            loading={loading}
          />
        </Grid>

        {/* WIP */}
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="В работе сейчас (WIP)"
            value={s ? fmtMoney(s.wip_amount) : '—'}
            subtitle="стоимость активных заказов"
            trend={null}
            icon={<CalendarTodayRounded />}
            color="#06B6D4"
            loading={loading}
          />
        </Grid>
      </Grid>

      {/* ── Alerts ────────────────────────────────────────────── */}
      {s && !loading && <AlertsBlock alerts={s.alerts} onNavigate={navigate} />}

      {/* ── Analytics Row ─────────────────────────────────────── */}
      {s && !loading && (
        <Grid container spacing={2.5} sx={{ mb: 3 }}>
          {/* Revenue chart */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2.5, height: '100%' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Выручка · {s.period_label}
              </Typography>
              <RevenueChart data={s.revenue_chart} period={s.period} />
            </Paper>
          </Grid>

          {/* Post load + pipeline */}
          <Grid item xs={12} md={4}>
            <Stack spacing={2.5} sx={{ height: '100%' }}>
              <Grid container spacing={1.5}>
                <Grid item xs={6}>
                  <LoadCard title="Загрузка сегодня" pct={s.post_load_today_pct} subtitle="слоты / посты" loading={false} />
                </Grid>
                <Grid item xs={6}>
                  <LoadCard title="Загрузка завтра" pct={s.post_load_tomorrow_pct} subtitle="предварительная" loading={false} />
                </Grid>
              </Grid>

              <Paper sx={{ p: 2.5, flex: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                  Pipeline — 7 дней
                </Typography>
                <PipelineBlock data={s.pipeline_7d} />
              </Paper>
            </Stack>
          </Grid>
        </Grid>
      )}

      {/* ── Mechanics ─────────────────────────────────────────── */}
      {s && !loading && (
        <Paper sx={{ p: 2.5, mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
            Выработка мастеров · {s.period_label}
          </Typography>
          <MechanicsTable mechanics={s.mechanics_stats} />
        </Paper>
      )}

      {/* ── Quick access ───────────────────────────────────────── */}
      <Typography variant="caption" sx={{ mb: 2, display: 'block', fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.05em' }}>
        Быстрый доступ
      </Typography>
      <Grid container spacing={2.5}>
        {mainActions.map((action) => (
          <Grid item xs={12} sm={6} md={3} key={action.title}>
            <Paper
              onClick={() => navigate(action.path)}
              sx={{
                p: 2.5, cursor: 'pointer', transition: 'all 0.2s ease',
                display: 'flex', flexDirection: 'column',
                border: '1px solid', borderColor: 'divider',
                '&:hover': {
                  transform: 'translateY(-3px)',
                  boxShadow: `0 8px 24px -8px ${alpha(action.color, 0.25)}`,
                  borderColor: action.color,
                  '& .nav-icon': { bgcolor: alpha(action.color, 0.12), color: action.color },
                  '& .nav-arrow': { transform: 'translateX(4px)', color: action.color },
                },
              }}
            >
              <Box
                className="nav-icon"
                sx={{ p: 1.5, borderRadius: '12px', bgcolor: '#F8FAFC', color: 'text.secondary', width: 'fit-content', mb: 2, transition: 'all 0.2s ease' }}
              >
                {action.icon}
              </Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>{action.title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1, fontSize: 13 }}>{action.desc}</Typography>
              <Stack direction="row" alignItems="center" spacing={0.5} sx={{ color: 'text.secondary' }}>
                <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: 10 }}>Перейти</Typography>
                <ArrowForwardRounded className="nav-arrow" sx={{ fontSize: 14, transition: 'all 0.2s ease' }} />
              </Stack>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* ── Plan dialog (admin only) ───────────────────────────── */}
      <PlanDialog
        open={planDialogOpen}
        onClose={() => setPlanDialogOpen(false)}
        onSave={handleSavePlan}
        currentPlan={s?.revenue.plan ?? null}
        year={getPlanYearMonth().year}
        month={getPlanYearMonth().month}
      />
    </Container>
  )
}
