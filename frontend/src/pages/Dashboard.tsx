import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Container, Typography, Box, Grid, Paper, Button, Stack,
  alpha, CircularProgress, Tooltip, LinearProgress,
  ToggleButton, ToggleButtonGroup, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, IconButton,
  Popover, Divider,
} from '@mui/material'
import {
  AssignmentRounded, EventAvailableRounded, Inventory2Rounded,
  PeopleAltRounded, AddRounded, ArrowForwardRounded,
  TrendingUpRounded, TrendingDownRounded, TrendingFlatRounded,
  WarningAmberRounded, AccountBalanceWalletRounded,
  EngineeringRounded, PersonOffRounded,
  AccessTimeRounded,
  EditRounded, CheckRounded,
  DateRangeRounded, ChevronLeftRounded, ChevronRightRounded,
  FlagRounded, InfoOutlined,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { DateField } from '../components/DateField'
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

interface CumulativePoint {
  label: string
  date: string
  current_cum: number | null
  previous_cum: number
  is_today: boolean
  is_future: boolean
}

interface RevenueCumulative {
  points: CumulativePoint[]
  plan_total: number | null
  forecast_eom: number | null
  prev_period_label: string
  today_current_cum: number | null
  today_previous_cum: number | null
  pace_vs_prev_pct: number | null
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
    forecast: number | null
    plan: number | null
    plan_pct: number | null
  }
  completed_revenue: { value: number; prev_value: number; change_pct: number | null }
  avg_check: { value: number; prev_value: number; change_pct: number | null }
  median_check: { value: number; prev_value: number; change_pct: number | null }
  orders_count: { value: number; prev_value: number; change_pct: number | null }
  wip: { amount: number; count: number }
  margins: {
    works_margin_pct: number | null
    parts_margin_pct: number | null
    works_share_pct: number | null
    works_revenue: number
    parts_revenue: number
    mechanic_fot: number
    parts_cost: number
  }
  post_load_today_pct: number | null
  post_load_tomorrow_pct: number | null
  pipeline_7d: PipelineDay[]
  revenue_chart: ChartDay[]
  revenue_cumulative: RevenueCumulative
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

function fmtMoneyFull(v: number): string {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0,
  }).format(v)
}

function pluralizeOrders(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 14) return 'заказов'
  if (mod10 === 1) return 'заказ'
  if (mod10 >= 2 && mod10 <= 4) return 'заказа'
  return 'заказов'
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

// ── Деньги и план ────────────────────────────────────────────────────────────

const PREV_PERIOD_LABEL: Record<Period, string> = {
  day: 'вчера',
  week: 'прошлая неделя',
  month: 'прошлый месяц',
  quarter: 'прошлый квартал',
  year: 'прошлый год',
  custom: 'пред. период',
}

const FORECAST_TITLE: Record<Period, string> = {
  day: 'Прогноз на день',
  week: 'Прогноз на неделю',
  month: 'Прогноз на месяц',
  quarter: 'Прогноз на квартал',
  year: 'Прогноз на год',
  custom: 'Прогноз периода',
}

const COLOR_FACT = '#10B981'
const COLOR_COMPLETED = '#0EA5E9'
const COLOR_FORECAST = '#3B82F6'

function planAccent(pct: number | null): string {
  if (pct === null) return '#94A3B8'
  if (pct >= 100) return '#10B981'
  if (pct >= 70) return '#3B82F6'
  if (pct >= 40) return '#F59E0B'
  return '#EF4444'
}

function MetricCard({
  label, description, info, value, accent, sub, loading, action,
}: {
  label: string
  description?: string
  info?: string
  value: React.ReactNode
  accent: string
  sub?: React.ReactNode
  loading: boolean
  action?: React.ReactNode
}) {
  return (
    <Paper sx={{
      p: 2.5, height: '100%', borderRadius: '14px',
      border: '1px solid', borderColor: 'divider',
      transition: 'box-shadow 0.2s, transform 0.15s, border-color 0.2s',
      '&:hover': {
        boxShadow: `0 6px 20px ${alpha(accent, 0.12)}`,
        borderColor: alpha(accent, 0.3),
        transform: 'translateY(-1px)',
      },
    }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: description ? 0.5 : 1.25 }}>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Typography sx={{
            fontSize: 12, fontWeight: 600,
            color: 'text.secondary',
          }}>
            {label}
          </Typography>
          {info && (
            <Tooltip title={info} arrow placement="top">
              <InfoOutlined
                sx={{
                  fontSize: 14, color: 'text.disabled',
                  cursor: 'help',
                  '&:hover': { color: 'text.secondary' },
                }}
              />
            </Tooltip>
          )}
        </Stack>
        {action}
      </Stack>
      {description && (
        <Typography sx={{
          fontSize: 11, color: 'text.disabled',
          lineHeight: 1.35, mb: 1,
        }}>
          {description}
        </Typography>
      )}
      {loading ? (
        <CircularProgress size={20} sx={{ color: accent }} />
      ) : (
        <Typography sx={{
          fontSize: 30, fontWeight: 800, lineHeight: 1.05,
          letterSpacing: '-0.02em', color: accent,
        }}>
          {value}
        </Typography>
      )}
      {sub && (
        <Box sx={{ mt: 1, minHeight: 18 }}>
          {sub}
        </Box>
      )}
    </Paper>
  )
}

function PlanCtaCard({ isAdmin, onEdit }: { isAdmin: boolean; onEdit: () => void }) {
  return (
    <Paper sx={{
      p: 2.5, height: '100%', borderRadius: '14px',
      border: '1px dashed', borderColor: alpha(COLOR_FACT, 0.45),
      bgcolor: alpha(COLOR_FACT, 0.04),
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      cursor: isAdmin ? 'pointer' : 'default',
      transition: 'background-color 0.15s, border-color 0.15s',
      '&:hover': isAdmin ? {
        bgcolor: alpha(COLOR_FACT, 0.08),
        borderColor: COLOR_FACT,
      } : undefined,
    }}
      onClick={isAdmin ? onEdit : undefined}
      role={isAdmin ? 'button' : undefined}
      tabIndex={isAdmin ? 0 : undefined}
      onKeyDown={isAdmin ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onEdit() }
      } : undefined}
    >
      <Typography sx={{ fontSize: 12, fontWeight: 600, color: 'text.secondary', mb: 1 }}>
        Выполнение плана
      </Typography>
      {isAdmin ? (
        <Stack direction="row" alignItems="center" spacing={1.25}>
          <Box sx={{
            width: 32, height: 32, borderRadius: '10px',
            bgcolor: alpha(COLOR_FACT, 0.15),
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: COLOR_FACT, flexShrink: 0,
          }}>
            <FlagRounded fontSize="small" />
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography sx={{ fontWeight: 700, fontSize: 14, color: 'text.primary', lineHeight: 1.2 }}>
              Задать план
            </Typography>
            <Typography sx={{ fontSize: 11, color: 'text.secondary' }}>
              Чтобы видеть прогресс
            </Typography>
          </Box>
          <ArrowForwardRounded sx={{ fontSize: 18, color: COLOR_FACT }} />
        </Stack>
      ) : (
        <Typography sx={{ fontSize: 13, color: 'text.secondary' }}>
          План на период не задан
        </Typography>
      )}
    </Paper>
  )
}

function PlanProgressBar({ value, plan, pct }: { value: number; plan: number; pct: number }) {
  const accent = planAccent(pct)
  const clampedPct = Math.min(Math.max(pct, 0), 100)
  return (
    <Paper sx={{
      p: 2.25, mt: 2, borderRadius: '14px',
      border: '1px solid', borderColor: 'divider',
    }}>
      <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1 }}>
        <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'text.primary' }}>
          Прогресс по плану
        </Typography>
        <Typography sx={{
          fontSize: 13, fontWeight: 700,
          color: 'text.secondary',
          fontVariantNumeric: 'tabular-nums',
        }}>
          <Box component="span" sx={{ color: accent, fontWeight: 800 }}>
            {fmtMoneyFull(value)}
          </Box>
          {' / '}
          {fmtMoneyFull(plan)}
        </Typography>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={clampedPct}
        sx={{
          height: 10, borderRadius: 6,
          bgcolor: alpha(accent, 0.12),
          '& .MuiLinearProgress-bar': {
            bgcolor: accent, borderRadius: 6,
            transition: 'transform 0.4s ease',
          },
        }}
      />
    </Paper>
  )
}

function MoneyAndPlanSection({
  revenue, completedRevenue, period, loading, isAdmin, onEditPlan,
}: {
  revenue: DashboardStats['revenue']
  completedRevenue: DashboardStats['completed_revenue']
  period: Period
  loading: boolean
  isAdmin: boolean
  onEditPlan: () => void
}) {
  const prevLabel = PREV_PERIOD_LABEL[period]
  const forecastTitle = FORECAST_TITLE[period]
  const planPct = revenue.plan_pct
  const planAccentColor = planAccent(planPct)

  // sub-blocks
  const factSub = revenue.prev_value > 0 ? (
    <Stack direction="row" spacing={0.75} alignItems="center" sx={{ flexWrap: 'wrap' }}>
      <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
        {prevLabel}: <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(revenue.prev_value)}</Box>
      </Typography>
      <TrendBadge pct={revenue.change_pct} />
    </Stack>
  ) : (
    <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>нет данных за пред. период</Typography>
  )

  const completedSub = completedRevenue.prev_value > 0 ? (
    <Stack direction="row" spacing={0.75} alignItems="center" sx={{ flexWrap: 'wrap' }}>
      <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
        {prevLabel}: <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(completedRevenue.prev_value)}</Box>
      </Typography>
      <TrendBadge pct={completedRevenue.change_pct} />
    </Stack>
  ) : (
    <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>нет данных за пред. период</Typography>
  )

  const forecastSub = revenue.forecast === null
    ? <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>период ещё не начался</Typography>
    : revenue.forecast === revenue.value
      ? <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>период закрыт</Typography>
      : <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>при текущем темпе</Typography>

  const planValueNode = planPct === null
    ? '—'
    : `${Math.round(planPct)}%`
  const planSub = revenue.plan
    ? (
      <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
        план <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(revenue.plan)}</Box>
      </Typography>
    )
    : null
  const planAction = revenue.plan && isAdmin
    ? (
      <Tooltip title="Изменить план">
        <IconButton
          size="small"
          onClick={onEditPlan}
          sx={{
            p: 0.5,
            borderRadius: 1.5,
            color: planAccentColor,
            bgcolor: alpha(planAccentColor, 0.1),
            border: '1px solid',
            borderColor: alpha(planAccentColor, 0.2),
            '&:hover': {
              bgcolor: alpha(planAccentColor, 0.18),
              borderColor: planAccentColor,
            },
          }}
        >
          <EditRounded sx={{ fontSize: 14 }} />
        </IconButton>
      </Tooltip>
    )
    : undefined

  return (
    <Box sx={{ mb: 3 }}>
      <Typography sx={{
        fontSize: 11, fontWeight: 700, color: 'text.secondary',
        textTransform: 'uppercase', letterSpacing: '0.08em', mb: 1.25,
      }}>
        Деньги и план
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Поступления"
            value={`${fmtMoneyFull(revenue.value)}`}
            accent={COLOR_FACT}
            sub={factSub}
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Выручка"
            info={'Выручка по начислению: сумма всех ЗН со статусом «Завершён», закрытых в периоде. Не зависит от оплат.'}
            value={`${fmtMoneyFull(completedRevenue.value)}`}
            accent={COLOR_COMPLETED}
            sub={completedSub}
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label={forecastTitle}
            value={revenue.forecast === null ? '—' : fmtMoneyFull(revenue.forecast)}
            accent={COLOR_FORECAST}
            sub={forecastSub}
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {revenue.plan
            ? (
              <MetricCard
                label="Выполнение плана"
                value={planValueNode}
                accent={planAccentColor}
                sub={planSub}
                loading={loading}
                action={planAction}
              />
            )
            : (
              <PlanCtaCard isAdmin={isAdmin} onEdit={onEditPlan} />
            )
          }
        </Grid>
      </Grid>

      {revenue.plan && !loading && planPct !== null && (
        <PlanProgressBar value={revenue.value} plan={revenue.plan} pct={planPct} />
      )}
    </Box>
  )
}

// ── Чек и заказы ─────────────────────────────────────────────────────────────

const COLOR_AVG = '#3B82F6'      // средний — синий
const COLOR_MEDIAN = '#F59E0B'   // медиана — янтарный (как в макете)
const COLOR_ORDERS = '#6366F1'   // закрыто — индиго
const COLOR_WIP = '#06B6D4'      // в работе — голубой

function ChecksAndOrdersSection({
  avgCheck, medianCheck, ordersCount, wip, period, loading,
}: {
  avgCheck: DashboardStats['avg_check']
  medianCheck: DashboardStats['median_check']
  ordersCount: DashboardStats['orders_count']
  wip: DashboardStats['wip']
  period: Period
  loading: boolean
}) {
  const prevLabel = PREV_PERIOD_LABEL[period]

  const trendSub = (prev: number, change: number | null, fmt: (n: number) => string) =>
    prev > 0 ? (
      <Stack direction="row" spacing={0.75} alignItems="center" sx={{ flexWrap: 'wrap' }}>
        <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
          {prevLabel}: <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmt(prev)}</Box>
        </Typography>
        <TrendBadge pct={change} />
      </Stack>
    ) : (
      <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>нет данных за пред. период</Typography>
    )

  // Подсказка по медиане относительно среднего — текстовый ярлык, не вычисление.
  let medianHint: React.ReactNode = trendSub(medianCheck.prev_value, medianCheck.change_pct, fmtMoneyFull)
  if (!loading && avgCheck.value > 0 && medianCheck.value > 0) {
    const ratio = medianCheck.value / avgCheck.value
    if (ratio < 0.85) {
      medianHint = (
        <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
          ниже среднего <Box component="span" sx={{ color: 'text.disabled' }}>→</Box> есть крупные
        </Typography>
      )
    } else if (ratio > 1.15) {
      medianHint = (
        <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
          выше среднего <Box component="span" sx={{ color: 'text.disabled' }}>→</Box> много мелких
        </Typography>
      )
    } else {
      medianHint = (
        <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>близко к среднему</Typography>
      )
    }
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Typography sx={{
        fontSize: 11, fontWeight: 700, color: 'text.secondary',
        textTransform: 'uppercase', letterSpacing: '0.08em', mb: 1.25,
      }}>
        Чек и заказы
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Средний чек"
            value={fmtMoneyFull(avgCheck.value)}
            accent={COLOR_AVG}
            sub={trendSub(avgCheck.prev_value, avgCheck.change_pct, fmtMoneyFull)}
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Медианный чек"
            description="это серединное значение всех заказ-нарядов, без перекоса крупными"
            value={fmtMoneyFull(medianCheck.value)}
            accent={COLOR_MEDIAN}
            sub={medianHint}
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Закрыто заказов"
            value={String(ordersCount.value)}
            accent={COLOR_ORDERS}
            sub={trendSub(ordersCount.prev_value, ordersCount.change_pct, (n) => String(n))}
            loading={loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Заказы в работе"
            value={fmtMoneyFull(wip.amount)}
            accent={COLOR_WIP}
            sub={
              <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
                {wip.count} {pluralizeOrders(wip.count)}
              </Typography>
            }
            loading={loading}
          />
        </Grid>
      </Grid>
    </Box>
  )
}

// ── Маржа ────────────────────────────────────────────────────────────────────

// Пороги по «здоровью» маржи — мнение бизнеса, а не данные;
// держим тут (не на бекенде), потому что это про окраску UI.
function worksMarginAccent(pct: number | null): string {
  if (pct === null) return '#94A3B8'
  if (pct >= 50) return '#10B981'
  if (pct >= 30) return '#F59E0B'
  return '#EF4444'
}
function partsMarginAccent(pct: number | null): string {
  if (pct === null) return '#94A3B8'
  if (pct >= 25) return '#10B981'
  if (pct >= 15) return '#F59E0B'
  return '#EF4444'
}
function worksShareAccent(pct: number | null): string {
  if (pct === null) return '#94A3B8'
  if (pct >= 55) return '#10B981'
  if (pct >= 40) return '#F59E0B'
  return '#EF4444'
}

function fmtPct(pct: number | null): string {
  if (pct === null) return '—'
  return `${Math.round(pct)}%`
}

function MarginsSection({
  margins, loading,
}: {
  margins: DashboardStats['margins']
  loading: boolean
}) {
  const worksAccent = worksMarginAccent(margins.works_margin_pct)
  const partsAccent = partsMarginAccent(margins.parts_margin_pct)
  const shareAccent = worksShareAccent(margins.works_share_pct)

  const partsShare = margins.works_share_pct === null
    ? null
    : Math.max(0, Math.round(100 - margins.works_share_pct))

  return (
    <Box sx={{ mb: 3 }}>
      <Typography sx={{
        fontSize: 11, fontWeight: 700, color: 'text.secondary',
        textTransform: 'uppercase', letterSpacing: '0.08em', mb: 1.25,
      }}>
        Маржа <Box component="span" sx={{ textTransform: 'none', color: 'text.disabled', fontWeight: 600 }}>
          (реальная прибыль, не оборот)
        </Box>
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            label="Маржа по работам"
            info="не считая окладов ваших автомехаников"
            description="доля от выручки по работам после бонусов механикам"
            value={fmtPct(margins.works_margin_pct)}
            accent={worksAccent}
            sub={
              margins.works_revenue > 0 ? (
                <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
                  работы <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(margins.works_revenue)}</Box>
                  {' − бонус '}
                  <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(margins.mechanic_fot)}</Box>
                </Typography>
              ) : (
                <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>нет продаж работ за период</Typography>
              )
            }
            loading={loading}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            label="Маржа по запчастям"
            description="доля от выручки по запчастям после закупки"
            value={fmtPct(margins.parts_margin_pct)}
            accent={partsAccent}
            sub={
              margins.parts_revenue > 0 ? (
                <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
                  запчасти <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(margins.parts_revenue)}</Box>
                  {' − закупка '}
                  <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>{fmtMoneyFull(margins.parts_cost)}</Box>
                </Typography>
              ) : (
                <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>нет продаж запчастей за период</Typography>
              )
            }
            loading={loading}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            label="Доля работ в выручке"
            value={fmtPct(margins.works_share_pct)}
            accent={shareAccent}
            sub={
              partsShare === null
                ? <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>нет данных за период</Typography>
                : <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
                    остальное — запчасти ({partsShare}%)
                  </Typography>
            }
            loading={loading}
          />
        </Grid>
      </Grid>
    </Box>
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

// ── RevenueRaceChart ─────────────────────────────────────────────────────────
//
// Кумулятивная «гонка месяца»: текущий период vs предыдущий, обе линии идут
// от 0 к концу периода. На фоне — пунктир плана и прогноз-конус до конца
// месяца. Под графиком — короткая summary-строка: темп vs прошлый период,
// прогноз и план. Все числа приходят с бекенда, фронт ничего не считает.

const RACE_COLOR_CUR = '#10B981'
const RACE_COLOR_PREV = '#94A3B8'
const RACE_COLOR_PLAN = '#3B82F6'

function RevenueRaceChart({ data }: { data: RevenueCumulative }) {
  const points = data.points
  const svgRef = useRef<SVGSVGElement>(null)
  // Индекс точки под курсором; null = ничего не выбрано (показываем summary).
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)

  if (points.length < 2) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
        <Typography color="text.secondary" variant="body2">Недостаточно данных за период</Typography>
      </Box>
    )
  }

  // SVG-координатная сетка. ViewBox делаем 800×220, дальше CSS-масштаб
  // подгонит под фактическую ширину карточки.
  const W = 800
  const H = 220
  const PAD = { l: 56, r: 16, t: 14, b: 28 }
  const innerW = W - PAD.l - PAD.r
  const innerH = H - PAD.t - PAD.b

  // Максимум по Y — учитываем план и прогноз тоже, чтобы линии не вылезли.
  const maxY = Math.max(
    data.plan_total ?? 0,
    data.forecast_eom ?? 0,
    ...points.map(p => p.current_cum ?? 0),
    ...points.map(p => p.previous_cum),
    1,
  )

  const x = (i: number) => PAD.l + (i / (points.length - 1)) * innerW
  const y = (v: number) => PAD.t + innerH - (v / maxY) * innerH

  // Полилинии. Current — только не-future точки.
  const curPath = points
    .map((p, i) => p.current_cum !== null ? `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.current_cum)}` : null)
    .filter(Boolean)
    .join(' ')
  const prevPath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.previous_cum)}`)
    .join(' ')

  // Прогноз-линия — пунктир от точки «сегодня» до forecast_eom в правом краю.
  const todayIdx = points.findIndex(p => p.is_today)
  const forecastPath = (todayIdx >= 0 && data.forecast_eom !== null && points[todayIdx].current_cum !== null)
    ? `M ${x(todayIdx)} ${y(points[todayIdx].current_cum!)} L ${x(points.length - 1)} ${y(data.forecast_eom)}`
    : null

  // Ticks: 0 / mid / max по Y; первый/середина/последний по X.
  const yTicks = [0, maxY / 2, maxY]
  const xTickIdx = [0, Math.floor((points.length - 1) / 2), points.length - 1]

  const todayPt = todayIdx >= 0 ? points[todayIdx] : null
  const lastPrev = points[points.length - 1]

  // Цвет темпа: ≥ 0 — зелёный, < 0 — красный, ровно 0 — серый.
  const pacePct = data.pace_vs_prev_pct
  const paceColor = pacePct === null ? 'text.secondary'
    : Math.abs(pacePct) < 0.5 ? 'text.secondary'
      : pacePct > 0 ? 'success.main' : 'error.main'

  // ── Hover-логика ───────────────────────────────────────────────────────
  // Переводим pixel-координату курсора в индекс ближайшей точки данных.
  const handlePointerMove = (e: React.PointerEvent<SVGRectElement>) => {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    // Из пикселей экрана → в координаты viewBox.
    const vbX = ((e.clientX - rect.left) / rect.width) * W
    const ratio = (vbX - PAD.l) / innerW
    const clamped = Math.max(0, Math.min(1, ratio))
    const idx = Math.round(clamped * (points.length - 1))
    setHoverIdx(idx)
  }
  const handlePointerLeave = () => setHoverIdx(null)

  const hoverPt = hoverIdx !== null ? points[hoverIdx] : null
  // Tooltip-позиция в процентах от ширины/высоты обёртки — чтобы корректно
  // позиционироваться внутри гибкого контейнера, а не в viewBox-координатах.
  const tooltipLeftPct = hoverIdx !== null ? (x(hoverIdx) / W) * 100 : 0
  // Anchor-Y берём по линии current (если есть данные) или previous.
  const anchorY = hoverPt
    ? (hoverPt.current_cum !== null ? y(hoverPt.current_cum) : y(hoverPt.previous_cum))
    : 0
  const tooltipTopPct = (anchorY / H) * 100
  // Flip tooltip-а вправо если он близко к левому краю, иначе влево.
  const flipRight = tooltipLeftPct < 30
  const deltaAbs = hoverPt && hoverPt.current_cum !== null
    ? hoverPt.current_cum - hoverPt.previous_cum
    : null
  const deltaPct = hoverPt && hoverPt.current_cum !== null && hoverPt.previous_cum > 0
    ? ((hoverPt.current_cum - hoverPt.previous_cum) / hoverPt.previous_cum) * 100
    : null

  return (
    <Box>
      {/* Легенда */}
      <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mb: 1, rowGap: 0.5 }}>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Box sx={{ width: 16, height: 2.5, bgcolor: RACE_COLOR_CUR, borderRadius: 1 }} />
          <Typography variant="caption" color="text.secondary">Текущий период</Typography>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Box sx={{ width: 16, height: 2.5, bgcolor: RACE_COLOR_PREV, borderRadius: 1 }} />
          <Typography variant="caption" color="text.secondary">{data.prev_period_label}</Typography>
        </Stack>
        {data.forecast_eom !== null && (
          <Stack direction="row" alignItems="center" spacing={0.5}>
            <Box sx={{
              width: 16, height: 0,
              borderTop: `2px dashed ${RACE_COLOR_CUR}`,
            }} />
            <Typography variant="caption" color="text.secondary">Прогноз до конца периода</Typography>
          </Stack>
        )}
        {data.plan_total !== null && (
          <Stack direction="row" alignItems="center" spacing={0.5}>
            <Box sx={{
              width: 16, height: 0,
              borderTop: `2px dashed ${RACE_COLOR_PLAN}`,
            }} />
            <Typography variant="caption" color="text.secondary">План: {fmtMoneyFull(data.plan_total)}</Typography>
          </Stack>
        )}
      </Stack>

      {/* График */}
      <Box sx={{ width: '100%', overflow: 'visible', position: 'relative' }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
          preserveAspectRatio="none"
        >
          {/* Y-сетка + подписи */}
          {yTicks.map((v, i) => (
            <g key={i}>
              <line
                x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)}
                stroke="#E2E8F0" strokeWidth={1}
                strokeDasharray={i === 0 ? '' : '3,3'}
              />
              <text x={PAD.l - 8} y={y(v) + 4} fontSize={11} fill="#94A3B8" textAnchor="end">
                {fmtMoneyShort(v)}
              </text>
            </g>
          ))}

          {/* X-подписи */}
          {xTickIdx.map((idx) => (
            <text
              key={idx}
              x={x(idx)} y={H - PAD.b + 16}
              fontSize={11} fill="#94A3B8" textAnchor="middle"
            >
              {points[idx].label.split(' ').slice(0, 2).join(' ')}
            </text>
          ))}

          {/* План — горизонтальная пунктирная линия */}
          {data.plan_total !== null && (
            <line
              x1={PAD.l} x2={W - PAD.r}
              y1={y(data.plan_total)} y2={y(data.plan_total)}
              stroke={RACE_COLOR_PLAN} strokeWidth={1.5}
              strokeDasharray="5,4"
            />
          )}

          {/* Линия прошлого периода */}
          <path
            d={prevPath}
            fill="none" stroke={RACE_COLOR_PREV}
            strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"
          />

          {/* Линия текущего периода (до сегодня) */}
          {curPath && (
            <path
              d={curPath}
              fill="none" stroke={RACE_COLOR_CUR}
              strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round"
            />
          )}

          {/* Пунктир-прогноз от сегодня до forecast_eom */}
          {forecastPath && (
            <path
              d={forecastPath}
              fill="none" stroke={RACE_COLOR_CUR}
              strokeWidth={2} strokeDasharray="5,4" strokeLinecap="round"
              opacity={0.7}
            />
          )}

          {/* Маркер «сегодня» (только если hover не активен) */}
          {hoverIdx === null && todayPt && todayPt.current_cum !== null && (
            <>
              <line
                x1={x(todayIdx)} x2={x(todayIdx)}
                y1={PAD.t} y2={H - PAD.b}
                stroke={RACE_COLOR_CUR} strokeWidth={1} opacity={0.25}
                strokeDasharray="2,3"
              />
              <circle
                cx={x(todayIdx)} cy={y(todayPt.current_cum)}
                r={5} fill={RACE_COLOR_CUR} stroke="#fff" strokeWidth={2}
              />
            </>
          )}

          {/* ── Hover-индикаторы ── */}
          {hoverPt && (
            <>
              {/* Вертикальная серая линия — guide */}
              <line
                x1={x(hoverIdx!)} x2={x(hoverIdx!)}
                y1={PAD.t} y2={H - PAD.b}
                stroke="#94A3B8" strokeWidth={1} opacity={0.45}
              />
              {/* Кружок на серой линии (прошлый период) */}
              <circle
                cx={x(hoverIdx!)} cy={y(hoverPt.previous_cum)}
                r={4.5} fill={RACE_COLOR_PREV} stroke="#fff" strokeWidth={2}
              />
              {/* Кружок на зелёной линии (текущий) — только если есть данные */}
              {hoverPt.current_cum !== null && (
                <circle
                  cx={x(hoverIdx!)} cy={y(hoverPt.current_cum)}
                  r={5} fill={RACE_COLOR_CUR} stroke="#fff" strokeWidth={2}
                />
              )}
            </>
          )}

          {/* Невидимая hit-area для отлова мыши — последней, чтобы быть сверху */}
          <rect
            x={PAD.l} y={PAD.t}
            width={innerW} height={innerH}
            fill="transparent"
            style={{ cursor: 'crosshair' }}
            onPointerMove={handlePointerMove}
            onPointerLeave={handlePointerLeave}
          />
        </svg>

        {/* Tooltip-оверлей: HTML поверх SVG. Позиционируется через % внутри
            обёртки-контейнера, поэтому работает на любой ширине. */}
        {hoverPt && (
          <Box
            sx={{
              position: 'absolute',
              left: `${tooltipLeftPct}%`,
              top: `${tooltipTopPct}%`,
              transform: flipRight
                ? 'translate(12px, -50%)'
                : 'translate(calc(-100% - 12px), -50%)',
              pointerEvents: 'none',
              bgcolor: '#0F172A',
              color: '#fff',
              borderRadius: '8px',
              px: 1.5, py: 1,
              fontSize: 12,
              boxShadow: '0 8px 24px rgba(15,23,42,0.25)',
              whiteSpace: 'nowrap',
              zIndex: 5,
            }}
          >
            <Box sx={{ fontWeight: 700, mb: 0.5 }}>{hoverPt.label}</Box>
            <Stack direction="row" alignItems="center" spacing={0.75} sx={{ mb: 0.25 }}>
              <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: RACE_COLOR_CUR }} />
              <Box>Текущий: <b>{hoverPt.current_cum !== null ? fmtMoneyFull(hoverPt.current_cum) : '—'}</b></Box>
            </Stack>
            <Stack direction="row" alignItems="center" spacing={0.75}>
              <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: RACE_COLOR_PREV }} />
              <Box>{data.prev_period_label}: <b>{fmtMoneyFull(hoverPt.previous_cum)}</b></Box>
            </Stack>
            {deltaAbs !== null && (
              <Box sx={{
                mt: 0.5, pt: 0.5,
                borderTop: '1px solid rgba(255,255,255,0.15)',
                color: deltaAbs > 0 ? '#34D399' : deltaAbs < 0 ? '#F87171' : '#CBD5E1',
                fontSize: 11, fontWeight: 700,
              }}>
                {deltaAbs > 0 ? '+' : ''}{fmtMoneyFull(deltaAbs)}
                {deltaPct !== null && (
                  <Box component="span" sx={{ ml: 0.75, opacity: 0.85 }}>
                    ({deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(1)}%)
                  </Box>
                )}
              </Box>
            )}
            {hoverPt.is_future && (
              <Box sx={{ mt: 0.5, fontSize: 10, opacity: 0.7 }}>прогноз / ещё впереди</Box>
            )}
          </Box>
        )}
      </Box>

      {/* Summary под графиком */}
      <Stack
        direction="row" spacing={3}
        sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider', flexWrap: 'wrap', rowGap: 1 }}
      >
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 700 }}>
            На сегодня
          </Typography>
          <Typography sx={{ fontWeight: 800, fontSize: 18, lineHeight: 1.1 }}>
            {fmtMoneyFull(data.today_current_cum ?? 0)}
          </Typography>
          {data.today_previous_cum !== null && data.today_previous_cum > 0 && (
            <Typography variant="caption" color="text.secondary">
              {data.prev_period_label} на ту же дату: {fmtMoneyFull(data.today_previous_cum)}
            </Typography>
          )}
        </Box>

        {pacePct !== null && (
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 700 }}>
              Темп
            </Typography>
            <Typography sx={{ fontWeight: 800, fontSize: 18, lineHeight: 1.1, color: paceColor }}>
              {pacePct > 0 ? '+' : ''}{pacePct.toFixed(1)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">vs {data.prev_period_label.toLowerCase()}</Typography>
          </Box>
        )}

        {data.forecast_eom !== null && data.forecast_eom !== data.today_current_cum && (
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 700 }}>
              Прогноз
            </Typography>
            <Typography sx={{ fontWeight: 800, fontSize: 18, lineHeight: 1.1, color: RACE_COLOR_CUR }}>
              {fmtMoneyFull(data.forecast_eom)}
            </Typography>
            <Typography variant="caption" color="text.secondary">при текущем темпе</Typography>
          </Box>
        )}

        <Box sx={{ ml: 'auto', textAlign: 'right' }}>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 700 }}>
            {data.prev_period_label} (итог)
          </Typography>
          <Typography sx={{ fontWeight: 800, fontSize: 18, lineHeight: 1.1, color: 'text.secondary' }}>
            {fmtMoneyFull(lastPrev.previous_cum)}
          </Typography>
        </Box>
      </Stack>
    </Box>
  )
}

// Короткий формат денег для оси Y: «50 тыс ₽», «1.2 млн ₽».
function fmtMoneyShort(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} млн`
  if (v >= 1_000) return `${Math.round(v / 1_000)} тыс`
  return `${Math.round(v)}`
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
        <DateField
          label="Начало"
          size="small"
          value={from}
          onChange={(v) => { setFrom(v); setError('') }}
          minWidth={0}
          clearable={false}
        />
        <DateField
          label="Конец"
          size="small"
          value={to}
          onChange={(v) => { setTo(v); setError('') }}
          minWidth={0}
          clearable={false}
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
    // Локальные YYYY-MM-DD без UTC-сдвига: toISOString() конвертирует в UTC
    // и в МСК (+3) откидывает дату назад на сутки — кнопка «вперёд» уходила
    // не в следующий месяц, а в последний день текущего.
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    const todayStr = fmt(new Date())
    const base = new Date((stats.nav_ref || todayStr) + 'T00:00:00')
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
    setRefDate(fmt(newDate))
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
    <Container maxWidth="xl" disableGutters sx={{ px: { xs: 0, sm: 2 } }}>
      {/* ── Header ────────────────────────────────────────────── */}
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        alignItems={{ xs: 'stretch', md: 'flex-end' }}
        justifyContent="space-between"
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography sx={{
            fontWeight: 800,
            fontSize: { xs: '1.5rem', md: '2.125rem' },
            lineHeight: 1.15,
          }}>
            Панель управления
          </Typography>
          <Typography color="text.secondary" sx={{ fontSize: { xs: 13, md: 16 } }}>
            {new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}
            {s && ` · ${s.period_label}`}
          </Typography>
        </Box>
        <Stack
          direction="row"
          spacing={{ xs: 1, sm: 2 }}
          alignItems="center"
          sx={{ flexWrap: 'wrap', rowGap: 1 }}
        >
          {/* Period selector */}
          <ToggleButtonGroup
            value={period}
            exclusive
            onChange={handlePeriodChange}
            size="small"
            sx={{
              bgcolor: 'background.paper',
              flexWrap: 'wrap',
              '& .MuiToggleButton-root': {
                px: { xs: 1, sm: 1.75 },
                py: { xs: 0.5, sm: 0.6 },
                fontSize: { xs: 11, sm: 12 },
                fontWeight: 600,
                textTransform: 'none',
                border: '1px solid',
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

          {isAdmin && (() => {
            const planSet = !!s?.revenue.plan && s.revenue.plan > 0
            return (
              <Button
                variant="contained"
                startIcon={planSet ? <EditRounded /> : <AddRounded />}
                onClick={() => setPlanDialogOpen(true)}
                sx={{
                  borderRadius: '10px',
                  px: { xs: 1.5, sm: 3 },
                  py: { xs: 0.6, sm: 1 },
                  fontSize: { xs: 12, sm: 14 },
                  whiteSpace: 'nowrap',
                  display: { xs: 'none', sm: 'inline-flex' },
                }}
              >
                {planSet ? 'Изменить план' : 'Задать план'}
              </Button>
            )
          })()}
        </Stack>
      </Stack>

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

      {/* ── Деньги и план ───────────────────────────────────── */}
      <MoneyAndPlanSection
        revenue={s?.revenue ?? { value: 0, prev_value: 0, change_pct: null, forecast: null, plan: null, plan_pct: null }}
        completedRevenue={s?.completed_revenue ?? { value: 0, prev_value: 0, change_pct: null }}
        period={period}
        loading={loading}
        isAdmin={isAdmin}
        onEditPlan={() => setPlanDialogOpen(true)}
      />

      {/* ── Чек и заказы ────────────────────────────────────── */}
      <ChecksAndOrdersSection
        avgCheck={s?.avg_check ?? { value: 0, prev_value: 0, change_pct: null }}
        medianCheck={s?.median_check ?? { value: 0, prev_value: 0, change_pct: null }}
        ordersCount={s?.orders_count ?? { value: 0, prev_value: 0, change_pct: null }}
        wip={s?.wip ?? { amount: 0, count: 0 }}
        period={period}
        loading={loading}
      />

      {/* ── Маржа (реальная прибыль, не оборот) ──────────────── */}
      <MarginsSection
        margins={s?.margins ?? {
          works_margin_pct: null, parts_margin_pct: null, works_share_pct: null,
          works_revenue: 0, parts_revenue: 0, mechanic_fot: 0, parts_cost: 0,
        }}
        loading={loading}
      />

      {/* ── Alerts ────────────────────────────────────────────── */}
      {s && !loading && <AlertsBlock alerts={s.alerts} onNavigate={navigate} />}

      {/* ── Revenue race chart — кумулятивная гонка периода ───── */}
      {s && !loading && (
        <Paper sx={{ p: 2.5, mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
            Выручка · {s.period_label}
            <Box component="span" sx={{ ml: 1, fontSize: 11, fontWeight: 600, color: 'text.disabled', textTransform: 'none' }}>
              гонка нарастающим итогом
            </Box>
          </Typography>
          <RevenueRaceChart data={s.revenue_cumulative} />
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
