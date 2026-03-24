import {
  Box, Paper, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid, alpha,
  MenuItem, Select, FormControl, InputLabel, Link,
} from '@mui/material'
import { AssignmentRounded, AccountBalanceWalletRounded } from '@mui/icons-material'
import { OrdersReportResponse } from '../../types'
import { useReportsStore } from '../../store/reportsStore'
import { BRAND, PALETTE, FONT, iconBoxSx, overlineSx } from '../../design-tokens'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

const STATUS_COLORS = {
  new:               PALETTE.slate[500],
  estimation:        PALETTE.blue.main,
  in_progress:       PALETTE.amber.main,
  ready_for_payment: PALETTE.blue.main,
  paid:              PALETTE.green.main,
  completed:         BRAND.primary,
  cancelled:         PALETTE.red.main,
} as const satisfies Record<string, string>

const STATUS_OPTIONS = [
  { value: '',                  label: 'Все статусы' },
  { value: 'new',               label: 'Новый' },
  { value: 'estimation',        label: 'Проценка' },
  { value: 'in_progress',       label: 'В работе' },
  { value: 'ready_for_payment', label: 'Готов к оплате' },
  { value: 'paid',              label: 'Оплачен' },
  { value: 'completed',         label: 'Завершён' },
  { value: 'cancelled',         label: 'Отменён' },
] as const

interface Props {
  data: OrdersReportResponse
}

export default function OrdersReport({ data }: Props) {
  const { ordersStatusFilter, setOrdersStatusFilter, fetchReport } = useReportsStore()

  const handleStatusChange = (value: string) => {
    setOrdersStatusFilter(value)
    fetchReport()
  }

  const statusColor = (status: string): string =>
    STATUS_COLORS[status as keyof typeof STATUS_COLORS] ?? PALETTE.slate[500]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

      {/* ── Summary cards ── */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(BRAND.primary)}><AssignmentRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Заказов</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>{data.total_count}</Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.green.main)}><AccountBalanceWalletRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Общая сумма</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>{fmt(data.total_amount)}</Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.amber.main)}><AccountBalanceWalletRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Оплачено</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>{fmt(data.total_paid)}</Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* ── Status breakdown chips ── */}
      {data.by_status.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {data.by_status.map((s) => (
            <Chip
              key={s.status}
              label={`${s.status_label}: ${s.count}`}
              size="small"
              sx={{
                fontWeight: 700,
                bgcolor: alpha(statusColor(s.status), 0.1),
                color: statusColor(s.status),
              }}
            />
          ))}
        </Box>
      )}

      {/* ── Filter + table ── */}
      <Paper elevation={0} sx={{ overflow: 'hidden' }}>
        <Box sx={{
          p: 3, pb: 1.5,
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', flexWrap: 'wrap', gap: 2,
        }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
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
                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {data.orders.length === 0 ? (
          <Box sx={{ px: 3, pb: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет заказ-нарядов за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer sx={{ maxHeight: 520 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Номер</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>Клиент</TableCell>
                  <TableCell>Автомобиль</TableCell>
                  <TableCell>Механик</TableCell>
                  <TableCell>Дата</TableCell>
                  <TableCell align="right">Работы</TableCell>
                  <TableCell align="right">Запчасти</TableCell>
                  <TableCell align="right">Итого</TableCell>
                  <TableCell align="right">Оплачено</TableCell>
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
                        sx={{
                          fontWeight: 700,
                          fontFamily: FONT.mono,
                          fontSize: '0.8rem',
                          color: BRAND.primary,
                          cursor: 'pointer',
                        }}
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
                          bgcolor: alpha(statusColor(o.status), 0.1),
                          color: statusColor(o.status),
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
                          color: o.paid_amount >= o.total_amount ? PALETTE.green.main : 'text.primary',
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
