import React, { useState, useRef } from 'react'
import {
  Box, Typography, TextField, InputAdornment, IconButton, CircularProgress,
  Card, CardContent, Stack, Chip, Divider, Alert, Button,
  Dialog, DialogTitle, DialogContent, DialogActions,
  Tooltip, alpha, Collapse, MenuItem, Select, FormControl, InputLabel,
} from '@mui/material'
import {
  SearchRounded,
  DirectionsCarRounded,
  HistoryRounded,
  PersonRounded,
  PhoneRounded,
  CloseRounded,
  ExpandMoreRounded,
  ExpandLessRounded,
  BuildRounded,
  CheckCircleOutlineRounded,
  EditRounded,
  SpeedRounded,
} from '@mui/icons-material'
import api from '../services/api'
import { Vehicle, OrderDetail, BrandRef, ModelRef } from '../types'

const ORDER_STATUS_LABELS: Record<string, { label: string; color: 'default' | 'primary' | 'warning' | 'info' | 'success' | 'error' }> = {
  new: { label: 'Новый', color: 'default' },
  estimation: { label: 'Проценка', color: 'info' },
  in_progress: { label: 'В работе', color: 'warning' },
  ready_for_payment: { label: 'К оплате', color: 'primary' },
  paid: { label: 'Оплачен', color: 'success' },
  completed: { label: 'Завершён', color: 'success' },
  cancelled: { label: 'Отменён', color: 'error' },
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(amount)
}

// ── Order card ─────────────────────────────────────────────────────────────────

function OrderCard({ order }: { order: OrderDetail }) {
  const [expanded, setExpanded] = useState(false)
  const st = ORDER_STATUS_LABELS[order.status] ?? { label: order.status, color: 'default' as const }

  return (
    <Box
      sx={{
        border: '1px solid #E2E8F0',
        borderLeft: order.status === 'completed'
          ? '3px solid #10B981'
          : order.status === 'cancelled'
            ? '3px solid #EF4444'
            : '3px solid #E2E8F0',
        borderRadius: '10px',
        overflow: 'hidden',
        mb: 1.5,
        bgcolor: '#fff',
      }}
    >
      <Box
        sx={{
          display: 'flex', alignItems: 'center', gap: 2, px: 2, py: 1.5,
          cursor: 'pointer',
          '&:hover': { bgcolor: '#F8FAFC' },
          transition: 'background 0.15s',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ minWidth: 110 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', color: '#475569', fontSize: '0.7rem', letterSpacing: '0.04em' }}>
            № {order.number}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {formatDate(order.created_at)}
          </Typography>
        </Box>

        <Chip
          label={st.label}
          color={st.color}
          size="small"
          sx={{ fontWeight: 700, minWidth: 84 }}
        />

        <Box sx={{ flexGrow: 1 }}>
          {order.mechanic && (
            <Typography variant="caption" color="text.secondary">
              {order.mechanic.full_name}
            </Typography>
          )}
        </Box>

        <Typography variant="subtitle2" sx={{ fontWeight: 800, color: '#0F172A', minWidth: 90, textAlign: 'right' }}>
          {formatCurrency(Number(order.total_amount))}
        </Typography>

        <IconButton size="small" sx={{ color: 'text.disabled' }}>
          {expanded ? <ExpandLessRounded fontSize="small" /> : <ExpandMoreRounded fontSize="small" />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ px: 2.5, pb: 2.5, pt: 0.5 }}>
          <Divider sx={{ mb: 2 }} />

          {order.order_works && order.order_works.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="overline" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1, color: '#64748B' }}>
                <BuildRounded fontSize="inherit" /> Работы
              </Typography>
              <Stack spacing={0.5}>
                {order.order_works.map((w) => (
                  <Box key={w.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" color="text.primary">
                      {w.work?.name || '—'}
                      {w.quantity > 1 && (
                        <Typography component="span" variant="caption" color="text.secondary"> × {w.quantity}</Typography>
                      )}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700, ml: 2, whiteSpace: 'nowrap' }}>
                      {formatCurrency(Number(w.total))}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </Box>
          )}

          {order.order_parts && order.order_parts.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="overline" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1, color: '#64748B' }}>
                <CheckCircleOutlineRounded fontSize="inherit" /> Запчасти
              </Typography>
              <Stack spacing={0.5}>
                {order.order_parts.map((p) => (
                  <Box key={p.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                    <Box>
                      <Typography variant="body2">
                        {p.part?.name || '—'}
                        {p.quantity > 1 && (
                          <Typography component="span" variant="caption" color="text.secondary"> × {p.quantity}</Typography>
                        )}
                      </Typography>
                      {p.part?.part_number && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                          {p.part.part_number}
                        </Typography>
                      )}
                    </Box>
                    <Typography variant="body2" sx={{ fontWeight: 700, ml: 2, whiteSpace: 'nowrap' }}>
                      {formatCurrency(Number(p.total))}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </Box>
          )}

          {order.recommendations && (
            <Box sx={{ mt: 1.5, p: 1.5, bgcolor: '#FFFBEB', borderRadius: '8px', border: '1px solid #FDE68A' }}>
              <Typography variant="overline" sx={{ color: '#92400E', display: 'block', mb: 0.5 }}>
                Рекомендации
              </Typography>
              <Typography variant="body2" color="text.secondary">{order.recommendations}</Typography>
            </Box>
          )}

          <Box sx={{
            display: 'flex', justifyContent: 'flex-end', mt: 2, pt: 1.5,
            borderTop: '1px solid #F1F5F9', gap: 3,
          }}>
            <Typography variant="body2" color="text.secondary">
              Оплачено: <strong>{formatCurrency(Number(order.paid_amount))}</strong>
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>
              Итого: {formatCurrency(Number(order.total_amount))}
            </Typography>
          </Box>
        </Box>
      </Collapse>
    </Box>
  )
}

// ── Vehicle history dialog ─────────────────────────────────────────────────────

function VehicleHistoryDialog({ vehicle, open, onClose }: {
  vehicle: Vehicle | null
  open: boolean
  onClose: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<OrderDetail[]>([])
  const [error, setError] = useState('')

  React.useEffect(() => {
    if (!open || !vehicle) return
    setLoading(true)
    setError('')
    api.get(`/vehicles/${vehicle.id}/history`)
      .then((res) => setHistory(res.data))
      .catch(() => setError('Не удалось загрузить историю'))
      .finally(() => setLoading(false))
  }, [open, vehicle])

  if (!vehicle) return null

  const vehicleLabel = [vehicle.brand?.name, vehicle.model?.name, vehicle.year, vehicle.license_plate]
    .filter(Boolean).join(' ')

  const totalSpent = history.reduce((sum, o) => sum + Number(o.total_amount), 0)

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { borderRadius: '16px', maxHeight: '90vh' } }}
    >
      <DialogTitle sx={{ pb: 1.5, borderBottom: '1px solid #F1F5F9' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{
              width: 40, height: 40,
              background: 'linear-gradient(135deg, #2DD4BF 0%, #0D9488 100%)',
              borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <HistoryRounded sx={{ color: '#fff', fontSize: 20 }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                История обслуживания
              </Typography>
              <Typography variant="caption" color="text.secondary">{vehicleLabel}</Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small"><CloseRounded /></IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pt: 2 }}>
        {vehicle.customer && (
          <Box sx={{
            p: 1.5, mb: 2.5,
            border: '1px solid #E2E8F0',
            borderRadius: '10px',
            display: 'flex', alignItems: 'center', gap: 2,
            bgcolor: '#F8FAFC',
          }}>
            <Box sx={{
              width: 36, height: 36, borderRadius: '50%',
              bgcolor: alpha('#0D9488', 0.1),
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <PersonRounded sx={{ color: '#0D9488', fontSize: 18 }} />
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{vehicle.customer.full_name}</Typography>
              <Typography variant="caption" color="text.secondary">{vehicle.customer.phone}</Typography>
            </Box>
            {vehicle.vin && (
              <Box sx={{ ml: 'auto', textAlign: 'right' }}>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ letterSpacing: '0.04em', textTransform: 'uppercase', fontSize: '0.65rem' }}>VIN</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, fontFamily: 'monospace', letterSpacing: '0.05em' }}>{vehicle.vin}</Typography>
              </Box>
            )}
          </Box>
        )}

        {!loading && history.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1.5, mb: 2.5 }}>
            {[
              { value: history.length, label: 'заказ-нарядов', color: '#0D9488' },
              { value: formatCurrency(totalSpent), label: 'суммарно', color: '#10B981' },
              ...(vehicle.mileage ? [{ value: `${vehicle.mileage.toLocaleString('ru-RU')} км`, label: 'пробег', color: '#F59E0B' }] : []),
            ].map((stat, i) => (
              <Box key={i} sx={{
                flex: 1, p: 1.5,
                border: '1px solid #E2E8F0',
                borderTop: `3px solid ${stat.color}`,
                borderRadius: '10px',
                textAlign: 'center',
                bgcolor: '#fff',
              }}>
                <Typography variant="h5" sx={{ fontWeight: 800, color: stat.color, lineHeight: 1.2 }}>{stat.value}</Typography>
                <Typography variant="caption" color="text.secondary">{stat.label}</Typography>
              </Box>
            ))}
          </Box>
        )}

        {loading && (
          <Box sx={{ textAlign: 'center', py: 6 }}><CircularProgress /></Box>
        )}
        {error && <Alert severity="error">{error}</Alert>}
        {!loading && !error && history.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <HistoryRounded sx={{ fontSize: 48, color: '#CBD5E1', mb: 1.5 }} />
            <Typography color="text.secondary" fontWeight={600}>Заказ-нарядов пока нет</Typography>
          </Box>
        )}

        {!loading && history.map((order) => (
          <OrderCard key={order.id} order={order} />
        ))}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5, borderTop: '1px solid #F1F5F9' }}>
        <Button onClick={onClose} variant="outlined">Закрыть</Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Vehicle edit dialog ────────────────────────────────────────────────────────

function VehicleEditDialog({ vehicle, open, onClose, onSaved }: {
  vehicle: Vehicle | null
  open: boolean
  onClose: () => void
  onSaved: (updated: Vehicle) => void
}) {
  const [brands, setBrands] = useState<BrandRef[]>([])
  const [models, setModels] = useState<ModelRef[]>([])
  const [form, setForm] = useState({ brand_id: 0, model_id: 0, year: '', mileage: '', vin: '', license_plate: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  React.useEffect(() => {
    if (!open || !vehicle) return
    setForm({
      brand_id: vehicle.brand_id,
      model_id: vehicle.model_id,
      year: vehicle.year ? String(vehicle.year) : '',
      mileage: vehicle.mileage ? String(vehicle.mileage) : '',
      vin: vehicle.vin || '',
      license_plate: vehicle.license_plate || '',
    })
    setError('')
    api.get('/vehicle-brands/').then((res) => setBrands(res.data.brands || []))
  }, [open, vehicle])

  React.useEffect(() => {
    if (!form.brand_id) return
    api.post('/vehicle-brands/models', { brand_id: form.brand_id })
      .then((res) => setModels(res.data.models || []))
  }, [form.brand_id])

  const handleSave = async () => {
    if (!vehicle) return
    setSaving(true)
    setError('')
    try {
      const res = await api.put(`/vehicles/${vehicle.id}`, {
        brand_id: form.brand_id,
        model_id: form.model_id,
        year: form.year ? Number(form.year) : null,
        mileage: form.mileage ? Number(form.mileage) : null,
        vin: form.vin || null,
        license_plate: form.license_plate || null,
        customer_id: vehicle.customer_id,
      })
      onSaved(res.data)
      onClose()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  if (!vehicle) return null

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pb: 1.5, borderBottom: '1px solid #F1F5F9' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{
              width: 40, height: 40,
              background: 'linear-gradient(135deg, #2DD4BF 0%, #0D9488 100%)',
              borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <EditRounded sx={{ color: '#fff', fontSize: 20 }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.2 }}>Редактировать автомобиль</Typography>
              <Typography variant="caption" color="text.secondary">
                {[vehicle.brand?.name, vehicle.model?.name, vehicle.license_plate].filter(Boolean).join(' · ')}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small"><CloseRounded /></IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pt: 2.5 }}>
        <Stack spacing={2.5}>
          {error && <Alert severity="error">{error}</Alert>}

          <FormControl fullWidth size="small">
            <InputLabel>Марка</InputLabel>
            <Select
              value={form.brand_id || ''}
              label="Марка"
              onChange={(e) => setForm((f) => ({ ...f, brand_id: Number(e.target.value), model_id: 0 }))}
            >
              {brands.map((b) => (
                <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small" disabled={!form.brand_id}>
            <InputLabel>Модель</InputLabel>
            <Select
              value={form.model_id || ''}
              label="Модель"
              onChange={(e) => setForm((f) => ({ ...f, model_id: Number(e.target.value) }))}
            >
              {models.map((m) => (
                <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField label="Год выпуска" size="small" fullWidth value={form.year}
              onChange={(e) => setForm((f) => ({ ...f, year: e.target.value }))}
              inputProps={{ maxLength: 4 }} />
            <TextField label="Пробег (км)" size="small" fullWidth value={form.mileage}
              onChange={(e) => setForm((f) => ({ ...f, mileage: e.target.value }))} />
          </Box>

          <TextField label="Госномер" size="small" fullWidth value={form.license_plate}
            onChange={(e) => setForm((f) => ({ ...f, license_plate: e.target.value.toUpperCase() }))}
            InputProps={{ sx: { fontFamily: 'monospace', letterSpacing: '0.08em' } }} />

          <TextField label="VIN" size="small" fullWidth value={form.vin}
            onChange={(e) => setForm((f) => ({ ...f, vin: e.target.value.toUpperCase() }))}
            InputProps={{ sx: { fontFamily: 'monospace', letterSpacing: '0.06em' } }}
            inputProps={{ maxLength: 17 }} />
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1, borderTop: '1px solid #F1F5F9' }}>
        <Button onClick={onClose} variant="outlined">Отмена</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || !form.brand_id || !form.model_id}
        >
          {saving ? <CircularProgress size={20} color="inherit" /> : 'Сохранить'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function VehiclesPage() {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<Vehicle[]>([])
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')
  const [historyVehicle, setHistoryVehicle] = useState<Vehicle | null>(null)
  const [editVehicle, setEditVehicle] = useState<Vehicle | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSearch = async (q?: string) => {
    const searchQuery = (q ?? inputValue).trim()
    if (searchQuery.length < 2) return
    setLoading(true)
    setError('')
    setSearched(true)
    try {
      const res = await api.get('/vehicles/search', { params: { q: searchQuery } })
      setResults(res.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка поиска')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <Box>
      {/* ── Page header ── */}
      <Box sx={{
        mb: 4,
        pb: 3,
        borderBottom: '1px solid #F1F5F9',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
      }}>
        <Box>
          <Typography variant="overline" sx={{ color: '#94A3B8', mb: 0.5, display: 'block' }}>
            База данных
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-0.03em', color: '#0F172A', lineHeight: 1 }}>
            Автомобили
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
            Поиск по номеру телефона, VIN или госномеру
          </Typography>
        </Box>
        <Box sx={{
          width: 44, height: 44,
          background: 'linear-gradient(135deg, #2DD4BF 0%, #0D9488 100%)',
          borderRadius: '12px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(79,70,229,0.3)',
        }}>
          <DirectionsCarRounded sx={{ color: '#fff', fontSize: 22 }} />
        </Box>
      </Box>

      {/* ── Search ── */}
      <Box sx={{
        display: 'flex',
        gap: 1.5,
        maxWidth: 680,
        mb: 3,
      }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          placeholder="А123ВС77 · +79001234567 · WBA..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          size="medium"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchRounded sx={{ color: '#94A3B8', fontSize: 22 }} />
              </InputAdornment>
            ),
            sx: {
              borderRadius: '10px',
              fontFamily: 'monospace',
              fontSize: '0.95rem',
              bgcolor: '#fff',
              letterSpacing: '0.03em',
            },
          }}
        />
        <Button
          variant="contained"
          onClick={() => handleSearch()}
          disabled={loading || inputValue.trim().length < 2}
          sx={{ borderRadius: '10px', fontWeight: 700, px: 3.5, minWidth: 110, whiteSpace: 'nowrap' }}
        >
          {loading ? <CircularProgress size={20} color="inherit" /> : 'Найти'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3, maxWidth: 680 }}>{error}</Alert>
      )}

      {/* ── Empty state ── */}
      {searched && !loading && results.length === 0 && !error && (
        <Box sx={{ textAlign: 'center', py: 10 }}>
          <Box sx={{
            width: 64, height: 64, borderRadius: '16px',
            bgcolor: '#F1F5F9',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            mb: 2,
          }}>
            <DirectionsCarRounded sx={{ fontSize: 32, color: '#CBD5E1' }} />
          </Box>
          <Typography variant="subtitle1" fontWeight={700} color="text.secondary">
            Автомобили не найдены
          </Typography>
          <Typography variant="body2" color="text.disabled" sx={{ mt: 0.5 }}>
            Попробуйте другой запрос
          </Typography>
        </Box>
      )}

      {/* ── Results ── */}
      {results.length > 0 && (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
            <Typography variant="overline" sx={{ color: '#64748B' }}>
              Найдено
            </Typography>
            <Chip
              label={results.length}
              size="small"
              sx={{
                bgcolor: '#0D9488',
                color: '#fff',
                fontWeight: 700,
                height: '20px',
                fontSize: '0.7rem',
              }}
            />
          </Box>

          <Stack spacing={1.5} sx={{ maxWidth: 760 }}>
            {results.map((vehicle) => (
              <Card
                key={vehicle.id}
                variant="outlined"
                sx={{
                  borderRadius: '12px',
                  borderLeft: '3px solid #0D9488',
                  transition: 'box-shadow 0.2s, border-color 0.2s',
                  '&:hover': {
                    boxShadow: '0 6px 20px rgba(0,0,0,0.08)',
                    borderLeftColor: '#2DD4BF',
                  },
                }}
              >
                <CardContent sx={{ '&:last-child': { pb: 2 }, p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>

                    {/* Car icon */}
                    <Box sx={{
                      width: 48, height: 48,
                      borderRadius: '10px',
                      bgcolor: alpha('#0D9488', 0.08),
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <DirectionsCarRounded sx={{ color: '#0D9488', fontSize: 22 }} />
                    </Box>

                    {/* Vehicle info */}
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 800, color: '#0F172A', lineHeight: 1.3 }}>
                          {[vehicle.brand?.name, vehicle.model?.name].filter(Boolean).join(' ')}
                        </Typography>
                        {vehicle.year && (
                          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                            {vehicle.year}
                          </Typography>
                        )}
                      </Box>

                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mt: 0.75 }}>
                        {vehicle.license_plate && (
                          <Chip
                            label={vehicle.license_plate}
                            size="small"
                            variant="outlined"
                            sx={{ fontFamily: 'monospace', fontWeight: 800, letterSpacing: '0.06em', fontSize: '0.72rem' }}
                          />
                        )}
                        {vehicle.vin && (
                          <Tooltip title="VIN номер">
                            <Chip
                              label={vehicle.vin}
                              size="small"
                              sx={{ fontFamily: 'monospace', bgcolor: '#F8FAFC', fontSize: '0.68rem', letterSpacing: '0.03em' }}
                            />
                          </Tooltip>
                        )}
                        {vehicle.mileage && (
                          <Chip
                            icon={<SpeedRounded sx={{ fontSize: '14px !important' }} />}
                            label={`${vehicle.mileage.toLocaleString('ru-RU')} км`}
                            size="small"
                            sx={{ bgcolor: '#F8FAFC', fontSize: '0.72rem' }}
                          />
                        )}
                      </Box>

                      {vehicle.customer && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mt: 1 }}>
                          <PersonRounded sx={{ fontSize: 14, color: '#94A3B8' }} />
                          <Typography variant="body2" sx={{ fontWeight: 600, color: '#475569' }}>
                            {vehicle.customer.full_name}
                          </Typography>
                          {vehicle.customer.phone && (
                            <>
                              <Typography variant="body2" color="text.disabled">·</Typography>
                              <PhoneRounded sx={{ fontSize: 13, color: '#94A3B8' }} />
                              <Typography variant="body2" color="text.secondary">
                                {vehicle.customer.phone}
                              </Typography>
                            </>
                          )}
                        </Box>
                      )}
                    </Box>

                    {/* Actions */}
                    <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<EditRounded />}
                        onClick={() => setEditVehicle(vehicle)}
                        sx={{ fontWeight: 700 }}
                      >
                        Изменить
                      </Button>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<HistoryRounded />}
                        onClick={() => setHistoryVehicle(vehicle)}
                        sx={{ fontWeight: 700 }}
                      >
                        История
                      </Button>
                    </Stack>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </Box>
      )}

      <VehicleHistoryDialog
        vehicle={historyVehicle}
        open={!!historyVehicle}
        onClose={() => setHistoryVehicle(null)}
      />
      <VehicleEditDialog
        vehicle={editVehicle}
        open={!!editVehicle}
        onClose={() => setEditVehicle(null)}
        onSaved={(updated) => {
          setResults((prev) => prev.map((v) => v.id === updated.id ? { ...v, ...updated } : v))
          setEditVehicle(null)
        }}
      />
    </Box>
  )
}
