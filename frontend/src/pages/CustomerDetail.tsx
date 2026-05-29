import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Typography,
  alpha,
} from '@mui/material'
import {
  ArrowBackRounded,
  CloseRounded,
  DirectionsCarRounded,
  EditRounded,
  EmailRounded,
  HomeRounded,
  PhoneRounded,
  SpeedRounded,
  StickyNote2Rounded,
} from '@mui/icons-material'
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom'

import api from '../services/api'
import { BRAND, PALETTE, RADIUS, SHADOW } from '../design-tokens'
import type { Customer, CustomerCreate, Vehicle } from '../types'

function EditDialog({
  open,
  customer,
  onClose,
  onSaved,
}: {
  open: boolean
  customer: Customer | null
  onClose: () => void
  onSaved: (c: Customer) => void
}) {
  const [form, setForm] = useState<CustomerCreate>({
    full_name: '',
    phone: '',
    email: '',
    address: '',
    notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !customer) return
    setError('')
    setForm({
      full_name: customer.full_name,
      phone: customer.phone,
      email: customer.email ?? '',
      address: customer.address ?? '',
      notes: customer.notes ?? '',
    })
  }, [open, customer])

  if (!customer) return null

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const res = await api.put(`/customers/${customer.id}`, {
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
        email: form.email?.trim() || undefined,
        address: form.address?.trim() || undefined,
        notes: form.notes?.trim() || undefined,
      })
      onSaved(res.data)
      onClose()
    } catch (e: any) {
      const detail = e.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail[0]?.msg ?? 'Ошибка валидации')
      } else {
        setError(typeof detail === 'string' ? detail : 'Не удалось сохранить клиента')
      }
    } finally {
      setSaving(false)
    }
  }

  const canSubmit = form.full_name.trim().length > 0 && form.phone.trim().length >= 5

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: RADIUS.lg } }}>
      <DialogTitle sx={{ pb: 1.5, borderBottom: `1px solid ${PALETTE.slate[100]}` }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                background: BRAND.gradient,
                borderRadius: RADIUS.md,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <EditRounded sx={{ color: '#fff', fontSize: 20 }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                Редактировать клиента
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {customer.full_name}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseRounded />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pt: 2.5 }}>
        <Stack spacing={2}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            label="ФИО *"
            size="small"
            fullWidth
            value={form.full_name}
            onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
            autoFocus
          />
          <TextField
            label="Телефон *"
            size="small"
            fullWidth
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />
          <TextField
            label="Email"
            size="small"
            fullWidth
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          />
          <TextField
            label="Адрес"
            size="small"
            fullWidth
            value={form.address}
            onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
          />
          <TextField
            label="Заметки"
            size="small"
            fullWidth
            multiline
            minRows={2}
            value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          />
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1, borderTop: `1px solid ${PALETTE.slate[100]}` }}>
        <Button onClick={onClose} variant="outlined">
          Отмена
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={!canSubmit || saving}>
          {saving ? <CircularProgress size={20} color="inherit" /> : 'Сохранить'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [customer, setCustomer] = useState<Customer | null>(null)
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editOpen, setEditOpen] = useState(false)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    setError('')
    Promise.all([
      api.get(`/customers/${id}`),
      api.get('/vehicles/', { params: { customer_id: id, limit: 200 } }),
    ])
      .then(([cRes, vRes]) => {
        if (cancelled) return
        setCustomer(cRes.data)
        setVehicles(vRes.data || [])
      })
      .catch((e) => {
        if (cancelled) return
        setError(e.response?.data?.detail || 'Не удалось загрузить клиента')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !customer) {
    return (
      <Box sx={{ maxWidth: 640 }}>
        <Button
          startIcon={<ArrowBackRounded />}
          onClick={() => navigate('/customers')}
          sx={{ mb: 2, fontWeight: 700 }}
        >
          Клиенты
        </Button>
        <Alert severity="error">{error || 'Клиент не найден'}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ maxWidth: 1000 }}>
      <Button
        startIcon={<ArrowBackRounded />}
        onClick={() => navigate('/customers')}
        sx={{ mb: 2, fontWeight: 700, color: PALETTE.slate[500] }}
      >
        Клиенты
      </Button>

      {/* ── Header card ── */}
      <Card
        variant="outlined"
        sx={{
          borderRadius: RADIUS.lg,
          borderLeft: `3px solid ${PALETTE.teal[600]}`,
          mb: 3,
          overflow: 'visible',
        }}
      >
        <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2.5, flexWrap: 'wrap' }}>
            <Box
              sx={{
                width: 64,
                height: 64,
                borderRadius: RADIUS.lg,
                background: BRAND.gradient,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 800,
                fontSize: '1.6rem',
                boxShadow: SHADOW.teal,
                flexShrink: 0,
              }}
            >
              {customer.full_name.charAt(0).toUpperCase()}
            </Box>

            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Typography variant="overline" sx={{ color: PALETTE.slate[400], display: 'block' }}>
                Клиент · ID {customer.id}
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: '-0.02em', color: PALETTE.slate[900] }}>
                {customer.full_name}
              </Typography>

              <Stack
                direction="row"
                spacing={3}
                sx={{ mt: 1.5, flexWrap: 'wrap', rowGap: 1.25 }}
              >
                <InfoRow icon={<PhoneRounded />} label="Телефон" value={customer.phone} />
                {customer.email && <InfoRow icon={<EmailRounded />} label="Email" value={customer.email} />}
                {customer.address && <InfoRow icon={<HomeRounded />} label="Адрес" value={customer.address} />}
              </Stack>

              {customer.notes && (
                <Box
                  sx={{
                    mt: 2,
                    p: 1.5,
                    bgcolor: alpha(PALETTE.amber.main, 0.06),
                    border: `1px solid ${PALETTE.amber.border}`,
                    borderRadius: RADIUS.md,
                    display: 'flex',
                    gap: 1,
                  }}
                >
                  <StickyNote2Rounded sx={{ color: PALETTE.amber.main, fontSize: 18, flexShrink: 0, mt: 0.2 }} />
                  <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                    {customer.notes}
                  </Typography>
                </Box>
              )}
            </Box>

            <Button
              variant="contained"
              startIcon={<EditRounded />}
              onClick={() => setEditOpen(true)}
              sx={{ fontWeight: 700, borderRadius: RADIUS.md }}
            >
              Изменить
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* ── Vehicles ── */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <Typography variant="overline" sx={{ color: PALETTE.slate[500] }}>
          Автомобили клиента
        </Typography>
        <Chip
          label={vehicles.length}
          size="small"
          sx={{ bgcolor: PALETTE.teal[600], color: '#fff', fontWeight: 700, height: 20, fontSize: '0.7rem' }}
        />
      </Box>

      {vehicles.length === 0 ? (
        <Card variant="outlined" sx={{ borderRadius: RADIUS.lg, p: 4, textAlign: 'center' }}>
          <DirectionsCarRounded sx={{ fontSize: 36, color: PALETTE.slate[400], mb: 1 }} />
          <Typography variant="body2" color="text.secondary">
            За клиентом не закреплено ни одного автомобиля
          </Typography>
        </Card>
      ) : (
        <Stack spacing={1.5}>
          {vehicles.map((v) => (
            <Card
              key={v.id}
              variant="outlined"
              sx={{
                borderRadius: RADIUS.lg,
                borderLeft: `3px solid ${PALETTE.teal[600]}`,
                transition: 'box-shadow 0.2s',
                '&:hover': { boxShadow: '0 6px 20px rgba(0,0,0,0.08)' },
              }}
            >
              <CardContent sx={{ '&:last-child': { pb: 2 }, p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box
                    sx={{
                      width: 44,
                      height: 44,
                      borderRadius: RADIUS.md,
                      bgcolor: alpha(PALETTE.teal[600], 0.08),
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <DirectionsCarRounded sx={{ color: PALETTE.teal[600], fontSize: 20 }} />
                  </Box>

                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap' }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, color: PALETTE.slate[900], lineHeight: 1.3 }}>
                        {[v.brand?.name, v.model?.name].filter(Boolean).join(' ')}
                      </Typography>
                      {v.year && (
                        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                          {v.year}
                        </Typography>
                      )}
                    </Box>

                    <Stack direction="row" spacing={0.75} sx={{ mt: 0.75, flexWrap: 'wrap', rowGap: 0.5 }}>
                      {v.license_plate && (
                        <Chip
                          label={v.license_plate}
                          size="small"
                          variant="outlined"
                          sx={{
                            fontFamily: 'monospace',
                            fontWeight: 800,
                            letterSpacing: '0.06em',
                            fontSize: '0.72rem',
                          }}
                        />
                      )}
                      {v.vin && (
                        <Chip
                          label={v.vin}
                          size="small"
                          sx={{
                            fontFamily: 'monospace',
                            bgcolor: PALETTE.slate[50],
                            fontSize: '0.68rem',
                            letterSpacing: '0.03em',
                          }}
                        />
                      )}
                      {v.mileage != null && (
                        <Chip
                          icon={<SpeedRounded sx={{ fontSize: '14px !important' }} />}
                          label={`${v.mileage.toLocaleString('ru-RU')} км`}
                          size="small"
                          sx={{ bgcolor: PALETTE.slate[50], fontSize: '0.72rem' }}
                        />
                      )}
                    </Stack>
                  </Box>

                  <Button
                    component={RouterLink}
                    to="/vehicles"
                    variant="outlined"
                    size="small"
                    sx={{ fontWeight: 700, flexShrink: 0 }}
                  >
                    К автомобилям
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}

      <EditDialog
        open={editOpen}
        customer={customer}
        onClose={() => setEditOpen(false)}
        onSaved={(saved) => setCustomer(saved)}
      />
    </Box>
  )
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box
        sx={{
          width: 28,
          height: 28,
          borderRadius: RADIUS.sm,
          bgcolor: PALETTE.slate[100],
          color: PALETTE.slate[500],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          '& svg': { fontSize: 16 },
        }}
      >
        {icon}
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.1, fontWeight: 600 }}>
          {label}
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600, color: PALETTE.slate[900] }}>
          {value}
        </Typography>
      </Box>
    </Box>
  )
}

