import React, { useState, useEffect } from 'react'
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
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Chip,
  Collapse,
  IconButton,
} from '@mui/material'
import {
  KeyboardArrowDown as ExpandMoreIcon,
  KeyboardArrowUp as ExpandLessIcon,
  Summarize as ReportIcon,
} from '@mui/icons-material'
import api from '../services/api'
import { Supplier, SupplierReceiptsReport } from '../types'

function formatMoney(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatDate(s: string | undefined): string {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('ru-RU')
}

export default function SupplierReconciliation() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [supplierId, setSupplierId] = useState<number | ''>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [report, setReport] = useState<SupplierReceiptsReport | null>(null)
  const [expandedReceiptId, setExpandedReceiptId] = useState<number | null>(null)

  useEffect(() => {
    api
      .get<Supplier[]>('/suppliers/')
      .then((r) => setSuppliers(r.data))
      .catch(() => setError('Не удалось загрузить список поставщиков'))
  }, [])

  const handleRunReport = () => {
    if (supplierId === '') {
      setError('Выберите поставщика')
      return
    }
    setError('')
    setLoading(true)
    setReport(null)
    const params: Record<string, string> = { supplier_id: String(supplierId) }
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    api
      .get<SupplierReceiptsReport>('/warehouse/reports/supplier-receipts', { params })
      .then((r) => setReport(r.data))
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка загрузки отчёта'))
      .finally(() => setLoading(false))
  }

  const toggleExpand = (id: number) => {
    setExpandedReceiptId((prev) => (prev === id ? null : id))
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>
        Сверка по поставщику
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Отчёт по приходным накладным выбранного поставщика за период (по дате документа). Для сверки выберите поставщика и при необходимости укажите период «от» и «до».
      </Typography>

      <Paper variant="outlined" sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-end' }}>
          <FormControl sx={{ minWidth: 260 }} size="small">
            <InputLabel>Поставщик</InputLabel>
            <Select
              value={supplierId}
              label="Поставщик"
              onChange={(e) => setSupplierId(e.target.value === '' ? '' : Number(e.target.value))}
            >
              <MenuItem value="">Не выбран</MenuItem>
              {suppliers.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                  {s.inn ? ` (ИНН ${s.inn})` : ''}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Дата от"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160 }}
          />
          <TextField
            size="small"
            label="Дата по"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160 }}
          />
          <Button
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <ReportIcon />}
            onClick={handleRunReport}
            disabled={loading || supplierId === ''}
          >
            Сформировать
          </Button>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {report && (
        <>
          <Paper variant="outlined" sx={{ p: 2, mb: 2, borderRadius: 2, bgcolor: 'action.hover' }}>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', alignItems: 'center' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Документов: {report.total_count}
              </Typography>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Сумма прихода: {formatMoney(report.total_amount)}
              </Typography>
            </Box>
          </Paper>

          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell width={48} />
                  <TableCell>Номер</TableCell>
                  <TableCell>Дата док.</TableCell>
                  <TableCell>№ док. поставщика</TableCell>
                  <TableCell>Дата док. поставщика</TableCell>
                  <TableCell align="right">Сумма</TableCell>
                  <TableCell>Статус</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {report.receipts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                      За выбранный период накладных нет
                    </TableCell>
                  </TableRow>
                ) : (
                  report.receipts.map((r) => (
                    <React.Fragment key={r.id}>
                      <TableRow
                        key={r.id}
                        hover
                        sx={{ '& > *': { borderBottom: 'unset' } }}
                      >
                        <TableCell>
                          {r.lines && r.lines.length > 0 && (
                            <IconButton size="small" onClick={() => toggleExpand(r.id)}>
                              {expandedReceiptId === r.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            </IconButton>
                          )}
                        </TableCell>
                        <TableCell>{r.number}</TableCell>
                        <TableCell>{formatDate(r.document_date)}</TableCell>
                        <TableCell>{r.supplier_document_number || '—'}</TableCell>
                        <TableCell>{formatDate(r.supplier_document_date)}</TableCell>
                        <TableCell align="right">
                          {r.total_amount != null ? formatMoney(Number(r.total_amount)) : '—'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={r.status === 'posted' ? 'Проведён' : 'Черновик'}
                            color={r.status === 'posted' ? 'success' : 'default'}
                            variant="outlined"
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell colSpan={7} sx={{ py: 0, borderBottom: expandedReceiptId === r.id ? undefined : 0 }}>
                          <Collapse in={expandedReceiptId === r.id} timeout="auto" unmountOnExit>
                            <Box sx={{ py: 2, pl: 6 }}>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                                Состав накладной
                              </Typography>
                              <Table size="small" sx={{ mt: 1 }}>
                                <TableHead>
                                  <TableRow>
                                    <TableCell>Запчасть</TableCell>
                                    <TableCell align="right">Кол-во</TableCell>
                                    <TableCell align="right">Закупка</TableCell>
                                    <TableCell align="right">Сумма</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {r.lines?.map((line) => (
                                    <TableRow key={line.id}>
                                      <TableCell>
                                        {line.part
                                          ? `${line.part.part_number} — ${line.part.name}`
                                          : `ID ${line.part_id}`}
                                      </TableCell>
                                      <TableCell align="right">{Number(line.quantity)}</TableCell>
                                      <TableCell align="right">
                                        {formatMoney(Number(line.purchase_price))}
                                      </TableCell>
                                      <TableCell align="right">
                                        {formatMoney(Number(line.quantity) * Number(line.purchase_price))}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </React.Fragment>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Box>
  )
}
