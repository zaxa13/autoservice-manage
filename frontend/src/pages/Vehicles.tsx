import React, { useState, useRef } from 'react'
import {
  Box, Typography, TextField, InputAdornment, IconButton, CircularProgress,
  Card, CardContent, Stack, Chip, Divider, Alert, Button,
  Dialog, DialogTitle, DialogContent, DialogActions,
  Table, TableBody, TableCell, TableHead, TableRow,
  Tooltip, Paper, alpha, Collapse, MenuItem, Select, FormControl, InputLabel,
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

// Карточка одного заказ-наряда с раскрытием деталей
function OrderCard({ order }: { order: OrderDetail }) {
  const [expanded, setExpanded] = useState(false)
  const st = ORDER_STATUS_LABELS[order.status] ?? { label: order.status, color: 'default' as const }

  return (
    <Paper
      variant="outlined"
      sx={{ borderRadius: '12px', overflow: 'hidden', mb: 1.5,
        borderColor: order.status === 'completed' ? 'success.light' : 'divider' }}
    >
      {/* Шапка заказа */}
      <Box
        sx={{ display: 'flex', alignItems: 'center', gap: 2, px: 2, py: 1.5,
          bgcolor: alpha('#F8FAFC', 0.8), cursor: 'pointer',
          '&:hover': { bgcolor: alpha('#F1F5F9', 1) } }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ minWidth: 120 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, display: 'block' }}>
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
          sx={{ fontWeight: 700, borderRadius: '8px', minWidth: 90 }}
        />

        <Box sx={{ flexGrow: 1 }}>
          {order.mechanic && (
            <Typography variant="caption" color="text.secondary">
              Механик: {order.mechanic.full_name}
            </Typography>
          )}
        </Box>

        <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'text.primary', minWidth: 100, textAlign: 'right' }}>
          {formatCurrency(Number(order.total_amount))}
        </Typography>

        <IconButton size="small" sx={{ ml: 0.5 }}>
          {expanded ? <ExpandLessRounded fontSize="small" /> : <ExpandMoreRounded fontSize="small" />}
        </IconButton>
      </Box>

      {/* Раскрытые детали */}
      <Collapse in={expanded}>
        <Box sx={{ px: 2, pb: 2 }}>
          <Divider sx={{ my: 1.5 }} />

          {/* Работы */}
          {order.order_works && order.order_works.length > 0 && (
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.75 }}>
                <BuildRounded fontSize="inherit" /> РАБОТЫ
              </Typography>
              <Stack spacing={0.5}>
                {order.order_works.map((w) => (
                  <Box key={w.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">
                      {w.work?.name || w.work_name || '—'}
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

          {/* Запчасти */}
          {order.order_parts && order.order_parts.length > 0 && (
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.75 }}>
                <CheckCircleOutlineRounded fontSize="inherit" /> ЗАПЧАСТИ
              </Typography>
              <Stack spacing={0.5}>
                {order.order_parts.map((p) => (
                  <Box key={p.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                    <Box>
                      <Typography variant="body2">
                        {p.part?.name || p.part_name || '—'}
                        {p.quantity > 1 && (
                          <Typography component="span" variant="caption" color="text.secondary"> × {p.quantity}</Typography>
                        )}
                      </Typography>
                      {(p.article || p.part?.part_number) && (
                        <Typography variant="caption" color="text.secondary">
                          Арт: {p.article || p.part?.part_number}
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

          {/* Рекомендации */}
          {order.recommendations && (
            <Box sx={{ mt: 1, p: 1.5, bgcolor: alpha('#FEF9C3', 0.6), borderRadius: '8px', border: '1px dashed #FCD34D' }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: '#92400E', display: 'block', mb: 0.5 }}>
                Рекомендации
              </Typography>
              <Typography variant="body2" color="text.secondary">{order.recommendations}</Typography>
            </Box>
          )}

          {/* Итог */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1.5, pt: 1.5, borderTop: '1px dashed', borderColor: 'divider', gap: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Оплачено: <strong>{formatCurrency(Number(order.paid_amount))}</strong>
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>
              Итого: {formatCurrency(Number(order.total_amount))}
            </Typography>
          </Box>
        </Box>
      </Collapse>
    </Paper>
  )
}

// Диалог истории конкретного авто
function VehicleHistoryDialog({
  vehicle, open, onClose,
}: {
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

  const vehicleLabel = [
    vehicle.brand?.name,
    vehicle.model?.name,
    vehicle.year,
    vehicle.license_plate,
  ].filter(Boolean).join(' ')

  const totalSpent = history.reduce((sum, o) => sum + Number(o.total_amount), 0)

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { borderRadius: '20px', maxHeight: '90vh' } }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ width: 40, height: 40, bgcolor: 'primary.main', borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
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

      <DialogContent sx={{ pt: 0 }}>
        {/* Клиент */}
        {vehicle.customer && (
          <Paper variant="outlined" sx={{ p: 1.5, mb: 2, borderRadius: '12px', display: 'flex', alignItems: 'center', gap: 2 }}>
            <PersonRounded color="action" />
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{vehicle.customer.full_name}</Typography>
              <Typography variant="caption" color="text.secondary">{vehicle.customer.phone}</Typography>
            </Box>
            {vehicle.vin && (
              <Box sx={{ ml: 'auto', textAlign: 'right' }}>
                <Typography variant="caption" color="text.secondary" display="block">VIN</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>{vehicle.vin}</Typography>
              </Box>
            )}
          </Paper>
        )}

        {/* Статистика */}
        {!loading && history.length > 0 && (
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Paper variant="outlined" sx={{ flex: 1, p: 1.5, borderRadius: '12px', textAlign: 'center' }}>
              <Typography variant="h5" sx={{ fontWeight: 900, color: 'primary.main' }}>{history.length}</Typography>
              <Typography variant="caption" color="text.secondary">заказ-нарядов</Typography>
            </Paper>
            <Paper variant="outlined" sx={{ flex: 1, p: 1.5, borderRadius: '12px', textAlign: 'center' }}>
              <Typography variant="h5" sx={{ fontWeight: 900, color: 'success.main' }}>
                {formatCurrency(totalSpent)}
              </Typography>
              <Typography variant="caption" color="text.secondary">суммарно потрачено</Typography>
            </Paper>
            {vehicle.mileage && (
              <Paper variant="outlined" sx={{ flex: 1, p: 1.5, borderRadius: '12px', textAlign: 'center' }}>
                <Typography variant="h5" sx={{ fontWeight: 900 }}>
                  {vehicle.mileage.toLocaleString('ru-RU')}
                </Typography>
                <Typography variant="caption" color="text.secondary">км пробег</Typography>
              </Paper>
            )}
          </Box>
        )}

        {loading && (
          <Box sx={{ textAlign: 'center', py: 6 }}><CircularProgress /></Box>
        )}

        {error && <Alert severity="error" sx={{ borderRadius: '12px' }}>{error}</Alert>}

        {!loading && !error && history.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <HistoryRounded sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography color="text.secondary">Заказ-нарядов по этому автомобилю пока нет</Typography>
          </Box>
        )}

        {!loading && history.map((order) => (
          <OrderCard key={order.id} order={order} />
        ))}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="outlined" sx={{ borderRadius: '10px', fontWeight: 700 }}>
          Закрыть
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// Диалог редактирования автомобиля
function VehicleEditDialog({
  vehicle, open, onClose, onSaved,
}: {
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

  const handleBrandChange = (brand_id: number) => {
    setForm((f) => ({ ...f, brand_id, model_id: 0 }))
  }

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
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { borderRadius: '20px' } }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ width: 40, height: 40, bgcolor: 'primary.main', borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
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

      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: '12px' }}>{error}</Alert>}

          <FormControl fullWidth size="small">
            <InputLabel>Марка</InputLabel>
            <Select
              value={form.brand_id || ''}
              label="Марка"
              onChange={(e) => handleBrandChange(Number(e.target.value))}
              sx={{ borderRadius: '12px' }}
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
              sx={{ borderRadius: '12px' }}
            >
              {models.map((m) => (
                <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              label="Год выпуска"
              size="small"
              fullWidth
              value={form.year}
              onChange={(e) => setForm((f) => ({ ...f, year: e.target.value }))}
              inputProps={{ maxLength: 4 }}
              InputProps={{ sx: { borderRadius: '12px' } }}
            />
            <TextField
              label="Пробег (км)"
              size="small"
              fullWidth
              value={form.mileage}
              onChange={(e) => setForm((f) => ({ ...f, mileage: e.target.value }))}
              InputProps={{ sx: { borderRadius: '12px' } }}
            />
          </Box>

          <TextField
            label="Госномер"
            size="small"
            fullWidth
            value={form.license_plate}
            onChange={(e) => setForm((f) => ({ ...f, license_plate: e.target.value.toUpperCase() }))}
            InputProps={{ sx: { borderRadius: '12px', fontFamily: 'monospace' } }}
          />

          <TextField
            label="VIN"
            size="small"
            fullWidth
            value={form.vin}
            onChange={(e) => setForm((f) => ({ ...f, vin: e.target.value.toUpperCase() }))}
            InputProps={{ sx: { borderRadius: '12px', fontFamily: 'monospace' } }}
            inputProps={{ maxLength: 17 }}
          />
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button onClick={onClose} variant="outlined" sx={{ borderRadius: '10px', fontWeight: 700 }}>
          Отмена
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving || !form.brand_id || !form.model_id}
          sx={{ borderRadius: '10px', fontWeight: 700 }}
        >
          {saving ? <CircularProgress size={20} color="inherit" /> : 'Сохранить'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// Основная страница
export default function VehiclesPage() {
  const [query, setQuery] = useState('')
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

  // При вводе VIN или госномера — автоматически в верхний регистр
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  return (
    <Box>
      {/* Заголовок */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: -0.5 }}>Автомобили</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Найдите автомобиль и просмотрите полную историю обслуживания
        </Typography>
      </Box>

      {/* Поиск */}
      <Paper
        elevation={0}
        sx={{ p: 3, borderRadius: '20px', border: '1px solid', borderColor: 'divider', mb: 3, maxWidth: 640 }}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1.5, color: 'text.secondary' }}>
          Поиск по номеру телефона, VIN или госномеру
        </Typography>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <TextField
            inputRef={inputRef}
            fullWidth
            placeholder="Например: +79001234567, А123ВС77, WBA..."
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchRounded color="action" />
                </InputAdornment>
              ),
              sx: { borderRadius: '12px', fontFamily: 'monospace' },
            }}
          />
          <Button
            variant="contained"
            onClick={() => handleSearch()}
            disabled={loading || inputValue.trim().length < 2}
            sx={{ borderRadius: '12px', fontWeight: 700, px: 3, minWidth: 100 }}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : 'Найти'}
          </Button>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          VIN и госномера ищутся без учёта регистра
        </Typography>
      </Paper>

      {/* Ошибка */}
      {error && (
        <Alert severity="error" sx={{ borderRadius: '12px', mb: 2, maxWidth: 640 }}>{error}</Alert>
      )}

      {/* Результаты */}
      {searched && !loading && results.length === 0 && !error && (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <DirectionsCarRounded sx={{ fontSize: 56, color: 'text.disabled', mb: 1.5 }} />
          <Typography color="text.secondary" sx={{ fontWeight: 600 }}>Автомобили не найдены</Typography>
          <Typography variant="caption" color="text.disabled">
            Попробуйте другой запрос
          </Typography>
        </Box>
      )}

      {results.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 2, color: 'text.secondary' }}>
            Найдено: {results.length}
          </Typography>
          <Stack spacing={1.5} sx={{ maxWidth: 720 }}>
            {results.map((vehicle) => (
              <Card
                key={vehicle.id}
                variant="outlined"
                sx={{ borderRadius: '16px', transition: 'box-shadow 0.2s',
                  '&:hover': { boxShadow: '0 4px 16px rgba(0,0,0,0.1)', borderColor: 'primary.light' } }}
              >
                <CardContent sx={{ '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                    {/* Иконка авто */}
                    <Box sx={{ width: 48, height: 48, bgcolor: alpha('#4F46E5', 0.1),
                      borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <DirectionsCarRounded sx={{ color: 'primary.main', fontSize: 24 }} />
                    </Box>

                    {/* Данные авто */}
                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                        {[vehicle.brand?.name, vehicle.model?.name].filter(Boolean).join(' ')}
                        {vehicle.year && (
                          <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                            {vehicle.year}
                          </Typography>
                        )}
                      </Typography>

                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 0.75 }}>
                        {vehicle.license_plate && (
                          <Chip
                            label={vehicle.license_plate}
                            size="small"
                            variant="outlined"
                            sx={{ fontWeight: 800, fontFamily: 'monospace', borderRadius: '8px', letterSpacing: 1 }}
                          />
                        )}
                        {vehicle.vin && (
                          <Tooltip title="VIN номер">
                            <Chip
                              label={vehicle.vin}
                              size="small"
                              sx={{ fontWeight: 700, fontFamily: 'monospace', borderRadius: '8px',
                                bgcolor: alpha('#F1F5F9', 1), fontSize: '0.7rem' }}
                            />
                          </Tooltip>
                        )}
                        {vehicle.mileage && (
                          <Chip
                            label={`${vehicle.mileage.toLocaleString('ru-RU')} км`}
                            size="small"
                            sx={{ borderRadius: '8px', fontSize: '0.75rem' }}
                          />
                        )}
                      </Box>

                      {/* Клиент */}
                      {vehicle.customer && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mt: 1 }}>
                          <PersonRounded fontSize="small" color="action" />
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {vehicle.customer.full_name}
                          </Typography>
                          {vehicle.customer.phone && (
                            <>
                              <Typography variant="body2" color="text.disabled">·</Typography>
                              <PhoneRounded fontSize="small" color="action" />
                              <Typography variant="body2" color="text.secondary">
                                {vehicle.customer.phone}
                              </Typography>
                            </>
                          )}
                        </Box>
                      )}
                    </Box>

                    {/* Кнопки действий */}
                    <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
                      <Button
                        variant="outlined"
                        startIcon={<EditRounded />}
                        onClick={() => setEditVehicle(vehicle)}
                        sx={{ borderRadius: '12px', fontWeight: 700 }}
                      >
                        Изменить
                      </Button>
                      <Button
                        variant="contained"
                        startIcon={<HistoryRounded />}
                        onClick={() => setHistoryVehicle(vehicle)}
                        sx={{ borderRadius: '12px', fontWeight: 700 }}
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

      {/* Диалог истории */}
      <VehicleHistoryDialog
        vehicle={historyVehicle}
        open={!!historyVehicle}
        onClose={() => setHistoryVehicle(null)}
      />

      {/* Диалог редактирования */}
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
