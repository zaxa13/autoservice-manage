import React from 'react'
import {
  Box, Grid, Paper, Typography, Divider, LinearProgress,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, alpha,
} from '@mui/material'
import {
  TrendingUpRounded,
  ReceiptRounded,
  ShoppingCartRounded,
  CreditCardRounded,
} from '@mui/icons-material'
import { RevenueReportResponse } from '../../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        border: '1px dashed',
        borderColor: 'divider',
        borderRadius: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: 2,
      }}
    >
      <Box
        sx={{
          width: 48,
          height: 48,
          borderRadius: '12px',
          bgcolor: alpha(color, 0.12),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color,
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
          {label}
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
          {value}
        </Typography>
      </Box>
    </Paper>
  )
}

interface Props {
  data: RevenueReportResponse
}

export default function RevenueReport({ data }: Props) {
  const maxRevenue = Math.max(...data.by_day.map((d) => d.revenue), 1)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* KPI cards */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            icon={<TrendingUpRounded />}
            label="Выручка"
            value={fmt(data.total_revenue)}
            color="#4F46E5"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            icon={<ReceiptRounded />}
            label="Заказ-нарядов"
            value={String(data.total_orders)}
            color="#10B981"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            icon={<ShoppingCartRounded />}
            label="Средний чек"
            value={fmt(data.avg_check)}
            color="#F59E0B"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Revenue by day chart (bar-style) */}
        <Grid item xs={12} md={7}>
          <Paper
            elevation={0}
            sx={{ p: 3, border: '1px dashed', borderColor: 'divider', borderRadius: '16px' }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
              Динамика по дням
            </Typography>
            {data.by_day.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Нет данных за выбранный период
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {data.by_day.map((day) => (
                  <Box key={day.date} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Typography
                      variant="caption"
                      sx={{ width: 80, flexShrink: 0, color: 'text.secondary', fontWeight: 600 }}
                    >
                      {new Date(day.date + 'T00:00:00').toLocaleDateString('ru-RU', {
                        day: 'numeric',
                        month: 'short',
                      })}
                    </Typography>
                    <Box sx={{ flexGrow: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={(day.revenue / maxRevenue) * 100}
                        sx={{
                          height: 10,
                          borderRadius: 5,
                          bgcolor: alpha('#4F46E5', 0.1),
                          '& .MuiLinearProgress-bar': { borderRadius: 5, bgcolor: '#4F46E5' },
                        }}
                      />
                    </Box>
                    <Typography
                      variant="caption"
                      sx={{ width: 90, textAlign: 'right', flexShrink: 0, fontWeight: 700 }}
                    >
                      {fmt(day.revenue)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Payment methods */}
        <Grid item xs={12} md={5}>
          <Paper
            elevation={0}
            sx={{ p: 3, border: '1px dashed', borderColor: 'divider', borderRadius: '16px', height: '100%' }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 2 }}>
              Методы оплаты
            </Typography>
            {data.by_payment_method.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Нет данных
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {data.by_payment_method.map((method) => {
                  const pct = data.total_revenue > 0 ? (method.amount / data.total_revenue) * 100 : 0
                  return (
                    <Box key={method.method}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <CreditCardRounded fontSize="small" color="action" />
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {method.method_label}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                          <Typography variant="body2" sx={{ fontWeight: 800 }}>
                            {fmt(method.amount)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {method.payments_count} оплат · {pct.toFixed(1)}%
                          </Typography>
                        </Box>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={pct}
                        sx={{
                          height: 6,
                          borderRadius: 3,
                          bgcolor: alpha('#10B981', 0.1),
                          '& .MuiLinearProgress-bar': { borderRadius: 3, bgcolor: '#10B981' },
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

      {/* Work categories */}
      <Paper
        elevation={0}
        sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: '16px', overflow: 'hidden' }}
      >
        <Box sx={{ p: 3, pb: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Выручка по категориям работ
          </Typography>
        </Box>
        <Divider sx={{ borderStyle: 'dashed' }} />
        {data.by_work_category.length === 0 ? (
          <Box sx={{ p: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет данных за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>Категория</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Заказов
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Выручка
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Доля
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.by_work_category.map((cat) => {
                  const pct =
                    data.total_revenue > 0
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
                          sx={{ fontWeight: 700, bgcolor: alpha('#4F46E5', 0.08), color: '#4F46E5' }}
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
