import React from 'react'
import {
  Box, Grid, Paper, Typography, LinearProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, Tooltip, alpha,
} from '@mui/material'
import {
  TrendingUpRounded,
  ReceiptRounded,
  ShoppingCartRounded,
  CreditCardRounded,
} from '@mui/icons-material'
import { RevenueReportResponse } from '../../types'
import { BRAND, FONT, MOTION, PALETTE, iconBoxSx, overlineSx } from '../../design-tokens'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

const fmtShort = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`
  return String(n)
}

// ── KPI stat card ─────────────────────────────────────────────────────────────

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box sx={iconBoxSx(color)}>{icon}</Box>
      <Box>
        <Typography sx={{ ...overlineSx, mb: 0.3 }}>{label}</Typography>
        <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
          {value}
        </Typography>
      </Box>
    </Paper>
  )
}

// ── Vertical bar chart ────────────────────────────────────────────────────────

const CHART_HEIGHT = 200 // px — fixed bar column height

interface BarChartProps {
  items: RevenueReportResponse['by_day']
}

function DailyBarChart({ items }: BarChartProps) {
  const maxRevenue = Math.max(...items.map((d) => d.revenue), 1)

  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Нет данных за выбранный период
      </Typography>
    )
  }

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: '4px',
        overflowX: 'auto',
        overflowY: 'visible',
        pb: 0.5,
        pt: 1,
        '&::-webkit-scrollbar': { height: 3 },
        '&::-webkit-scrollbar-track': { bgcolor: 'transparent' },
        '&::-webkit-scrollbar-thumb': { bgcolor: PALETTE.stone[300], borderRadius: 2 },
      }}
    >
      {items.map((day) => {
        // teal cap height proportional to revenue; min 4px when non-zero
        const tealPx = day.revenue > 0
          ? Math.max((day.revenue / maxRevenue) * CHART_HEIGHT, 4)
          : 0
        const date = new Date(day.date + 'T00:00:00')
        const dayNum = date.toLocaleDateString('ru-RU', { day: 'numeric' })
        const monthAbbr = date.toLocaleDateString('ru-RU', { month: 'short' }).replace('.', '')

        return (
          <Tooltip
            key={day.date}
            title={
              <Box sx={{ textAlign: 'center', py: 0.3 }}>
                <Typography variant="caption" sx={{ fontWeight: 700, display: 'block' }}>
                  {date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', fontWeight: 800 }}>
                  {fmt(day.revenue)}
                </Typography>
                <Typography variant="caption" color="inherit" sx={{ opacity: 0.75 }}>
                  {day.orders_count} заказов
                </Typography>
              </Box>
            }
            placement="top"
            arrow
          >
            <Box
              sx={{
                flex: '1 0 22px',
                maxWidth: 56,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                cursor: 'default',
              }}
            >
              {/* Full-height bar: teal cap on top, gray fill below */}
              <Box
                sx={{
                  position: 'relative',
                  width: '82%',
                  minWidth: 14,
                  height: CHART_HEIGHT,
                  overflow: 'visible',
                  borderRadius: '4px',
                  display: 'flex',
                  flexDirection: 'column',
                  '&:hover .bar-teal': { filter: 'brightness(1.1)' },
                }}
              >
                {/* Gray fill — top (empty space) */}
                <Box
                  sx={{
                    flex: 1,
                    bgcolor: PALETTE.stone[200],
                    borderRadius: tealPx > 0 ? '4px 4px 0 0' : '4px',
                  }}
                />

                {/* Teal bar — bottom, proportional height */}
                <Box
                  className="bar-teal"
                  sx={{
                    height: tealPx,
                    flexShrink: 0,
                    background: tealPx > 0 ? BRAND.gradient : 'transparent',
                    borderRadius: '0 0 4px 4px',
                    transition: `height ${MOTION.spring}`,
                  }}
                />

                {/* Value label — always inside teal, near its top edge */}
                {day.revenue > 0 && (
                  <Typography
                    sx={{
                      position: 'absolute',
                      // clamp: at least 4px from bottom, at most CHART_HEIGHT-16px from bottom
                      bottom: `${Math.min(Math.max(tealPx - 18, 4), CHART_HEIGHT - 16)}px`,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      fontSize: '0.58rem',
                      fontWeight: 700,
                      color: '#fff',
                      fontFamily: FONT.mono,
                      letterSpacing: '-0.02em',
                      whiteSpace: 'nowrap',
                      lineHeight: 1.4,
                      textShadow: '0 1px 2px rgba(0,0,0,0.25)',
                    }}
                  >
                    {fmtShort(day.revenue)}
                  </Typography>
                )}
              </Box>

              {/* Date label */}
              <Box sx={{ textAlign: 'center', mt: 0.75, lineHeight: 1.2 }}>
                <Typography sx={{ fontSize: '0.62rem', fontWeight: 700, color: PALETTE.stone[700], display: 'block' }}>
                  {dayNum}
                </Typography>
                <Typography sx={{ fontSize: '0.56rem', color: PALETTE.stone[400], display: 'block' }}>
                  {monthAbbr}
                </Typography>
              </Box>
            </Box>
          </Tooltip>
        )
      })}
    </Box>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  data: RevenueReportResponse
}

export default function RevenueReport({ data }: Props) {
  const maxPayment = Math.max(...data.by_payment_method.map((m) => m.amount), 1)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

      {/* KPI cards */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            icon={<TrendingUpRounded />}
            label="Выручка"
            value={fmt(data.total_revenue)}
            color={BRAND.primary}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            icon={<ReceiptRounded />}
            label="Заказ-нарядов"
            value={String(data.total_orders)}
            color={PALETTE.green.main}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            icon={<ShoppingCartRounded />}
            label="Средний чек"
            value={fmt(data.avg_check)}
            color={PALETTE.amber.main}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* ── Vertical bar chart ── */}
        <Grid item xs={12} md={7}>
          <Paper elevation={0} sx={{ p: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 2.5 }}>
              Динамика по дням
            </Typography>
            <DailyBarChart items={data.by_day} />
          </Paper>
        </Grid>

        {/* ── Payment methods ── */}
        <Grid item xs={12} md={5}>
          <Paper elevation={0} sx={{ p: 3, height: '100%' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 2.5 }}>
              Методы оплаты
            </Typography>
            {data.by_payment_method.length === 0 ? (
              <Typography variant="body2" color="text.secondary">Нет данных</Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                {data.by_payment_method.map((method) => {
                  const pct = maxPayment > 0 ? (method.amount / maxPayment) * 100 : 0
                  return (
                    <Box key={method.method}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.75 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <CreditCardRounded fontSize="small" sx={{ color: BRAND.primary }} />
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {method.method_label}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                          <Typography variant="body2" sx={{ fontWeight: 800 }}>
                            {fmt(method.amount)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {method.payments_count} оплат · {((method.amount / (data.total_revenue || 1)) * 100).toFixed(1)}%
                          </Typography>
                        </Box>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={pct}
                        sx={{
                          height: 5,
                          borderRadius: 3,
                          bgcolor: alpha(BRAND.primary, 0.1),
                          '& .MuiLinearProgress-bar': {
                            borderRadius: 3,
                            background: BRAND.gradient,
                          },
                        }}
                      />
                    </Box>
                  )
                })}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* ── Work categories ── */}
      <Paper elevation={0} sx={{ overflow: 'hidden' }}>
        <Box sx={{ p: 3, pb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
            Выручка по категориям работ
          </Typography>
        </Box>
        {data.by_work_category.length === 0 ? (
          <Box sx={{ px: 3, pb: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет данных за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Категория</TableCell>
                  <TableCell align="right">Заказов</TableCell>
                  <TableCell align="right">Выручка</TableCell>
                  <TableCell align="right">Доля</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.by_work_category.map((cat) => {
                  const pct = data.total_revenue > 0
                    ? ((cat.revenue / data.total_revenue) * 100).toFixed(1)
                    : '0.0'
                  return (
                    <TableRow key={cat.category} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {cat.category_label}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={cat.orders_count}
                          size="small"
                          sx={{
                            fontWeight: 700,
                            bgcolor: alpha(BRAND.primary, 0.08),
                            color: BRAND.primary,
                          }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 800 }}>
                          {fmt(cat.revenue)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                          {pct}%
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  )
}
