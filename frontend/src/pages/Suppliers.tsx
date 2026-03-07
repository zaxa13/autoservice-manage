import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  CircularProgress,
  Alert,
  Tooltip,
} from '@mui/material'
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material'
import api from '../services/api'
import { Supplier } from '../types'

const emptyForm = {
  name: '',
  inn: '',
  kpp: '',
  legal_address: '',
  contact: '',
  bank_name: '',
  bik: '',
  bank_account: '',
  correspondent_account: '',
}

function supplierToForm(s: Supplier) {
  return {
    name: s.name ?? '',
    inn: s.inn ?? '',
    kpp: s.kpp ?? '',
    legal_address: s.legal_address ?? '',
    contact: s.contact ?? '',
    bank_name: s.bank_name ?? '',
    bik: s.bik ?? '',
    bank_account: s.bank_account ?? '',
    correspondent_account: s.correspondent_account ?? '',
  }
}

export default function Suppliers() {
  const [list, setList] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadSuppliers = () => {
    setLoading(true)
    api
      .get<Supplier[]>('/suppliers/')
      .then((r) => setList(r.data))
      .catch(() => setError('Не удалось загрузить список поставщиков'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadSuppliers()
  }, [])

  const openCreate = () => {
    setEditingId(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  const openEdit = (s: Supplier) => {
    setEditingId(s.id)
    setForm(supplierToForm(s))
    setDialogOpen(true)
  }

  const closeDialog = () => {
    setDialogOpen(false)
    setEditingId(null)
    setForm(emptyForm)
  }

  const handleSave = () => {
    const name = form.name.trim()
    if (!name) {
      setError('Укажите название поставщика')
      return
    }
    setError('')
    setSaving(true)
    const payload = {
      name,
      inn: form.inn.trim() || undefined,
      kpp: form.kpp.trim() || undefined,
      legal_address: form.legal_address.trim() || undefined,
      contact: form.contact.trim() || undefined,
      bank_name: form.bank_name.trim() || undefined,
      bik: form.bik.trim() || undefined,
      bank_account: form.bank_account.trim() || undefined,
      correspondent_account: form.correspondent_account.trim() || undefined,
    }
    if (editingId !== null) {
      api
        .put<Supplier>(`/suppliers/${editingId}`, payload)
        .then(() => {
          loadSuppliers()
          closeDialog()
        })
        .catch((e) => setError(e.response?.data?.detail || 'Ошибка сохранения'))
        .finally(() => setSaving(false))
    } else {
      api
        .post<Supplier>('/suppliers/', payload)
        .then(() => {
          loadSuppliers()
          closeDialog()
        })
        .catch((e) => setError(e.response?.data?.detail || 'Ошибка создания'))
        .finally(() => setSaving(false))
    }
  }

  const handleDeleteConfirm = (id: number) => {
    setDeleting(true)
    api
      .delete(`/suppliers/${id}`)
      .then(() => {
        loadSuppliers()
        setDeleteConfirmId(null)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка удаления'))
      .finally(() => setDeleting(false))
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Поставщики
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          Добавить поставщика
        </Button>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Название</TableCell>
              <TableCell>ИНН</TableCell>
              <TableCell>КПП</TableCell>
              <TableCell>Контакт</TableCell>
              <TableCell align="right" width={120}>
                Действия
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <CircularProgress size={32} />
                </TableCell>
              </TableRow>
            ) : list.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }} color="text.secondary">
                  Нет поставщиков. Добавьте первого.
                </TableCell>
              </TableRow>
            ) : (
              list.map((s) => (
                <TableRow key={s.id} hover>
                  <TableCell>{s.name}</TableCell>
                  <TableCell>{s.inn || '—'}</TableCell>
                  <TableCell>{s.kpp || '—'}</TableCell>
                  <TableCell>{s.contact || '—'}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Редактировать">
                      <IconButton size="small" onClick={() => openEdit(s)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Удалить">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => setDeleteConfirmId(s.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Диалог создания/редактирования */}
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId !== null ? 'Редактировать поставщика' : 'Добавить поставщика'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Название"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="ООО Компания"
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="ИНН"
                value={form.inn}
                onChange={(e) => setForm((p) => ({ ...p, inn: e.target.value }))}
                placeholder="10 или 12 цифр"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="КПП"
                value={form.kpp}
                onChange={(e) => setForm((p) => ({ ...p, kpp: e.target.value }))}
                placeholder="9 цифр"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Юридический адрес"
                value={form.legal_address}
                onChange={(e) => setForm((p) => ({ ...p, legal_address: e.target.value }))}
                placeholder="необязательно"
                multiline
                minRows={2}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Контакт"
                value={form.contact}
                onChange={(e) => setForm((p) => ({ ...p, contact: e.target.value }))}
                placeholder="телефон, email"
              />
            </Grid>
            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 700, mt: 1, mb: 0.5 }}>
                Банковские реквизиты
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Название банка"
                value={form.bank_name}
                onChange={(e) => setForm((p) => ({ ...p, bank_name: e.target.value }))}
                placeholder="необязательно"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="БИК"
                value={form.bik}
                onChange={(e) => setForm((p) => ({ ...p, bik: e.target.value }))}
                placeholder="9 цифр"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Корр. счёт"
                value={form.correspondent_account}
                onChange={(e) => setForm((p) => ({ ...p, correspondent_account: e.target.value }))}
                placeholder="20 цифр"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Расчётный счёт"
                value={form.bank_account}
                onChange={(e) => setForm((p) => ({ ...p, bank_account: e.target.value }))}
                placeholder="20 цифр"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Отмена</Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saving || !form.name.trim()}
          >
            {saving ? <CircularProgress size={24} /> : editingId !== null ? 'Сохранить' : 'Добавить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Подтверждение удаления */}
      <Dialog
        open={deleteConfirmId !== null}
        onClose={() => !deleting && setDeleteConfirmId(null)}
      >
        <DialogTitle>Удалить поставщика?</DialogTitle>
        <DialogContent>
          Поставщик будет удалён. Накладные с этим поставщиком останутся, но связь станет пустой.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmId(null)} disabled={deleting}>
            Отмена
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteConfirmId !== null && handleDeleteConfirm(deleteConfirmId)}
            disabled={deleting}
          >
            {deleting ? <CircularProgress size={24} /> : 'Удалить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
