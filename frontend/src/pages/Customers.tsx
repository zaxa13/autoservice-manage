import { useEffect, useRef, useState } from 'react'
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
  InputAdornment,
  Stack,
  TextField,
  Typography,
  alpha,
} from '@mui/material'
import {
  AddRounded,
  CloseRounded,
  EmailRounded,
  HomeRounded,
  NavigateBeforeRounded,
  NavigateNextRounded,
  PersonRounded,
  PhoneRounded,
  SearchRounded,
  StickyNote2Rounded,
} from '@mui/icons-material'
import { Link as RouterLink } from 'react-router-dom'

import api from '../services/api'
import PhoneInput from '../components/PhoneInput'
import { BRAND, PALETTE, RADIUS, SHADOW, SURFACE } from '../design-tokens'
import type { Customer, CustomerCreate } from '../types'
import { formatPhoneDisplay, isValidRussianPhone } from '../utils/phone'

const BATCH_SIZE = 30

const EMPTY_FORM: CustomerCreate = {
  full_name: '',
  phone: '',
  email: '',
  address: '',
  notes: '',
}

function CustomerFormDialog({
  open,
  initial,
  onClose,
  onSaved,
}: {
  open: boolean
  initial: Customer | null
  onClose: () => void
  onSaved: (c: Customer) => void
}) {
  const [form, setForm] = useState<CustomerCreate>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const isEdit = !!initial

  useEffect(() => {
    if (!open) return
    setError('')
    setForm(
      initial
        ? {
            full_name: initial.full_name,
            phone: initial.phone,
            email: initial.email ?? '',
            address: initial.address ?? '',
            notes: initial.notes ?? '',
          }
        : EMPTY_FORM,
    )
  }, [open, initial])

  const handleSave = async () => {
    setSaving(true)
    setError('')
    const payload: CustomerCreate = {
      full_name: form.full_name.trim(),
      phone: form.phone.trim(),
      email: form.email?.trim() || undefined,
      address: form.address?.trim() || undefined,
      notes: form.notes?.trim() || undefined,
    }
    try {
      const res = isEdit
        ? await api.put(`/customers/${initial!.id}`, payload)
        : await api.post('/customers/', payload)
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

  const canSubmit = form.full_name.trim().length > 0 && isValidRussianPhone(form.phone)

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
              <PersonRounded sx={{ color: '#fff', fontSize: 22 }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.2 }}>
                {isEdit ? 'Редактировать клиента' : 'Новый клиент'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                ФИО, телефон и контакты
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseRounded />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pt: 2.5, bgcolor: SURFACE.muted }}>
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
          <PhoneInput
            label="Телефон *"
            size="small"
            fullWidth
            value={form.phone}
            onChange={(stored) => setForm((f) => ({ ...f, phone: stored }))}
            validate
          />
          <TextField
            label="Email"
            size="small"
            fullWidth
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            placeholder="client@example.com"
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
          {saving ? <CircularProgress size={20} color="inherit" /> : isEdit ? 'Сохранить' : 'Создать'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default function CustomersPage() {
  const [inputValue, setInputValue] = useState('')
  const [results, setResults] = useState<Customer[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const [browseCustomers, setBrowseCustomers] = useState<Customer[]>([])
  const [browsePage, setBrowsePage] = useState(0)
  const [browseHasMore, setBrowseHasMore] = useState(false)
  const [browseLoading, setBrowseLoading] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<Customer | null>(null)

  const loadBrowsePage = async (page: number) => {
    setBrowseLoading(true)
    setError('')
    try {
      const res = await api.get('/customers/', {
        params: { skip: page * BATCH_SIZE, limit: BATCH_SIZE + 1 },
      })
      const data: Customer[] = res.data || []
      setBrowseHasMore(data.length > BATCH_SIZE)
      setBrowseCustomers(data.slice(0, BATCH_SIZE))
      setBrowsePage(page)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка загрузки списка')
      setBrowseCustomers([])
      setBrowseHasMore(false)
    } finally {
      setBrowseLoading(false)
    }
  }

  useEffect(() => {
    loadBrowsePage(0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSearch = async (q?: string) => {
    const searchQuery = (q ?? inputValue).trim()
    if (searchQuery.length < 2) return
    setLoading(true)
    setError('')
    setSearched(true)
    try {
      const isPhoneLike = /^[+\d\s\-()]+$/.test(searchQuery)
      if (isPhoneLike) {
        const res = await api.get('/customers/search/by-phone', { params: { phone: searchQuery } })
        setResults(res.data || [])
      } else {
        // По ФИО фильтруем на клиенте по уже загруженному списку — отдельного
        // серверного поиска по имени нет. Подгружаем побольше за один запрос.
        const res = await api.get('/customers/', { params: { skip: 0, limit: 500 } })
        const lower = searchQuery.toLowerCase()
        setResults((res.data || []).filter((c: Customer) => c.full_name.toLowerCase().includes(lower)))
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка поиска')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleClearSearch = () => {
    setInputValue('')
    setSearched(false)
    setResults([])
    setError('')
  }

  const handleCustomerSaved = (saved: Customer) => {
    setBrowseCustomers((prev) => {
      const idx = prev.findIndex((c) => c.id === saved.id)
      if (idx >= 0) {
        const copy = [...prev]
        copy[idx] = saved
        return copy
      }
      return prev
    })
    setResults((prev) => prev.map((c) => (c.id === saved.id ? saved : c)))
    if (!editing) loadBrowsePage(0)
  }

  const listToRender = searched ? results : browseCustomers

  return (
    <Box>
      {/* ── Header ── */}
      <Box
        sx={{
          mb: 4,
          pb: 3,
          borderBottom: `1px solid ${PALETTE.slate[100]}`,
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          gap: 2,
          flexWrap: 'wrap',
        }}
      >
        <Box>
          <Typography variant="overline" sx={{ color: PALETTE.slate[400], mb: 0.5, display: 'block' }}>
            База данных
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-0.03em', color: PALETTE.slate[900], lineHeight: 1 }}>
            Клиенты
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
            Поиск по ФИО или номеру телефона
          </Typography>
        </Box>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Button
            variant="contained"
            startIcon={<AddRounded />}
            onClick={() => setCreateOpen(true)}
            sx={{
              borderRadius: RADIUS.md,
              fontWeight: 700,
              px: 2.5,
              py: 1.1,
              background: BRAND.gradient,
              boxShadow: SHADOW.teal,
              '&:hover': { background: BRAND.gradient, boxShadow: SHADOW.tealLg },
            }}
          >
            Новый клиент
          </Button>
          <Box
            sx={{
              width: 44,
              height: 44,
              background: BRAND.gradient,
              borderRadius: RADIUS.lg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: SHADOW.teal,
            }}
          >
            <PersonRounded sx={{ color: '#fff', fontSize: 22 }} />
          </Box>
        </Stack>
      </Box>

      {/* ── Search ── */}
      <Box sx={{ display: 'flex', gap: 1.5, maxWidth: 680, mb: 3 }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          placeholder="Иванов · +79001234567"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch()
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchRounded sx={{ color: PALETTE.slate[400], fontSize: 22 }} />
              </InputAdornment>
            ),
            sx: { borderRadius: RADIUS.md, bgcolor: '#fff' },
          }}
        />
        <Button
          variant="contained"
          onClick={() => handleSearch()}
          disabled={loading || inputValue.trim().length < 2}
          sx={{ borderRadius: RADIUS.md, fontWeight: 700, px: 3.5, minWidth: 110, whiteSpace: 'nowrap' }}
        >
          {loading ? <CircularProgress size={20} color="inherit" /> : 'Найти'}
        </Button>
        {searched && (
          <Button variant="text" onClick={handleClearSearch} sx={{ borderRadius: RADIUS.md, fontWeight: 700, whiteSpace: 'nowrap' }}>
            Назад к списку
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3, maxWidth: 680 }}>
          {error}
        </Alert>
      )}

      {/* ── Empty: search ── */}
      {searched && !loading && results.length === 0 && !error && (
        <EmptyState
          title="Клиенты не найдены"
          subtitle="Попробуйте другой запрос"
        />
      )}

      {/* ── Empty: browse ── */}
      {!searched && !browseLoading && browseCustomers.length === 0 && !error && (
        <EmptyState
          title="В базе пока нет клиентов"
          subtitle="Добавьте первого клиента через кнопку справа сверху"
        />
      )}

      {/* ── Loader ── */}
      {!searched && browseLoading && browseCustomers.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {/* ── List ── */}
      {listToRender.length > 0 && (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
            <Typography variant="overline" sx={{ color: PALETTE.slate[500] }}>
              {searched ? 'Найдено' : 'Все клиенты'}
            </Typography>
            <Chip
              label={
                searched
                  ? results.length
                  : `${browsePage * BATCH_SIZE + 1}–${browsePage * BATCH_SIZE + browseCustomers.length}`
              }
              size="small"
              sx={{
                bgcolor: PALETTE.teal[600],
                color: '#fff',
                fontWeight: 700,
                height: 20,
                fontSize: '0.7rem',
              }}
            />
          </Box>

          <Stack spacing={1.5} sx={{ maxWidth: 760 }}>
            {listToRender.map((customer) => (
              <Card
                key={customer.id}
                variant="outlined"
                sx={{
                  borderRadius: RADIUS.lg,
                  borderLeft: `3px solid ${PALETTE.teal[600]}`,
                  transition: 'box-shadow 0.2s, border-color 0.2s',
                  '&:hover': {
                    boxShadow: '0 6px 20px rgba(0,0,0,0.08)',
                    borderLeftColor: PALETTE.teal[400],
                  },
                }}
              >
                <CardContent sx={{ '&:last-child': { pb: 2 }, p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: RADIUS.md,
                        bgcolor: alpha(PALETTE.teal[600], 0.08),
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <PersonRounded sx={{ color: PALETTE.teal[600], fontSize: 22 }} />
                    </Box>

                    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                      <Typography
                        component={RouterLink}
                        to={`/customers/${customer.id}`}
                        variant="subtitle1"
                        sx={{
                          fontWeight: 800,
                          color: PALETTE.slate[900],
                          lineHeight: 1.3,
                          textDecoration: 'none',
                          '&:hover': { color: PALETTE.teal[700], textDecoration: 'underline' },
                        }}
                      >
                        {customer.full_name}
                      </Typography>

                      <Stack direction="row" spacing={2} sx={{ mt: 0.75, flexWrap: 'wrap', rowGap: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <PhoneRounded sx={{ fontSize: 14, color: PALETTE.slate[400] }} />
                          <Typography variant="body2" color="text.secondary">
                            {formatPhoneDisplay(customer.phone)}
                          </Typography>
                        </Box>
                        {customer.email && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <EmailRounded sx={{ fontSize: 14, color: PALETTE.slate[400] }} />
                            <Typography variant="body2" color="text.secondary">
                              {customer.email}
                            </Typography>
                          </Box>
                        )}
                        {customer.address && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <HomeRounded sx={{ fontSize: 14, color: PALETTE.slate[400] }} />
                            <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 220 }}>
                              {customer.address}
                            </Typography>
                          </Box>
                        )}
                      </Stack>

                      {customer.notes && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                          <StickyNote2Rounded sx={{ fontSize: 14, color: PALETTE.slate[400] }} />
                          <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 360 }}>
                            {customer.notes}
                          </Typography>
                        </Box>
                      )}
                    </Box>

                    <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => setEditing(customer)}
                        sx={{ fontWeight: 700 }}
                      >
                        Изменить
                      </Button>
                      <Button
                        component={RouterLink}
                        to={`/customers/${customer.id}`}
                        variant="contained"
                        size="small"
                        sx={{ fontWeight: 700 }}
                      >
                        Открыть
                      </Button>
                    </Stack>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Stack>

          {!searched && (browsePage > 0 || browseHasMore) && (
            <Box
              sx={{
                maxWidth: 760,
                mt: 3,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 2,
              }}
            >
              <Button
                variant="outlined"
                startIcon={<NavigateBeforeRounded />}
                onClick={() => loadBrowsePage(browsePage - 1)}
                disabled={browsePage === 0 || browseLoading}
                sx={{ fontWeight: 700, borderRadius: RADIUS.md }}
              >
                Назад
              </Button>
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
                Страница {browsePage + 1}
              </Typography>
              <Button
                variant="contained"
                endIcon={<NavigateNextRounded />}
                onClick={() => loadBrowsePage(browsePage + 1)}
                disabled={!browseHasMore || browseLoading}
                sx={{ fontWeight: 700, borderRadius: RADIUS.md }}
              >
                {browseLoading ? <CircularProgress size={20} color="inherit" /> : 'Далее'}
              </Button>
            </Box>
          )}
        </Box>
      )}

      <CustomerFormDialog
        open={createOpen}
        initial={null}
        onClose={() => setCreateOpen(false)}
        onSaved={handleCustomerSaved}
      />
      <CustomerFormDialog
        open={!!editing}
        initial={editing}
        onClose={() => setEditing(null)}
        onSaved={handleCustomerSaved}
      />
    </Box>
  )
}

function EmptyState({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <Box sx={{ textAlign: 'center', py: 10 }}>
      <Box
        sx={{
          width: 64,
          height: 64,
          borderRadius: RADIUS.lg,
          bgcolor: PALETTE.slate[100],
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 2,
        }}
      >
        <PersonRounded sx={{ fontSize: 32, color: PALETTE.slate[400] }} />
      </Box>
      <Typography variant="subtitle1" fontWeight={700} color="text.secondary">
        {title}
      </Typography>
      <Typography variant="body2" color="text.disabled" sx={{ mt: 0.5 }}>
        {subtitle}
      </Typography>
    </Box>
  )
}
