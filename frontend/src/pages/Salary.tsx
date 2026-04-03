import { useState, useEffect } from 'react'
import {
  Container, Typography, Box, Button, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Stack, Alert, Tab, Tabs, TextField, CircularProgress,
  Chip, MenuItem, FormControl, InputLabel, Select, Dialog, DialogTitle, DialogContent,
  DialogActions, Tooltip, IconButton, RadioGroup, FormControlLabel, Radio
} from '@mui/material'
import {
  CalculateRounded, CheckCircleRounded, EditRounded, PercentRounded, PersonRounded,
  AccountBalanceWalletRounded
} from '@mui/icons-material'
import type { Employee, SalaryScheme, SalaryRecord, SalaryStatus, CashAccount } from '../types'
import api from '../services/api'

const STATUS_LABELS = {
  draft:      'Черновик',
  calculated: 'Рассчитана',
  paid:       'Выплачена',
} as const satisfies Record<SalaryStatus, string>

const STATUS_COLORS = {
  draft:      'default',
  calculated: 'info',
  paid:       'success',
} as const satisfies Record<SalaryStatus, 'default' | 'info' | 'success'>

const POSITION_LABELS: Record<string, string> = {
  admin: 'Администратор',
  manager: 'Менеджер',
  mechanic: 'Механик',
}

const fmt = (v: unknown): string =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(Number(v) || 0)

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('ru-RU')
}

function periodLabel(start: string, end: string) {
  const s = new Date(start)
  const e = new Date(end)
  const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
  if (s.getFullYear() === e.getFullYear() && s.getMonth() === e.getMonth()) {
    return `${months[s.getMonth()]} ${s.getFullYear()}`
  }
  return `${fmtDate(start)} – ${fmtDate(end)}`
}

// Get first/last day of current month
function currentMonthRange() {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth(), 1)
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { start: fmt(first), end: fmt(last) }
}

export default function Salary() {
  const [tab, setTab] = useState(0)
  const [employees, setEmployees] = useState<Employee[]>([])
  const [salaries, setSalaries] = useState<SalaryRecord[]>([])
  const [schemes, setSchemes] = useState<Record<number, SalaryScheme>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Calculate dialog
  const [calcOpen, setCalcOpen] = useState(false)
  const [calcEmployeeId, setCalcEmployeeId] = useState<number | ''>('')
  const [calcPeriod, setCalcPeriod] = useState(currentMonthRange())
  const [calculating, setCalculating] = useState(false)
  const [calcError, setCalcError] = useState('')

  // Scheme edit
  const [schemeEditId, setSchemeEditId] = useState<number | null>(null)
  const [schemeWorks, setSchemeWorks] = useState('')
  const [schemeRevenue, setSchemeRevenue] = useState('')
  const [savingScheme, setSavingScheme] = useState(false)

  // Pay salary dialog
  const [payDialogSalary, setPayDialogSalary] = useState<SalaryRecord | null>(null)
  const [accounts, setAccounts] = useState<CashAccount[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [paying, setPaying] = useState(false)

  const loadData = async () => {
    try {
      setLoading(true)
      const [empRes, salRes, accRes] = await Promise.all([
        api.get('/employees/'),
        api.get('/salary/?limit=200'),
        api.get('/cashflow/accounts'),
      ])
      const emps: Employee[] = empRes.data || []
      setEmployees(emps)
      setSalaries(salRes.data || [])
      const accs: CashAccount[] = (accRes.data?.accounts || accRes.data || []).filter((a: CashAccount) => a.is_active)
      setAccounts(accs)

      // Load schemes for all employees
      const schemeMap: Record<number, SalaryScheme> = {}
      await Promise.all(
        emps.map(async (e) => {
          try {
            const r = await api.get(`/salary/scheme/${e.id}`)
            schemeMap[e.id] = r.data
          } catch {
            schemeMap[e.id] = { employee_id: e.id, works_percentage: 0, revenue_percentage: 0 }
          }
        })
      )
      setSchemes(schemeMap)
    } catch {
      setError('Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleCalculate = async () => {
    if (!calcEmployeeId) { setCalcError('Выберите сотрудника'); return }
    setCalculating(true)
    setCalcError('')
    try {
      await api.post('/salary/calculate', {
        employee_id: calcEmployeeId,
        period_start: calcPeriod.start,
        period_end: calcPeriod.end,
      })
      setCalcOpen(false)
      setSuccess('Зарплата рассчитана')
      await loadData()
    } catch (e: any) {
      setCalcError(e.response?.data?.detail || 'Ошибка расчёта')
    } finally {
      setCalculating(false)
    }
  }

  const handleOpenPayDialog = (salary: SalaryRecord) => {
    setPayDialogSalary(salary)
    // выбираем первый активный счёт по умолчанию
    setSelectedAccountId(accounts.length > 0 ? accounts[0].id : null)
  }

  const handleConfirmPay = async () => {
    if (!payDialogSalary) return
    setPaying(true)
    try {
      const params = selectedAccountId ? `?account_id=${selectedAccountId}` : ''
      await api.post(`/salary/${payDialogSalary.id}/pay${params}`)
      setPayDialogSalary(null)
      setSuccess('Зарплата выплачена')
      await loadData()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка выплаты')
    } finally {
      setPaying(false)
    }
  }

  const handleOpenSchemeEdit = (emp: Employee) => {
    const s = schemes[emp.id]
    setSchemeEditId(emp.id)
    setSchemeWorks(s?.works_percentage?.toString() ?? '0')
    setSchemeRevenue(s?.revenue_percentage?.toString() ?? '0')
  }

  const handleSaveScheme = async () => {
    if (schemeEditId === null) return
    setSavingScheme(true)
    try {
      const r = await api.put(`/salary/scheme/${schemeEditId}`, {
        works_percentage: parseFloat(schemeWorks) || 0,
        revenue_percentage: parseFloat(schemeRevenue) || 0,
      })
      setSchemes(prev => ({ ...prev, [schemeEditId]: r.data }))
      setSchemeEditId(null)
      setSuccess('Схема сохранена')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSavingScheme(false)
    }
  }

  const empById = (id: number) => employees.find(e => e.id === id)

  if (loading) return <Container sx={{ py: 4, textAlign: 'center' }}><CircularProgress /></Container>

  return (
    <Container maxWidth={false} sx={{ px: { xs: 2, md: 5 }, py: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 900 }}>Зарплата</Typography>
        {tab === 0 && (
          <Button variant="contained" startIcon={<CalculateRounded />} onClick={() => { setCalcError(''); setCalcOpen(true) }} sx={{ borderRadius: 3, px: 3 }}>
            Рассчитать
          </Button>
        )}
      </Stack>

      {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 2 }}>{success}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Расчёты" />
        <Tab label="Схемы зарплат" icon={<PercentRounded />} iconPosition="start" />
      </Tabs>

      {/* ── Tab 0: Salary records ── */}
      {tab === 0 && (
        <TableContainer component={Paper} sx={{ borderRadius: 3, border: '1px solid #E2E8F0' }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#F8FAFC' }}>
                <TableCell sx={{ fontWeight: 700 }}>Сотрудник</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Период</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Оклад</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Выработка</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Штраф</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Итого</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Статус</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Дата расчёта</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {salaries.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                    Расчётов нет. Нажмите «Рассчитать» чтобы создать первый.
                  </TableCell>
                </TableRow>
              )}
              {salaries.map(s => {
                const emp = empById(s.employee_id)
                return (
                  <TableRow key={s.id} hover>
                    <TableCell>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <PersonRounded fontSize="small" color="action" />
                        <Box>
                          <Typography variant="body2" fontWeight={600}>{emp?.full_name ?? `#${s.employee_id}`}</Typography>
                          <Typography variant="caption" color="text.secondary">{emp ? POSITION_LABELS[emp.position] || emp.position : ''}</Typography>
                        </Box>
                      </Stack>
                    </TableCell>
                    <TableCell>{periodLabel(s.period_start, s.period_end)}</TableCell>
                    <TableCell align="right">{fmt(s.base_salary)}</TableCell>
                    <TableCell align="right" sx={{ color: Number(s.bonus) > 0 ? 'success.main' : 'inherit' }}>{fmt(s.bonus)}</TableCell>
                    <TableCell align="right" sx={{ color: Number(s.penalty) > 0 ? 'error.main' : 'inherit' }}>{fmt(s.penalty)}</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>{fmt(s.total)}</TableCell>
                    <TableCell><Chip label={STATUS_LABELS[s.status] || s.status} color={STATUS_COLORS[s.status] || 'default'} size="small" /></TableCell>
                    <TableCell>{fmtDate(s.created_at)}</TableCell>
                    <TableCell align="right">
                      {s.status === 'calculated' && (
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          startIcon={<CheckCircleRounded />}
                          onClick={() => handleOpenPayDialog(s)}
                          sx={{ borderRadius: 2 }}
                        >
                          Выплатить
                        </Button>
                      )}
                      {s.status === 'paid' && s.paid_at && (
                        <Typography variant="caption" color="text.secondary">{fmtDate(s.paid_at)}</Typography>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* ── Tab 1: Salary schemes ── */}
      {tab === 1 && (
        <TableContainer component={Paper} sx={{ borderRadius: 3, border: '1px solid #E2E8F0' }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#F8FAFC' }}>
                <TableCell sx={{ fontWeight: 700 }}>Сотрудник</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Должность</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Оклад</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="center">
                  <Tooltip title="% от суммы завершённых заказов (для механиков)">
                    <span>% выработки (механик)</span>
                  </Tooltip>
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="center">
                  <Tooltip title="% от суммы завершённых заказов менеджера (для менеджеров)">
                    <span>% выручки (менеджер)</span>
                  </Tooltip>
                </TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {employees.filter(e => e.is_active).map(emp => {
                const s = schemes[emp.id]
                return (
                  <TableRow key={emp.id} hover>
                    <TableCell sx={{ fontWeight: 600 }}>{emp.full_name}</TableCell>
                    <TableCell>{POSITION_LABELS[emp.position] || emp.position}</TableCell>
                    <TableCell>{fmt(emp.salary_base)}</TableCell>
                    <TableCell align="center">
                      {emp.position === 'mechanic' ? (
                        <Chip
                          label={`${s?.works_percentage ?? 0}%`}
                          color={Number(s?.works_percentage) > 0 ? 'primary' : 'default'}
                          size="small"
                        />
                      ) : '—'}
                    </TableCell>
                    <TableCell align="center">
                      {emp.position !== 'mechanic' ? (
                        <Chip
                          label={`${s?.revenue_percentage ?? 0}%`}
                          color={Number(s?.revenue_percentage) > 0 ? 'primary' : 'default'}
                          size="small"
                        />
                      ) : '—'}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleOpenSchemeEdit(emp)}>
                        <EditRounded fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* ── Calculate dialog ── */}
      <Dialog open={calcOpen} onClose={() => setCalcOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Рассчитать зарплату</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {calcError && <Alert severity="error">{calcError}</Alert>}
            <FormControl fullWidth size="small">
              <InputLabel>Сотрудник</InputLabel>
              <Select
                value={calcEmployeeId}
                label="Сотрудник"
                onChange={e => setCalcEmployeeId(Number(e.target.value))}
              >
                {employees.filter(e => e.is_active).map(e => (
                  <MenuItem key={e.id} value={e.id}>{e.full_name} — {POSITION_LABELS[e.position] || e.position}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Stack direction="row" spacing={1.5}>
              <TextField
                label="Начало периода"
                type="date"
                size="small"
                fullWidth
                value={calcPeriod.start}
                onChange={e => setCalcPeriod(p => ({ ...p, start: e.target.value }))}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                label="Конец периода"
                type="date"
                size="small"
                fullWidth
                value={calcPeriod.end}
                onChange={e => setCalcPeriod(p => ({ ...p, end: e.target.value }))}
                InputLabelProps={{ shrink: true }}
              />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              Базовый оклад + % от суммы завершённых заказов за период
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setCalcOpen(false)}>Отмена</Button>
          <Button
            variant="contained"
            onClick={handleCalculate}
            disabled={calculating}
            startIcon={calculating ? <CircularProgress size={16} color="inherit" /> : <CalculateRounded />}
          >
            Рассчитать
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Scheme edit dialog ── */}
      <Dialog open={schemeEditId !== null} onClose={() => setSchemeEditId(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Схема зарплаты — {schemeEditId ? empById(schemeEditId)?.full_name : ''}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {schemeEditId && empById(schemeEditId)?.position === 'mechanic' ? (
              <TextField
                label="% от суммы завершённых заказов (выработка)"
                size="small"
                type="number"
                fullWidth
                value={schemeWorks}
                onChange={e => setSchemeWorks(e.target.value)}
                InputProps={{ endAdornment: <PercentRounded fontSize="small" color="action" /> }}
                helperText="Берётся сумма заказов, где механик — данный сотрудник"
              />
            ) : (
              <TextField
                label="% от личной выручки (выручка менеджера)"
                size="small"
                type="number"
                fullWidth
                value={schemeRevenue}
                onChange={e => setSchemeRevenue(e.target.value)}
                InputProps={{ endAdornment: <PercentRounded fontSize="small" color="action" /> }}
                helperText="Берётся сумма заказов, где менеджер — данный сотрудник"
              />
            )}
            <Typography variant="caption" color="text.secondary">
              Зарплата = Оклад + (Сумма завершённых заказов × %) / 100
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setSchemeEditId(null)}>Отмена</Button>
          <Button
            variant="contained"
            onClick={handleSaveScheme}
            disabled={savingScheme}
            startIcon={savingScheme ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            Сохранить
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Pay dialog ── */}
      {(() => {
        const selectedAcc = accounts.find(a => a.id === selectedAccountId)
        const salaryTotal = Number(payDialogSalary?.total ?? 0)
        const insufficient = !!selectedAcc && selectedAcc.current_balance < salaryTotal
        return (
          <Dialog open={!!payDialogSalary} onClose={() => !paying && setPayDialogSalary(null)} maxWidth="xs" fullWidth>
            <DialogTitle sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccountBalanceWalletRounded color="success" />
              Выплата зарплаты
            </DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ pt: 1 }}>
                {payDialogSalary && (
                  <Box sx={{ p: 1.5, bgcolor: '#F8FAFC', borderRadius: 2 }}>
                    <Typography variant="body2" fontWeight={600}>
                      {empById(payDialogSalary.employee_id)?.full_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {periodLabel(payDialogSalary.period_start, payDialogSalary.period_end)} • <b>{fmt(salaryTotal)}</b>
                    </Typography>
                  </Box>
                )}
                <Typography variant="body2" fontWeight={600}>Списать со счёта:</Typography>
                {accounts.length === 0 ? (
                  <Alert severity="warning">Нет активных счетов. Создайте счёт в разделе Касса.</Alert>
                ) : (
                  <RadioGroup
                    value={selectedAccountId?.toString() ?? ''}
                    onChange={e => setSelectedAccountId(Number(e.target.value))}
                  >
                    {accounts.map(acc => {
                      const notEnough = acc.current_balance < salaryTotal
                      return (
                        <FormControlLabel
                          key={acc.id}
                          value={acc.id.toString()}
                          control={<Radio size="small" />}
                          label={
                            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ width: '100%', minWidth: 240 }}>
                              <Typography variant="body2" color={notEnough ? 'text.disabled' : 'inherit'}>
                                {acc.name}{' '}
                                <Typography component="span" variant="caption" color="text.secondary">
                                  ({acc.account_type === 'cash' ? 'Наличные' : 'Банк'})
                                </Typography>
                              </Typography>
                              <Typography variant="body2" fontWeight={600} color={notEnough ? 'error.main' : 'success.main'}>
                                {fmt(acc.current_balance)}
                              </Typography>
                            </Stack>
                          }
                        />
                      )
                    })}
                  </RadioGroup>
                )}
                {insufficient && (
                  <Alert severity="error">
                    Недостаточно средств на счёте «{selectedAcc?.name}». Не хватает {fmt(salaryTotal - selectedAcc!.current_balance)}.
                  </Alert>
                )}
              </Stack>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button onClick={() => setPayDialogSalary(null)} disabled={paying}>Отмена</Button>
              <Button
                variant="contained"
                color="success"
                disabled={paying || accounts.length === 0 || insufficient}
                startIcon={paying ? <CircularProgress size={16} color="inherit" /> : <CheckCircleRounded />}
                onClick={handleConfirmPay}
              >
                Выплатить
              </Button>
            </DialogActions>
          </Dialog>
        )
      })()}
    </Container>
  )
}
