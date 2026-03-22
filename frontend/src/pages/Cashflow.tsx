import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Box, Typography, Grid, Card, CardContent, Button, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Tooltip, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem, Select, InputLabel,
  FormControl, Alert, Tabs, Tab, Divider, alpha, Stack,
  CircularProgress, FormControlLabel, Switch,
} from '@mui/material'
import {
  AddRounded, DeleteRounded, EditRounded, AccountBalanceWalletRounded,
  TrendingUpRounded, TrendingDownRounded, SwapHorizRounded,
  AccountBalanceRounded, LocalAtmRounded, RefreshRounded,
  FilterListRounded, ArchiveRounded, UnarchiveRounded,
} from '@mui/icons-material'
import { format, startOfMonth, endOfMonth } from 'date-fns'
import { useCashflowStore } from '../store/cashflowStore'
import { getRoleFromToken } from '../store/authStore'
import type {
  CashAccount,
  CashTransaction,
  CashTransactionCreate,
  CashTransactionUpdate,
  CashAccountCreate,
  CashAccountUpdate,
  CashTransactionType,
  AccountType,
} from '../types'

// ── Constants ─────────────────────────────────────────────────────────────────

const TX_TYPE_LABELS: Record<CashTransactionType, string> = {
  income: 'Приход',
  expense: 'Расход',
  transfer: 'Перевод',
}

const TX_TYPE_COLORS: Record<CashTransactionType, 'success' | 'error' | 'info'> = {
  income: 'success',
  expense: 'error',
  transfer: 'info',
}

const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  cash: 'Наличные',
  bank: 'Банк',
}

const formatMoney = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

// ── Summary Cards ─────────────────────────────────────────────────────────────

function SummaryCards() {
  const { summary } = useCashflowStore()
  if (!summary) return null

  const cards = [
    {
      label: 'Общий остаток',
      value: formatMoney(summary.total_balance),
      icon: <AccountBalanceWalletRounded sx={{ fontSize: 32 }} />,
      color: '#4F46E5',
      bg: '#EEF2FF',
    },
    {
      label: 'Приход за период',
      value: formatMoney(summary.total_income),
      icon: <TrendingUpRounded sx={{ fontSize: 32 }} />,
      color: '#16A34A',
      bg: '#F0FDF4',
    },
    {
      label: 'Расход за период',
      value: formatMoney(summary.total_expense),
      icon: <TrendingDownRounded sx={{ fontSize: 32 }} />,
      color: '#DC2626',
      bg: '#FEF2F2',
    },
    {
      label: 'Чистый поток',
      value: formatMoney(summary.net_flow),
      icon: <SwapHorizRounded sx={{ fontSize: 32 }} />,
      color: summary.net_flow >= 0 ? '#16A34A' : '#DC2626',
      bg: summary.net_flow >= 0 ? '#F0FDF4' : '#FEF2F2',
    },
  ]

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {cards.map((c) => (
        <Grid item xs={12} sm={6} md={3} key={c.label}>
          <Card sx={{ borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5 }}>
              <Box sx={{ p: 1.5, borderRadius: '12px', bgcolor: c.bg, color: c.color, display: 'flex' }}>
                {c.icon}
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                  {c.label}
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 900, color: c.color }}>
                  {c.value}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  )
}

// ── Account Cards ─────────────────────────────────────────────────────────────

interface AccountCardsProps {
  isAdmin: boolean
  onEdit: (acc: CashAccount) => void
  onArchive: (acc: CashAccount) => void
  onRestore: (acc: CashAccount) => void
  onDelete: (acc: CashAccount) => void
}

function AccountCards({ isAdmin, onEdit, onArchive, onRestore, onDelete }: AccountCardsProps) {
  const { accounts, fetchAccounts } = useCashflowStore()
  const [showArchived, setShowArchived] = useState(false)

  useEffect(() => {
    fetchAccounts(showArchived)
  }, [showArchived, fetchAccounts])

  const visible = showArchived ? accounts : accounts.filter((a) => a.is_active)

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
          Счета
        </Typography>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
            />
          }
          label={
            <Typography variant="caption" color="text.secondary">
              Показать архивные
            </Typography>
          }
          sx={{ mr: 0 }}
        />
      </Box>

      {visible.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
          {showArchived ? 'Нет архивных счетов' : 'Нет активных счетов'}
        </Typography>
      )}

      <Grid container spacing={2}>
        {visible.map((acc) => (
          <Grid item xs={12} sm={6} md={4} key={acc.id}>
            <Card
              sx={{
                borderRadius: '16px',
                border: '1px solid',
                borderColor: acc.is_active ? 'divider' : 'warning.light',
                bgcolor: acc.is_active ? 'background.paper' : 'action.hover',
              }}
            >
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
                <Box sx={{ color: acc.account_type === 'cash' ? '#F59E0B' : '#3B82F6', opacity: acc.is_active ? 1 : 0.5 }}>
                  {acc.account_type === 'cash'
                    ? <LocalAtmRounded sx={{ fontSize: 28 }} />
                    : <AccountBalanceRounded sx={{ fontSize: 28 }} />}
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 800 }} noWrap>
                      {acc.name}
                    </Typography>
                    {!acc.is_active && (
                      <Chip label="Архив" size="small" color="warning" sx={{ fontSize: '0.65rem', height: 18 }} />
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {ACCOUNT_TYPE_LABELS[acc.account_type]}
                  </Typography>
                </Box>
                <Typography
                  variant="h6"
                  sx={{ fontWeight: 900, whiteSpace: 'nowrap', opacity: acc.is_active ? 1 : 0.5 }}
                >
                  {formatMoney(acc.current_balance)}
                </Typography>
                {isAdmin && (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, ml: 0.5 }}>
                    {acc.is_active ? (
                      <>
                        <Tooltip title="Редактировать">
                          <IconButton size="small" onClick={() => onEdit(acc)}>
                            <EditRounded fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="В архив">
                          <IconButton size="small" sx={{ color: 'warning.main' }} onClick={() => onArchive(acc)}>
                            <ArchiveRounded fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    ) : (
                      <>
                        <Tooltip title="Восстановить">
                          <IconButton size="small" color="success" onClick={() => onRestore(acc)}>
                            <UnarchiveRounded fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Удалить безвозвратно">
                          <IconButton size="small" color="error" onClick={() => onDelete(acc)}>
                            <DeleteRounded fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

// ── Add Transaction Dialog ────────────────────────────────────────────────────

interface AddTxDialogProps {
  open: boolean
  onClose: () => void
}

function AddTransactionDialog({ open, onClose }: AddTxDialogProps) {
  const { accounts, categories, addTransaction, fetchCategories } = useCashflowStore()

  const [form, setForm] = useState<CashTransactionCreate>({
    transaction_type: 'income',
    account_id: 0,
    to_account_id: null,
    category_id: 0,
    amount: 0,
    description: '',
    transaction_date: null,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      fetchCategories(form.transaction_type)
      setError('')
    }
  }, [open, form.transaction_type, fetchCategories])

  const filteredCategories = categories.filter(
    (c) => c.transaction_type === form.transaction_type
  )

  const handleSubmit = async () => {
    if (!form.account_id || !form.category_id || form.amount <= 0) {
      setError('Заполните счёт, категорию и сумму')
      return
    }
    if (form.transaction_type === 'transfer' && !form.to_account_id) {
      setError('Укажите счёт назначения')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await addTransaction(form)
      onClose()
      setForm({ transaction_type: 'income', account_id: 0, to_account_id: null, category_id: 0, amount: 0, description: '', transaction_date: null })
    } catch {
      setError('Ошибка создания операции')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: '20px' } }}>
      <DialogTitle sx={{ fontWeight: 900 }}>Новая операция</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: '12px' }}>{error}</Alert>}

          <FormControl fullWidth>
            <InputLabel>Тип операции</InputLabel>
            <Select
              value={form.transaction_type}
              label="Тип операции"
              onChange={(e) =>
                setForm({ ...form, transaction_type: e.target.value as CashTransactionType, category_id: 0 })
              }
            >
              <MenuItem value="income">Приход</MenuItem>
              <MenuItem value="expense">Расход</MenuItem>
              <MenuItem value="transfer">Перевод между счетами</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Счёт</InputLabel>
            <Select
              value={form.account_id || ''}
              label="Счёт"
              onChange={(e) => setForm({ ...form, account_id: Number(e.target.value) })}
            >
              {accounts.map((a) => (
                <MenuItem key={a.id} value={a.id}>
                  {a.name} — {formatMoney(a.current_balance)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {form.transaction_type === 'transfer' && (
            <FormControl fullWidth>
              <InputLabel>Счёт назначения</InputLabel>
              <Select
                value={form.to_account_id || ''}
                label="Счёт назначения"
                onChange={(e) => setForm({ ...form, to_account_id: Number(e.target.value) })}
              >
                {accounts
                  .filter((a) => a.id !== form.account_id)
                  .map((a) => (
                    <MenuItem key={a.id} value={a.id}>
                      {a.name}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
          )}

          <FormControl fullWidth>
            <InputLabel>Категория</InputLabel>
            <Select
              value={form.category_id || ''}
              label="Категория"
              onChange={(e) => setForm({ ...form, category_id: Number(e.target.value) })}
            >
              {filteredCategories.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name} {c.is_system ? '(системная)' : ''}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Сумма, ₽"
            type="number"
            fullWidth
            value={form.amount || ''}
            onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
            inputProps={{ min: 0.01, step: '0.01' }}
          />

          <TextField
            label="Описание (необязательно)"
            fullWidth
            multiline
            rows={2}
            value={form.description || ''}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />

          <TextField
            label="Дата операции"
            type="datetime-local"
            fullWidth
            InputLabelProps={{ shrink: true }}
            value={
              form.transaction_date
                ? form.transaction_date.slice(0, 16)
                : format(new Date(), "yyyy-MM-dd'T'HH:mm")
            }
            onChange={(e) => setForm({ ...form, transaction_date: e.target.value ? `${e.target.value}:00` : null })}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} color="inherit">Отмена</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          {submitting ? <CircularProgress size={20} /> : 'Создать'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Edit Account Dialog ───────────────────────────────────────────────────────

interface EditAccountDialogProps {
  account: CashAccount | null
  onClose: () => void
}

function EditAccountDialog({ account, onClose }: EditAccountDialogProps) {
  const { editAccount } = useCashflowStore()
  const [form, setForm] = useState<CashAccountUpdate>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (account) {
      setForm({ name: account.name, is_active: account.is_active })
      setError('')
    }
  }, [account])

  const handleSubmit = async () => {
    if (!form.name?.trim()) {
      setError('Введите название счёта')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await editAccount(account!.id, form)
      onClose()
    } catch {
      setError('Ошибка обновления счёта')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      open={!!account}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{ sx: { borderRadius: '20px' } }}
    >
      <DialogTitle sx={{ fontWeight: 900 }}>Редактировать счёт</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: '12px' }}>{error}</Alert>}
          <TextField
            label="Название"
            fullWidth
            value={form.name ?? ''}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={onClose} color="inherit" variant="outlined" sx={{ borderRadius: '10px' }}>
          Отмена
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={submitting}
          sx={{ borderRadius: '10px' }}
        >
          {submitting ? <CircularProgress size={20} /> : 'Сохранить'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Add Account Dialog ────────────────────────────────────────────────────────

interface AddAccountDialogProps {
  open: boolean
  onClose: () => void
}

function AddAccountDialog({ open, onClose }: AddAccountDialogProps) {
  const { addAccount } = useCashflowStore()
  const [form, setForm] = useState<CashAccountCreate>({ name: '', account_type: 'cash', initial_balance: 0 })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setError('Введите название счёта')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await addAccount(form)
      onClose()
      setForm({ name: '', account_type: 'cash', initial_balance: 0 })
    } catch {
      setError('Ошибка создания счёта')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: '20px' } }}>
      <DialogTitle sx={{ fontWeight: 900 }}>Новый счёт</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: '12px' }}>{error}</Alert>}
          <TextField
            label="Название"
            fullWidth
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Касса (наличные)"
          />
          <FormControl fullWidth>
            <InputLabel>Тип счёта</InputLabel>
            <Select
              value={form.account_type}
              label="Тип счёта"
              onChange={(e) => setForm({ ...form, account_type: e.target.value as AccountType })}
            >
              <MenuItem value="cash">Наличные</MenuItem>
              <MenuItem value="bank">Банковский счёт</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Начальный остаток, ₽"
            type="number"
            fullWidth
            value={form.initial_balance || ''}
            onChange={(e) => setForm({ ...form, initial_balance: parseFloat(e.target.value) || 0 })}
            helperText="Введите текущую сумму при переходе с другой системы"
            inputProps={{ min: 0, step: '0.01' }}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} color="inherit">Отмена</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          {submitting ? <CircularProgress size={20} /> : 'Создать'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Edit Transaction Dialog ───────────────────────────────────────────────────

interface EditTxDialogProps {
  tx: CashTransaction | null
  onClose: () => void
}

function EditTransactionDialog({ tx, onClose }: EditTxDialogProps) {
  const { categories, editTransaction, fetchCategories } = useCashflowStore()

  const [form, setForm] = useState<CashTransactionUpdate>({
    amount: undefined,
    description: undefined,
    transaction_date: undefined,
    category_id: undefined,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (tx) {
      fetchCategories(tx.transaction_type)
      setForm({
        amount: tx.amount,
        description: tx.description ?? '',
        transaction_date: format(new Date(tx.transaction_date), "yyyy-MM-dd'T'HH:mm"),
        category_id: tx.category_id,
      })
      setError('')
    }
  }, [tx, fetchCategories])

  const filteredCategories = categories.filter(
    (c) => c.transaction_type === tx?.transaction_type
  )

  const handleSubmit = async () => {
    if (!form.amount || form.amount <= 0) {
      setError('Введите корректную сумму')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await editTransaction(tx!.id, {
        ...form,
        transaction_date: form.transaction_date ? `${form.transaction_date}:00` : undefined,
      })
      onClose()
    } catch {
      setError('Ошибка сохранения')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={!!tx} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: '20px' } }}>
      <DialogTitle sx={{ fontWeight: 900 }}>Редактировать операцию</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: '12px' }}>{error}</Alert>}

          <FormControl fullWidth>
            <InputLabel>Категория</InputLabel>
            <Select
              value={form.category_id || ''}
              label="Категория"
              onChange={(e) => setForm({ ...form, category_id: Number(e.target.value) })}
            >
              {filteredCategories.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name} {c.is_system ? '(системная)' : ''}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Сумма, ₽"
            type="number"
            fullWidth
            value={form.amount || ''}
            onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
            inputProps={{ min: 0.01, step: '0.01' }}
          />

          <TextField
            label="Описание"
            fullWidth
            multiline
            rows={2}
            value={form.description || ''}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />

          <TextField
            label="Дата операции"
            type="datetime-local"
            fullWidth
            InputLabelProps={{ shrink: true }}
            value={form.transaction_date || ''}
            onChange={(e) => setForm({ ...form, transaction_date: e.target.value })}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} color="inherit">Отмена</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          {submitting ? <CircularProgress size={20} /> : 'Сохранить'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Transactions Table ────────────────────────────────────────────────────────

const TAB_TYPE_MAP: Record<number, CashTransactionType | null> = {
  0: null,
  1: 'income',
  2: 'expense',
  3: 'transfer',
}

interface TransactionsTableProps {
  onDelete: (id: number) => void
  onEdit: (tx: CashTransaction) => void
  isAdmin: boolean
  tab: number
}

function TransactionsTable({ onDelete, onEdit, isAdmin, tab }: TransactionsTableProps) {
  const { transactions, transactionsTotal, loading } = useCashflowStore()

  const typeFilter = TAB_TYPE_MAP[tab] ?? null
  const visible = typeFilter ? transactions.filter((t) => t.transaction_type === typeFilter) : transactions

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (visible.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <Typography color="text.secondary">Операций пока нет</Typography>
        <Typography variant="caption" color="text.secondary">
          Нажмите «Новая операция» чтобы добавить первую запись
        </Typography>
      </Box>
    )
  }

  return (
    <>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
        Показано {visible.length} из {transactionsTotal}
      </Typography>
      <TableContainer component={Paper} sx={{ borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: alpha('#F1F5F9', 0.8) }}>
              <TableCell sx={{ fontWeight: 800 }}>Дата</TableCell>
              <TableCell sx={{ fontWeight: 800 }}>Тип</TableCell>
              <TableCell sx={{ fontWeight: 800 }}>Счёт</TableCell>
              <TableCell sx={{ fontWeight: 800 }}>Категория</TableCell>
              <TableCell sx={{ fontWeight: 800 }}>Описание</TableCell>
              <TableCell sx={{ fontWeight: 800 }} align="right">Сумма</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {visible.map((tx) => (
              <TableRow key={tx.id} hover>
                <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}>
                  {format(new Date(tx.transaction_date), 'dd.MM.yyyy HH:mm')}
                </TableCell>
                <TableCell>
                  <Chip
                    label={TX_TYPE_LABELS[tx.transaction_type]}
                    color={TX_TYPE_COLORS[tx.transaction_type]}
                    size="small"
                    sx={{ fontWeight: 700, fontSize: '0.7rem' }}
                  />
                </TableCell>
                <TableCell sx={{ fontSize: '0.8rem' }}>
                  {tx.transaction_type === 'transfer'
                    ? `${tx.account.name} → ${tx.to_account?.name}`
                    : tx.account.name}
                </TableCell>
                <TableCell sx={{ fontSize: '0.8rem' }}>{tx.category.name}</TableCell>
                <TableCell sx={{ fontSize: '0.8rem', color: 'text.secondary', maxWidth: 200 }}>
                  <Typography noWrap variant="caption">{tx.description || '—'}</Typography>
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 800, whiteSpace: 'nowrap' }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 800,
                      color:
                        tx.transaction_type === 'income'
                          ? 'success.main'
                          : tx.transaction_type === 'expense'
                          ? 'error.main'
                          : 'info.main',
                    }}
                  >
                    {tx.transaction_type === 'income' ? '+' : tx.transaction_type === 'expense' ? '−' : ''}
                    {formatMoney(tx.amount)}
                  </Typography>
                </TableCell>
                <TableCell padding="none" align="center" sx={{ whiteSpace: 'nowrap' }}>
                  {isAdmin && (
                    <Tooltip title="Редактировать">
                      <IconButton size="small" onClick={() => onEdit(tx)}>
                        <EditRounded fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                  {isAdmin && (
                    <Tooltip title="Удалить">
                      <IconButton size="small" color="error" onClick={() => onDelete(tx.id)}>
                        <DeleteRounded fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function Cashflow() {
  const {
    fetchAccounts, fetchCategories, fetchTransactions,
    fetchSummary, removeTransaction, removeAccount, editAccount, error,
  } = useCashflowStore()

  const isAdmin = getRoleFromToken() === 'admin'

  const [tab, setTab] = useState(0)
  const [addTxOpen, setAddTxOpen] = useState(false)
  const [addAccOpen, setAddAccOpen] = useState(false)
  const [editTx, setEditTx] = useState<CashTransaction | null>(null)
  const [editAcc, setEditAcc] = useState<CashAccount | null>(null)
  const [archiveTarget, setArchiveTarget] = useState<CashAccount | null>(null)
  const [restoreTarget, setRestoreTarget] = useState<CashAccount | null>(null)
  const [deleteAccTarget, setDeleteAccTarget] = useState<CashAccount | null>(null)
  const [filterType] = useState<CashTransactionType | ''>('')

  const thisMonthFrom = format(startOfMonth(new Date()), "yyyy-MM-dd'T'00:00:00")
  const thisMonthTo = format(endOfMonth(new Date()), "yyyy-MM-dd'T'23:59:59")

  const loadAll = useCallback(async () => {
    await Promise.all([
      fetchAccounts(),
      fetchCategories(),
      fetchTransactions({ limit: 100, transaction_type: filterType || undefined }),
      fetchSummary(thisMonthFrom, thisMonthTo),
    ])
  }, [fetchAccounts, fetchCategories, fetchTransactions, fetchSummary, filterType, thisMonthFrom, thisMonthTo])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const [confirmId, setConfirmId] = useState<number | null>(null)
  const [deleteAccError, setDeleteAccError] = useState<string | null>(null)
  const deleteAccErrorTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showDeleteAccError = (msg: string) => {
    if (deleteAccErrorTimer.current) clearTimeout(deleteAccErrorTimer.current)
    setDeleteAccError(msg)
    deleteAccErrorTimer.current = setTimeout(() => setDeleteAccError(null), 5000)
  }

  const handleDeleteTx = (id: number) => setConfirmId(id)

  const handleConfirmDelete = async () => {
    if (confirmId === null) return
    await removeTransaction(confirmId)
    setConfirmId(null)
  }

  const handleConfirmArchive = async () => {
    if (!archiveTarget) return
    try {
      await editAccount(archiveTarget.id, { is_active: false })
      setArchiveTarget(null)
      fetchAccounts(false)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Ошибка архивирования счёта'
      setArchiveTarget(null)
      showDeleteAccError(msg)
    }
  }

  const handleConfirmRestore = async () => {
    if (!restoreTarget) return
    try {
      await editAccount(restoreTarget.id, { is_active: true })
      setRestoreTarget(null)
      fetchAccounts(true)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Ошибка восстановления счёта'
      setRestoreTarget(null)
      showDeleteAccError(msg)
    }
  }

  const handleConfirmDeleteAccount = async () => {
    if (!deleteAccTarget) return
    try {
      await removeAccount(deleteAccTarget.id)
      setDeleteAccTarget(null)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Ошибка удаления счёта'
      setDeleteAccTarget(null)
      showDeleteAccError(msg)
    }
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 900 }}>Касса</Typography>
          <Typography variant="body2" color="text.secondary">
            Учёт денежных потоков · {format(new Date(), 'MMMM yyyy', { locale: undefined })}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Обновить">
            <IconButton onClick={loadAll}><RefreshRounded /></IconButton>
          </Tooltip>
          <Button variant="outlined" startIcon={<AccountBalanceRounded />} onClick={() => setAddAccOpen(true)}>
            Новый счёт
          </Button>
          <Button variant="contained" startIcon={<AddRounded />} onClick={() => setAddTxOpen(true)}>
            Новая операция
          </Button>
        </Stack>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2, borderRadius: '12px' }}>{error}</Alert>}
      {deleteAccError && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: '12px' }} onClose={() => setDeleteAccError(null)}>
          {deleteAccError}
        </Alert>
      )}

      {/* Summary */}
      <SummaryCards />
      <AccountCards
        isAdmin={isAdmin}
        onEdit={setEditAcc}
        onArchive={setArchiveTarget}
        onRestore={setRestoreTarget}
        onDelete={setDeleteAccTarget}
      />

      <Divider sx={{ my: 2 }} />

      {/* Tabs */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Все операции" />
          <Tab label="Приходы" />
          <Tab label="Расходы" />
          <Tab label="Переводы" />
        </Tabs>
        <Tooltip title="Фильтры">
          <IconButton><FilterListRounded /></IconButton>
        </Tooltip>
      </Box>

      {/* Transactions */}
      <TransactionsTable onDelete={handleDeleteTx} onEdit={setEditTx} isAdmin={isAdmin} tab={tab} />

      {/* Dialogs */}
      <AddTransactionDialog open={addTxOpen} onClose={() => { setAddTxOpen(false); loadAll() }} />
      <AddAccountDialog open={addAccOpen} onClose={() => { setAddAccOpen(false); fetchAccounts() }} />
      <EditTransactionDialog tx={editTx} onClose={() => { setEditTx(null); loadAll() }} />
      <EditAccountDialog account={editAcc} onClose={() => { setEditAcc(null); fetchAccounts() }} />

      {/* Confirm delete transaction */}
      <Dialog
        open={confirmId !== null}
        onClose={() => setConfirmId(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 900, fontSize: '1.1rem' }}>
          Удалить операцию?
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            Это действие нельзя отменить. Балансы счетов будут пересчитаны.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={() => setConfirmId(null)} color="inherit" variant="outlined" sx={{ borderRadius: '10px' }}>
            Отмена
          </Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained" sx={{ borderRadius: '10px' }}>
            Удалить
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirm archive account */}
      <Dialog
        open={!!archiveTarget}
        onClose={() => setArchiveTarget(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 900, fontSize: '1.1rem' }}>
          Переместить в архив?
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            Счёт <strong>{archiveTarget?.name}</strong> будет скрыт из активных.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            История операций сохранится. Счёт можно восстановить в любой момент через раздел «Архивные».
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={() => setArchiveTarget(null)} color="inherit" variant="outlined" sx={{ borderRadius: '10px' }}>
            Отмена
          </Button>
          <Button onClick={handleConfirmArchive} color="warning" variant="contained" sx={{ borderRadius: '10px' }}>
            В архив
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirm restore account */}
      <Dialog
        open={!!restoreTarget}
        onClose={() => setRestoreTarget(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 900, fontSize: '1.1rem' }}>
          Восстановить счёт?
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            Счёт <strong>{restoreTarget?.name}</strong> снова станет активным и будет отображаться в кассе.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={() => setRestoreTarget(null)} color="inherit" variant="outlined" sx={{ borderRadius: '10px' }}>
            Отмена
          </Button>
          <Button onClick={handleConfirmRestore} color="success" variant="contained" sx={{ borderRadius: '10px' }}>
            Восстановить
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirm hard delete account */}
      <Dialog
        open={!!deleteAccTarget}
        onClose={() => setDeleteAccTarget(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 900, fontSize: '1.1rem' }}>
          Удалить счёт безвозвратно?
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            Счёт <strong>{deleteAccTarget?.name}</strong> будет удалён навсегда.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Удаление возможно только если по счёту нет операций.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={() => setDeleteAccTarget(null)} color="inherit" variant="outlined" sx={{ borderRadius: '10px' }}>
            Отмена
          </Button>
          <Button onClick={handleConfirmDeleteAccount} color="error" variant="contained" sx={{ borderRadius: '10px' }}>
            Удалить
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
