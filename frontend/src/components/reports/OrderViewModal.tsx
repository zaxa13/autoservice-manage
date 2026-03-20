import { useState, useEffect } from 'react'
import {
  Dialog, AppBar, Toolbar, IconButton, Typography,
  Box, Stack, Paper, Grid, Chip, Divider, CircularProgress,
  Table, TableBody, TableCell, TableHead, TableRow, alpha,
} from '@mui/material'
import {
  ArrowBackRounded,
  DirectionsCarFilledRounded,
  BuildCircleRounded,
  ShoppingBagRounded,
  PaymentRounded,
  PersonRounded,
  PhoneRounded,
  EngineeringRounded,
  SpeedRounded,
  CommentRounded,
  EditRounded,
  LocalAtmRounded,
  CreditCardRounded,
  AccountBalanceWalletRounded,
} from '@mui/icons-material'
import { OrderDetail } from '../../types'
import api from '../../services/api'

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

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  estimation: 'Проценка',
  in_progress: 'В работе',
  ready_for_payment: 'Готов к оплате',
  paid: 'Оплачен',
  completed: 'Завершён',
  cancelled: 'Отменён',
}

const METHOD_ICONS: Record<string, React.ReactNode> = {
  cash: <LocalAtmRounded fontSize="small" />,
  card: <CreditCardRounded fontSize="small" />,
  yookassa: <AccountBalanceWalletRounded fontSize="small" />,
}

const METHOD_LABELS: Record<string, string> = {
  cash: 'Наличные',
  card: 'Карта',
  yookassa: 'ЮKassa',
}

interface Payment {
  id: number
  amount: number
  payment_method: string
  status: string
  created_at: string
}

interface Props {
  orderId: number | null
  open: boolean
  onClose: () => void
}

export default function OrderViewModal({ orderId, open, onClose }: Props) {
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !orderId) return
    setLoading(true)
    setOrder(null)
    setPayments([])
    Promise.all([
      api.get<OrderDetail>(`/orders/${orderId}`),
      api.get<Payment[]>(`/orders/${orderId}/payments`),
    ])
      .then(([orderRes, paymentsRes]) => {
        setOrder(orderRes.data)
        setPayments(paymentsRes.data || [])
      })
      .finally(() => setLoading(false))
  }, [open, orderId])

  const status = order ? String((order as any).status?.value ?? order.status) : ''
  const statusLabel = STATUS_LABELS[status] ?? status
  const statusColor = STATUS_COLORS[status] ?? '#64748B'

  const worksTotal = order?.order_works?.reduce((s, w) => s + Number(w.total), 0) ?? 0
  const partsTotal = order?.order_parts?.reduce((s, p) => s + Number(p.total), 0) ?? 0
  const succeededPayments = payments.filter((p) => p.status === 'succeeded')
  const paidTotal = succeededPayments.reduce((s, p) => s + Number(p.amount), 0)

  return (
    <Dialog open={open} onClose={onClose} fullScreen PaperProps={{ sx: { bgcolor: '#F8FAFC' } }}>
      <AppBar
        sx={{
          position: 'sticky',
          bgcolor: '#fff',
          color: 'text.primary',
          boxShadow: 'none',
          borderBottom: '1px solid #E2E8F0',
          zIndex: 1100,
        }}
      >
        <Toolbar>
          <IconButton edge="start" onClick={onClose} sx={{ mr: 2 }}>
            <ArrowBackRounded />
          </IconButton>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              {order ? `Заказ-наряд ${order.number}` : 'Заказ-наряд'}
            </Typography>
            {order && (
              <Chip
                label={statusLabel}
                size="small"
                sx={{
                  fontWeight: 700,
                  bgcolor: alpha(statusColor, 0.12),
                  color: statusColor,
                }}
              />
            )}
          </Stack>
        </Toolbar>
      </AppBar>

      <Box sx={{ p: 3 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
            <CircularProgress />
          </Box>
        ) : order ? (
          <Stack spacing={2} sx={{ maxWidth: 1200, mx: 'auto' }}>

            {/* Vehicle + customer */}
            <Paper sx={{ p: 3, borderRadius: 3, border: '1px solid #E2E8F0' }}>
              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: '12px',
                    bgcolor: alpha('#4F46E5', 0.1),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'primary.main',
                    flexShrink: 0,
                  }}
                >
                  <DirectionsCarFilledRounded />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    {order.vehicle?.brand?.name} {order.vehicle?.model?.name}
                  </Typography>
                  <Stack direction="row" flexWrap="wrap" gap={2} sx={{ mt: 0.5 }}>
                    {order.vehicle?.license_plate && (
                      <Typography variant="body2" color="text.secondary">
                        {order.vehicle.license_plate}
                      </Typography>
                    )}
                    {order.vehicle?.vin && (
                      <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                        VIN: {order.vehicle.vin}
                      </Typography>
                    )}
                    {order.vehicle?.mileage != null && (
                      <Stack direction="row" alignItems="center" spacing={0.5}>
                        <SpeedRounded sx={{ fontSize: 14, color: 'text.secondary' }} />
                        <Typography variant="body2" color="text.secondary">
                          {order.vehicle.mileage.toLocaleString('ru-RU')} км
                        </Typography>
                      </Stack>
                    )}
                  </Stack>
                  {order.vehicle?.customer && (
                    <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                      <Stack direction="row" alignItems="center" spacing={0.5}>
                        <PersonRounded sx={{ fontSize: 15, color: 'text.secondary' }} />
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {order.vehicle.customer.full_name}
                        </Typography>
                      </Stack>
                      {order.vehicle.customer.phone && (
                        <Stack direction="row" alignItems="center" spacing={0.5}>
                          <PhoneRounded sx={{ fontSize: 15, color: 'text.secondary' }} />
                          <Typography
                            component="a"
                            href={`tel:${order.vehicle.customer.phone}`}
                            variant="body2"
                            sx={{ color: 'primary.main', fontWeight: 600, textDecoration: 'none' }}
                          >
                            {order.vehicle.customer.phone}
                          </Typography>
                        </Stack>
                      )}
                    </Stack>
                  )}
                </Box>
                <Box sx={{ textAlign: 'right', flexShrink: 0 }}>
                  {order.mechanic && (
                    <Stack direction="row" alignItems="center" spacing={1} justifyContent="flex-end">
                      <EngineeringRounded fontSize="small" color="action" />
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {order.mechanic.full_name}
                      </Typography>
                    </Stack>
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {new Date(order.created_at).toLocaleDateString('ru-RU', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}
                  </Typography>
                  {order.completed_at && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Завершён: {new Date(order.completed_at).toLocaleDateString('ru-RU')}
                    </Typography>
                  )}
                </Box>
              </Stack>
            </Paper>

            <Grid container spacing={2}>
              {/* Works */}
              <Grid item xs={12} md={6}>
                <Paper sx={{ borderRadius: 3, border: '1px solid #E2E8F0', overflow: 'hidden', height: '100%' }}>
                  <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <BuildCircleRounded fontSize="small" color="primary" />
                    <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                      Работы
                    </Typography>
                  </Box>
                  <Divider sx={{ borderStyle: 'dashed' }} />
                  {order.order_works?.length === 0 ? (
                    <Box sx={{ p: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Нет работ
                      </Typography>
                    </Box>
                  ) : (
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 700 }}>Наименование</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>Кол-во</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Цена</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Итого</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {order.order_works?.map((w) => (
                          <TableRow key={w.id}>
                            <TableCell>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(w as any).work_name || w.work?.name || '—'}
                              </Typography>
                            </TableCell>
                            <TableCell align="center">{w.quantity}</TableCell>
                            <TableCell align="right">{fmt(Number(w.price))}</TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" sx={{ fontWeight: 800 }}>
                                {fmt(Number(w.total))}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow>
                          <TableCell colSpan={3} sx={{ fontWeight: 800, borderTop: '2px solid #E2E8F0' }}>
                            Итого работы
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 900, borderTop: '2px solid #E2E8F0', color: 'primary.main' }}>
                            {fmt(worksTotal)}
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  )}
                </Paper>
              </Grid>

              {/* Parts */}
              <Grid item xs={12} md={6}>
                <Paper sx={{ borderRadius: 3, border: '1px solid #E2E8F0', overflow: 'hidden', height: '100%' }}>
                  <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ShoppingBagRounded fontSize="small" color="primary" />
                    <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                      Запчасти
                    </Typography>
                  </Box>
                  <Divider sx={{ borderStyle: 'dashed' }} />
                  {order.order_parts?.length === 0 ? (
                    <Box sx={{ p: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Нет запчастей
                      </Typography>
                    </Box>
                  ) : (
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 700 }}>Наименование</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>Кол-во</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Цена</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Итого</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {order.order_parts?.map((p) => (
                          <TableRow key={p.id}>
                            <TableCell>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {(p as any).part_name || p.part?.name || '—'}
                              </Typography>
                              {((p as any).article || p.part?.part_number) && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                                  {(p as any).article || p.part?.part_number}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell align="center">{p.quantity}</TableCell>
                            <TableCell align="right">{fmt(Number(p.price))}</TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" sx={{ fontWeight: 800 }}>
                                {fmt(Number(p.total))}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow>
                          <TableCell colSpan={3} sx={{ fontWeight: 800, borderTop: '2px solid #E2E8F0' }}>
                            Итого запчасти
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 900, borderTop: '2px solid #E2E8F0', color: 'primary.main' }}>
                            {fmt(partsTotal)}
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  )}
                </Paper>
              </Grid>
            </Grid>

            {/* Totals + payments */}
            <Paper sx={{ p: 3, borderRadius: 3, border: '2px solid', borderColor: 'primary.main' }}>
              <Grid container spacing={3} alignItems="center">
                <Grid item xs={12} sm={6}>
                  <Stack spacing={1}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Работы</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{fmt(worksTotal)}</Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Запчасти</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{fmt(partsTotal)}</Typography>
                    </Stack>
                    <Divider sx={{ borderStyle: 'dashed' }} />
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Итого</Typography>
                      <Typography variant="subtitle1" sx={{ fontWeight: 900, color: 'primary.main' }}>
                        {fmt(Number(order.total_amount))}
                      </Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Оплачено</Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 800,
                          color: paidTotal >= Number(order.total_amount) && Number(order.total_amount) > 0
                            ? '#10B981'
                            : 'text.primary',
                        }}
                      >
                        {fmt(paidTotal)}
                      </Typography>
                    </Stack>
                  </Stack>
                </Grid>

                {/* Payment list */}
                <Grid item xs={12} sm={6}>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <PaymentRounded fontSize="small" color="action" />
                    <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                      Платежи
                    </Typography>
                  </Stack>
                  {succeededPayments.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      Нет проведённых платежей
                    </Typography>
                  ) : (
                    <Stack spacing={0.5}>
                      {succeededPayments.map((p) => (
                        <Stack key={p.id} direction="row" alignItems="center" spacing={1}>
                          <Box sx={{ color: 'text.secondary' }}>{METHOD_ICONS[p.payment_method]}</Box>
                          <Typography variant="body2" sx={{ flex: 1 }}>
                            {METHOD_LABELS[p.payment_method] ?? p.payment_method}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(p.created_at).toLocaleDateString('ru-RU')}
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 800 }}>
                            {fmt(Number(p.amount))}
                          </Typography>
                        </Stack>
                      ))}
                    </Stack>
                  )}
                </Grid>
              </Grid>
            </Paper>

            {/* Comments / recommendations */}
            {(order.recommendations || order.comments) && (
              <Grid container spacing={2}>
                {order.recommendations && (
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0' }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                        <CommentRounded fontSize="small" color="action" />
                        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                          Рекомендации
                        </Typography>
                      </Stack>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {order.recommendations}
                      </Typography>
                    </Paper>
                  </Grid>
                )}
                {order.comments && (
                  <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0' }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                        <EditRounded fontSize="small" color="action" />
                        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                          Комментарии
                        </Typography>
                      </Stack>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {order.comments}
                      </Typography>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            )}
          </Stack>
        ) : null}
      </Box>
    </Dialog>
  )
}
