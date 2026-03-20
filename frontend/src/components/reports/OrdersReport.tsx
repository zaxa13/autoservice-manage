import { useState } from 'react'
import {
  Box, Paper, Typography, Divider, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid, alpha,
  MenuItem, Select, FormControl, InputLabel, Link,
} from '@mui/material'
import { AssignmentRounded, AccountBalanceWalletRounded } from '@mui/icons-material'
import { OrdersReportResponse } from '../../types'
import { useReportsStore } from '../../store/reportsStore'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

const STATUS_COLORS: Record<string, string> = {
  new: '#64748B',
  estimation: '#8B5CF6',
  in_progress: '#F59E0B',
  ready_for_payment: '#3B82F6',
  paid: '#10B981',
  completed: '#4F46E5',
  cancelled: '#EF4444',
}

const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'new', label: 'Новый' },
  { value: 'estimation', label: 'Проценка' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'ready_for_payment', label: 'Готов к оплате' },
  { value: 'paid', label: 'Оплачен' },
  { value: 'completed', label: 'Завершён' },
  { value: 'cancelled', label: 'Отменён' },
]

interface Props {
  data: OrdersReportResponse
}

export default function OrdersReport({ data }: Props) {
  const { ordersStatusFilter, setOrdersStatusFilter, fetchReport } = useReportsStore()

  const handleStatusChange = (value: string) => {
    setOrdersStatusFilter(value)
    fetchReport()
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Summary cards */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
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
                bgcolor: alpha('#4F46E5', 0.12),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#4F46E5',
                flexShrink: 0,
              }}
            >
              <AssignmentRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Заказов
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.total_count}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
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
                bgcolor: alpha('#10B981', 0.12),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#10B981',
                flexShrink: 0,
              }}
            >
              <AccountBalanceWalletRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Общая сумма
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.total_amount)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
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
                bgcolor: alpha('#F59E0B', 0.12),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#F59E0B',
                flexShrink: 0,
              }}
            >
              <AccountBalanceWalletRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Оплачено
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.total_paid)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Status breakdown */}
      {data.by_status.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {data.by_status.map((s) => (
            <Chip
              key={s.status}
              label={`${s.status_label}: ${s.count}`}
              size="small"
              sx={{
                fontWeight: 700,
                bgcolor: alpha(STATUS_COLORS[s.status] || '#64748B', 0.12),
                color: STATUS_COLORS[s.status] || '#64748B',
              }}
            />
          ))}
        </Box>
      )}

      {/* Filter + table */}
      <Paper
        elevation={0}
        sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: '16px', overflow: 'hidden' }}
      >
        <Box sx={{ p: 3, pb: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Список заказ-нарядов ({data.total_count})
          </Typography>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Статус</InputLabel>
            <Select
              value={ordersStatusFilter}
              label="Статус"
              onChange={(e) => handleStatusChange(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        <Divider sx={{ borderStyle: 'dashed' }} />
        {data.orders.length === 0 ? (
          <Box sx={{ p: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет заказ-нарядов за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer sx={{ maxHeight: 520 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>Номер</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Статус</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Клиент</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Автомобиль</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Механик</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Дата</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Работы
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Запчасти
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Итого
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Оплачено
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.orders.map((o) => (
                  <TableRow key={o.id} hover>
                    <TableCell>
                      <Link
                        component="button"
                        underline="hover"
                        onClick={() => window.open(`/orders?open=${o.id}`, '_blank')}
                        sx={{ fontWeight: 700, fontFamily: 'monospace', fontSize: '0.875rem', cursor: 'pointer' }}
                      >
                        {o.number}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={o.status_label}
                        size="small"
                        sx={{
                          fontWeight: 700,
                          bgcolor: alpha(STATUS_COLORS[o.status] || '#64748B', 0.12),
                          color: STATUS_COLORS[o.status] || '#64748B',
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {o.customer_name || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {o.vehicle_info || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {o.mechanic_name || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                        {new Date(o.created_at).toLocaleDateString('ru-RU')}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">{fmt(o.works_total)}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">{fmt(o.parts_total)}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        {fmt(o.total_amount)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color: o.paid_amount >= o.total_amount ? '#10B981' : 'text.primary',
                        }}
                      >
                        {fmt(o.paid_amount)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

    </Box>
  )
}
