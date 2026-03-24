import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Box, Typography, Grid, Card, CardContent, Button, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Tooltip, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem, Select, InputLabel,
  FormControl, Alert, Tabs, Tab, Divider, Stack, Container,
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
import {
  PALETTE, BRAND, SURFACE, SHADOW, RADIUS, MOTION,
  iconBoxSx, cardSx, overlineSx,
} from '../design-tokens'
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

// ── Branded domain IDs ─────────────────────────────────────────────────────────

type Brand<T, B extends string> = T & { readonly __brand: B }
type TransactionId = Brand<number, 'TransactionId'>

// ── Tab index with exhaustive mapping ─────────────────────────────────────────

type TabIndex = 0 | 1 | 2 | 3

const TAB_TYPE_MAP = {
  0: null,
  1: 'income',
  2: 'expense',
  3: 'transfer',
} as const satisfies Record<TabIndex, CashTransactionType | null>

// ── Constants (satisfies for type-checked exhaustiveness) ─────────────────────

const TX_TYPE_LABELS = {
  income:   'Приход',
  expense:  'Расход',
  transfer: 'Перевод',
} as const satisfies Record<CashTransactionType, string>

const TX_TYPE_COLORS = {
  income:   'success',
  expense:  'error',
  transfer: 'info',
} as const satisfies Record<CashTransactionType, 'success' | 'error' | 'info'>

const ACCOUNT_TYPE_LABELS = {
  cash: 'Наличные',
  bank: 'Банк',
} as const satisfies Record<AccountType, string>

// ── Type predicates ────────────────────────────────────────────────────────────

function isTransfer(tx: CashTransaction): tx is CashTransaction & {
  transaction_type: 'transfer'
  to_account: NonNullable<CashTransaction['to_account']>
} {
  return tx.transaction_type === 'transfer'
}

// ── Utility types ──────────────────────────────────────────────────────────────

/** Confirmation dialog variants */
type ConfirmVariant = 'archive' | 'restore' | 'delete-account' | 'delete-tx'

interface ConfirmState {
  variant: ConfirmVariant
  accountTarget?: CashAccount
  txId?: TransactionId
}

// ── Formatter ─────────────────────────────────────────────────────────────────

const formatMoney = (n: number): string =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

// ── Summary card config ────────────────────────────────────────────────────────

interface SummaryCardConfig {
  label: string
  value: string
  icon: React.ReactNode
  color: string
}

// ── Summary Cards ─────────────────────────────────────────────────────────────

function SummaryCards() {
  const { summary } = useCashflowStore()
  if (!summary) return null

  const netPositive = summary.net_flow >= 0

  const cards: SummaryCardConfig[] = [
    {
      label: 'Общий остаток',
      value: formatMoney(summary.total_balance),
      icon:  <AccountBalanceWalletRounded sx={{ fontSize: 22 }} />,
      color: BRAND.primary,
    },
    {
      label: 'Приход за период',
      value: formatMoney(summary.total_income),
      icon:  <TrendingUpRounded sx={{ fontSize: 22 }} />,
      color: PALETTE.green.main,
    },
    {
      label: 'Расход за период',
      value: formatMoney(summary.total_expense),
      icon:  <TrendingDownRounded sx={{ fontSize: 22 }} />,
      color: PALETTE.red.main,
    },
    {
      label: 'Чистый поток',
      value: formatMoney(summary.net_flow),
      icon:  <SwapHorizRounded sx={{ fontSize: 22 }} />,
      color: netPositive ? PALETTE.green.main : PALETTE.red.main,
    },
  ]

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {cards.map((c) => (
        <Grid item xs={12} sm={6} md={3} key={c.label}>
          <Card sx={{ ...cardSx }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2.5, '&:last-child': { pb: 2.5 } }}>
              <Box sx={iconBoxSx(c.color)}>
                {c.icon}
              </Box>
              <Box>
                <Typography sx={overlineSx}>{c.label}</Typography>
                <Typography variant="h6" sx={{ fontWeight: 800, color: c.color, lineHeight: 1.2, mt: 0.25 }}>
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
  onConfirm: (state: ConfirmState) => void
  onEdit: (acc: CashAccount) => void
}

function AccountCards({ isAdmin, onConfirm, onEdit }: AccountCardsProps) {
  const { accounts, fetchAccounts } = useCashflowStore()
  const [showArchived, setShowArchived] = useState(false)

  useEffect(() => {
    fetchAccounts(showArchived)
  }, [showArchived, fetchAccounts])

  const visible = showArchived ? accounts : accounts.filter((a) => a.is_active)

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: PALETTE.stone[600], letterSpacing: '0.04em', textTransform: 'uppercase', fontSize: '0.72rem' }}>
          Счета
        </Typography>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
              sx={{ '& .MuiSwitch-thumb': { boxShadow: SHADOW.xs } }}
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
        {visible.map((acc) => {
          const accentColor = acc.account_type === 'cash' ? PALETTE.amber.main : PALETTE.blue.main

          return (
            <Grid item xs={12} sm={6} md={4} key={acc.id}>
              <Card
                sx={{
                  ...cardSx,
                  borderColor: acc.is_active ? PALETTE.stone[200] : PALETTE.amber.border,
                  bgcolor: acc.is_active ? SURFACE.card : PALETTE.amber.bg,
                  opacity: acc.is_active ? 1 : 0.85,
                }}
              >
                <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2, '&:last-child': { pb: 2 } }}>
                  <Box sx={iconBoxSx(accentColor)}>
                    {acc.account_type === 'cash'
                      ? <LocalAtmRounded sx={{ fontSize: 20 }} />
                      : <AccountBalanceRounded sx={{ fontSize: 20 }} />}
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
                        {acc.name}
                      </Typography>
                      {!acc.is_active && (
                        <Chip label="Архив" size="small" color="warning" sx={{ fontSize: '0.62rem', height: 17, borderRadius: RADIUS.full }} />
                      )}
                    </Box>
                    <Typography variant="caption" sx={{ color: PALETTE.stone[500] }}>
                      {ACCOUNT_TYPE_LABELS[acc.account_type]}
                    </Typography>
                  </Box>
                  <Typography variant="body1" sx={{ fontWeight: 800, whiteSpace: 'nowrap', color: PALETTE.stone[800] }}>
                    {formatMoney(acc.current_balance)}
                  </Typography>
                  {isAdmin && (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, ml: 0.25 }}>
                      {acc.is_active ? (
                        <>
                          <Tooltip title="Редактировать">
                            <IconButton size="small" onClick={() => onEdit(acc)}>
                              <EditRounded sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="В архив">
                            <IconButton
                              size="small"
                              sx={{ color: PALETTE.amber.main }}
                              onClick={() => onConfirm({ variant: 'archive', accountTarget: acc })}
                            >
                              <ArchiveRounded sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                        </>
                      ) : (
                        <>
                          <Tooltip title="Восстановить">
                            <IconButton
                              size="small"
                              sx={{ color: PALETTE.green.main }}
                              onClick={() => onConfirm({ variant: 'restore', accountTarget: acc })}
                            >
                              <UnarchiveRounded sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Удалить безвозвратно">
                            <IconButton
                              size="small"
                              sx={{ color: PALETTE.red.main }}
                              onClick={() => onConfirm({ variant: 'delete-account', accountTarget: acc })}
                            >
                              <DeleteRounded sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          )
        })}
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
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: RADIUS.xl } }}>
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>Новая операция</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: RADIUS.md }}>{error}</Alert>}

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
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={onClose} color="inherit" variant="outlined" sx={{ borderRadius: RADIUS.md }}>
          Отмена
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting} sx={{ borderRadius: RADIUS.md }}>
          {submitting ? <CircularProgress size={20} color="inherit" /> : 'Создать'}
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
    <Dialog open={!!account} onClose={onClose} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: RADIUS.xl } }}>
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>Редактировать счёт</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: RADIUS.md }}>{error}</Alert>}
          <TextField
            label="Название"
            fullWidth
            value={form.name ?? ''}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={onClose} color="inherit" variant="outlined" sx={{ borderRadius: RADIUS.md }}>
          Отмена
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting} sx={{ borderRadius: RADIUS.md }}>
          {submitting ? <CircularProgress size={20} color="inherit" /> : 'Сохранить'}
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
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: RADIUS.xl } }}>
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>Новый счёт</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: RADIUS.md }}>{error}</Alert>}
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
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={onClose} color="inherit" variant="outlined" sx={{ borderRadius: RADIUS.md }}>
          Отмена
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting} sx={{ borderRadius: RADIUS.md }}>
          {submitting ? <CircularProgress size={20} color="inherit" /> : 'Создать'}
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
    <Dialog open={!!tx} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: RADIUS.xl } }}>
      <DialogTitle sx={{ fontWeight: 800, pb: 1 }}>Редактировать операцию</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error" sx={{ borderRadius: RADIUS.md }}>{error}</Alert>}

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
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={onClose} color="inherit" variant="outlined" sx={{ borderRadius: RADIUS.md }}>
          Отмена
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting} sx={{ borderRadius: RADIUS.md }}>
          {submitting ? <CircularProgress size={20} color="inherit" /> : 'Сохранить'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ── Transactions Table ────────────────────────────────────────────────────────

interface TransactionsTableProps {
  onDelete: (id: TransactionId) => void
  onEdit: (tx: CashTransaction) => void
  isAdmin: boolean
  tab: TabIndex
}

function TransactionsTable({ onDelete, onEdit, isAdmin, tab }: TransactionsTableProps) {
  const { transactions, transactionsTotal, loading } = useCashflowStore()

  const typeFilter = TAB_TYPE_MAP[tab]
  const visible = typeFilter !== null
    ? transactions.filter((t) => t.transaction_type === typeFilter)
    : transactions

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
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
          Нажмите «Новая операция» чтобы добавить первую запись
        </Typography>
      </Box>
    )
  }

  const amountColor = (type: CashTransactionType): string => {
    if (type === 'income')   return PALETTE.green.main
    if (type === 'expense')  return PALETTE.red.main
    return PALETTE.blue.main
  }

  const amountPrefix = (type: CashTransactionType): string => {
    if (type === 'income')  return '+'
    if (type === 'expense') return '−'
    return ''
  }

  return (
    <>
      <Typography variant="caption" sx={{ ...overlineSx, mb: 1 }}>
        Показано {visible.length} из {transactionsTotal}
      </Typography>
      <TableContainer
        component={Paper}
        sx={{
          borderRadius: RADIUS.lg,
          border: `1px solid ${PALETTE.stone[200]}`,
          boxShadow: SHADOW.sm,
        }}
      >
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: SURFACE.muted }}>
              {['Дата', 'Тип', 'Счёт', 'Категория', 'Описание'].map((h) => (
                <TableCell key={h} sx={{ fontWeight: 700, fontSize: '0.78rem', color: PALETTE.stone[600] }}>
                  {h}
                </TableCell>
              ))}
              <TableCell sx={{ fontWeight: 700, fontSize: '0.78rem', color: PALETTE.stone[600] }} align="right">
                Сумма
              </TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {visible.map((tx) => (
              <TableRow
                key={tx.id}
                hover
                sx={{ transition: `background ${MOTION.fast}` }}
              >
                <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.8rem', color: PALETTE.stone[600] }}>
                  {format(new Date(tx.transaction_date), 'dd.MM.yyyy HH:mm')}
                </TableCell>
                <TableCell>
                  <Chip
                    label={TX_TYPE_LABELS[tx.transaction_type]}
                    color={TX_TYPE_COLORS[tx.transaction_type]}
                    size="small"
                    sx={{ fontWeight: 700, fontSize: '0.7rem', borderRadius: RADIUS.full }}
                  />
                </TableCell>
                <TableCell sx={{ fontSize: '0.8rem' }}>
                  {isTransfer(tx)
                    ? `${tx.account.name} → ${tx.to_account.name}`
                    : tx.account.name}
                </TableCell>
                <TableCell sx={{ fontSize: '0.8rem' }}>{tx.category.name}</TableCell>
                <TableCell sx={{ fontSize: '0.8rem', color: 'text.secondary', maxWidth: 200 }}>
                  <Typography noWrap variant="caption">{tx.description || '—'}</Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 800,
                      whiteSpace: 'nowrap',
                      color: amountColor(tx.transaction_type),
                    }}
                  >
                    {amountPrefix(tx.transaction_type)}{formatMoney(tx.amount)}
                  </Typography>
                </TableCell>
                <TableCell padding="none" align="center" sx={{ whiteSpace: 'nowrap', pr: 1 }}>
                  {isAdmin && (
                    <Tooltip title="Редактировать">
                      <IconButton size="small" onClick={() => onEdit(tx)}>
                        <EditRounded sx={{ fontSize: 16 }} />
                      </IconButton>
                    </Tooltip>
                  )}
                  {isAdmin && (
                    <Tooltip title="Удалить">
                      <IconButton
                        size="small"
                        sx={{ color: PALETTE.red.main }}
                        onClick={() => onDelete(tx.id as TransactionId)}
                      >
                        <DeleteRounded sx={{ fontSize: 16 }} />
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

// ── Confirm Dialog (generic) ──────────────────────────────────────────────────

interface ConfirmDialogConfig {
  title: string
  body: React.ReactNode
  confirmLabel: string
  confirmColor: 'error' | 'warning' | 'success' | 'primary'
  onConfirm: () => Promise<void>
}

function buildConfirmConfig(
  state: ConfirmState | null,
  handlers: {
    onDeleteTx: () => Promise<void>
    onArchive: () => Promise<void>
    onRestore: () => Promise<void>
    onDeleteAccount: () => Promise<void>
  }
): ConfirmDialogConfig | null {
  if (!state) return null

  switch (state.variant) {
    case 'delete-tx':
      return {
        title: 'Удалить операцию?',
        body: 'Это действие нельзя отменить. Балансы счетов будут пересчитаны.',
        confirmLabel: 'Удалить',
        confirmColor: 'error',
        onConfirm: handlers.onDeleteTx,
      }
    case 'archive':
      return {
        title: 'Переместить в архив?',
        body: (
          <>
            Счёт <strong>{state.accountTarget?.name}</strong> будет скрыт из активных.{' '}
            История операций сохранится.
          </>
        ),
        confirmLabel: 'В архив',
        confirmColor: 'warning',
        onConfirm: handlers.onArchive,
      }
    case 'restore':
      return {
        title: 'Восстановить счёт?',
        body: (
          <>
            Счёт <strong>{state.accountTarget?.name}</strong> снова станет активным.
          </>
        ),
        confirmLabel: 'Восстановить',
        confirmColor: 'success',
        onConfirm: handlers.onRestore,
      }
    case 'delete-account':
      return {
        title: 'Удалить счёт безвозвратно?',
        body: (
          <>
            Счёт <strong>{state.accountTarget?.name}</strong> будет удалён навсегда.{' '}
            Удаление возможно только если по счёту нет операций.
          </>
        ),
        confirmLabel: 'Удалить',
        confirmColor: 'error',
        onConfirm: handlers.onDeleteAccount,
      }
  }
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function Cashflow() {
  const {
    fetchAccounts, fetchCategories, fetchTransactions,
    fetchSummary, removeTransaction, removeAccount, editAccount, error,
  } = useCashflowStore()

  const isAdmin = getRoleFromToken() === 'admin'

  const [tab, setTab] = useState<TabIndex>(0)
  const [addTxOpen, setAddTxOpen]   = useState(false)
  const [addAccOpen, setAddAccOpen] = useState(false)
  const [editTx, setEditTx]   = useState<CashTransaction | null>(null)
  const [editAcc, setEditAcc] = useState<CashAccount | null>(null)

  // Single confirm state replaces 4 separate dialog states
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null)
  const [confirmRunning, setConfirmRunning] = useState(false)

  const [accError, setAccError] = useState<string | null>(null)
  const accErrorTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const thisMonthFrom = format(startOfMonth(new Date()), "yyyy-MM-dd'T'00:00:00")
  const thisMonthTo   = format(endOfMonth(new Date()), "yyyy-MM-dd'T'23:59:59")

  const loadAll = useCallback(async () => {
    await Promise.all([
      fetchAccounts(),
      fetchCategories(),
      fetchTransactions({ limit: 100 }),
      fetchSummary(thisMonthFrom, thisMonthTo),
    ])
  }, [fetchAccounts, fetchCategories, fetchTransactions, fetchSummary, thisMonthFrom, thisMonthTo])

  useEffect(() => { loadAll() }, [loadAll])

  const showAccError = (msg: string) => {
    if (accErrorTimer.current) clearTimeout(accErrorTimer.current)
    setAccError(msg)
    accErrorTimer.current = setTimeout(() => setAccError(null), 5000)
  }

  const handleConfirm = async () => {
    if (!confirmState) return
    setConfirmRunning(true)

    const apiError = (e: unknown, fallback: string): string =>
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback

    try {
      switch (confirmState.variant) {
        case 'delete-tx':
          if (confirmState.txId !== undefined) await removeTransaction(confirmState.txId)
          break
        case 'archive':
          if (confirmState.accountTarget) {
            await editAccount(confirmState.accountTarget.id, { is_active: false })
            fetchAccounts(false)
          }
          break
        case 'restore':
          if (confirmState.accountTarget) {
            await editAccount(confirmState.accountTarget.id, { is_active: true })
            fetchAccounts(true)
          }
          break
        case 'delete-account':
          if (confirmState.accountTarget) await removeAccount(confirmState.accountTarget.id)
          break
      }
    } catch (e: unknown) {
      showAccError(apiError(e, 'Произошла ошибка'))
    } finally {
      setConfirmRunning(false)
      setConfirmState(null)
    }
  }

  const confirmConfig = buildConfirmConfig(confirmState, {
    onDeleteTx:      handleConfirm,
    onArchive:       handleConfirm,
    onRestore:       handleConfirm,
    onDeleteAccount: handleConfirm,
  })

  return (
    <Container maxWidth={false} sx={{ px: { xs: 2, md: 5 }, py: 2 }}>
      {/* ── Header ── */}
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 900 }}>Касса</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
            Учёт денежных потоков · {format(new Date(), 'MMMM yyyy')}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Tooltip title="Обновить">
            <IconButton onClick={loadAll} sx={{ color: PALETTE.stone[500] }}>
              <RefreshRounded />
            </IconButton>
          </Tooltip>
          <Button
            variant="outlined"
            startIcon={<AccountBalanceRounded />}
            onClick={() => setAddAccOpen(true)}
            sx={{ borderRadius: RADIUS.md }}
          >
            Новый счёт
          </Button>
          <Button
            variant="contained"
            startIcon={<AddRounded />}
            onClick={() => setAddTxOpen(true)}
            sx={{ borderRadius: RADIUS.md }}
          >
            Новая операция
          </Button>
        </Stack>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: RADIUS.md }}>{error}</Alert>
      )}
      {accError && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: RADIUS.md }} onClose={() => setAccError(null)}>
          {accError}
        </Alert>
      )}

      {/* ── Summary ── */}
      <SummaryCards />

      {/* ── Accounts ── */}
      <AccountCards
        isAdmin={isAdmin}
        onConfirm={setConfirmState}
        onEdit={setEditAcc}
      />

      <Divider sx={{ my: 2, borderColor: PALETTE.stone[200] }} />

      {/* ── Transaction tabs ── */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Tabs value={tab} onChange={(_, v: TabIndex) => setTab(v)}>
          <Tab label="Все операции" />
          <Tab label="Приходы" />
          <Tab label="Расходы" />
          <Tab label="Переводы" />
        </Tabs>
        <Tooltip title="Фильтры">
          <IconButton sx={{ color: PALETTE.stone[500] }}>
            <FilterListRounded />
          </IconButton>
        </Tooltip>
      </Box>

      <TransactionsTable
        onDelete={(id) => setConfirmState({ variant: 'delete-tx', txId: id })}
        onEdit={setEditTx}
        isAdmin={isAdmin}
        tab={tab}
      />

      {/* ── CRUD Dialogs ── */}
      <AddTransactionDialog open={addTxOpen}  onClose={() => { setAddTxOpen(false); loadAll() }} />
      <AddAccountDialog     open={addAccOpen} onClose={() => { setAddAccOpen(false); fetchAccounts() }} />
      <EditTransactionDialog tx={editTx}      onClose={() => { setEditTx(null); loadAll() }} />
      <EditAccountDialog     account={editAcc} onClose={() => { setEditAcc(null); fetchAccounts() }} />

      {/* ── Unified confirm dialog ── */}
      <Dialog
        open={!!confirmState}
        onClose={() => !confirmRunning && setConfirmState(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: RADIUS.xl, p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 800, fontSize: '1.05rem' }}>
          {confirmConfig?.title}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {confirmConfig?.body}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button
            onClick={() => setConfirmState(null)}
            color="inherit"
            variant="outlined"
            disabled={confirmRunning}
            sx={{ borderRadius: RADIUS.md }}
          >
            Отмена
          </Button>
          <Button
            onClick={handleConfirm}
            color={confirmConfig?.confirmColor ?? 'primary'}
            variant="contained"
            disabled={confirmRunning}
            sx={{ borderRadius: RADIUS.md }}
          >
            {confirmRunning ? <CircularProgress size={20} color="inherit" /> : confirmConfig?.confirmLabel}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
