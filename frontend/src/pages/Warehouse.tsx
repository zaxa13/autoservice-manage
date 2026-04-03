import { useState, useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Container,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Grid,
  Autocomplete,
  InputAdornment,
} from '@mui/material'
import { Search as SearchIcon } from '@mui/icons-material'
import {
  Add as AddIcon,
  Inventory2 as InventoryIcon,
  History as HistoryIcon,
  ReceiptLong as ReceiptIcon,
  WarningAmber as LowStockIcon,
  Edit as EditIcon,
  CheckCircle as PostIcon,
  Delete as DeleteIcon,
  Print as PrintIcon,
} from '@mui/icons-material'
import api from '../services/api'
import {
  WarehouseItem,
  WarehouseTransactionList,
  ReceiptDocument,
  ReceiptDocumentCreate,
  ReceiptLineCreate,
  Supplier,
  Part,
  WarehouseAdjustmentCreate,
} from '../types'

const TRANSACTION_TYPE_LABELS: Record<string, string> = {
  incoming: 'Приход',
  outgoing: 'Расход',
  adjustment: 'Корректировка',
}

export default function Warehouse() {
  const [tab, setTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Остатки (общий пулл запчастей)
  const [items, setItems] = useState<WarehouseItem[]>([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [itemsPartNumberSearch, setItemsPartNumberSearch] = useState('')
  const [adjustmentOpen, setAdjustmentOpen] = useState(false)
  const [adjustmentItem, setAdjustmentItem] = useState<WarehouseItem | null>(null)
  const [adjustmentDelta, setAdjustmentDelta] = useState('')
  const [adjustmentReason, setAdjustmentReason] = useState('')
  const [savingAdjustment, setSavingAdjustment] = useState(false)

  // Журнал движений
  const [transactions, setTransactions] = useState<WarehouseTransactionList[]>([])
  const [txDateFrom, setTxDateFrom] = useState('')
  const [txDateTo, setTxDateTo] = useState('')
  const [txTypeFilter, setTxTypeFilter] = useState<string>('')

  // Приходные накладные
  const [receipts, setReceipts] = useState<ReceiptDocument[]>([])
  const [receiptDialogOpen, setReceiptDialogOpen] = useState(false)
  const [receiptForm, setReceiptForm] = useState<ReceiptDocumentCreate>({
    document_date: new Date().toISOString().split('T')[0],
    supplier_id: undefined,
    supplier_document_number: '',
    supplier_document_date: undefined,
    lines: [{ part_id: 0, quantity: 1, purchase_price: 0, sale_price: 0 }],
  })
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [partsSearchQuery, setPartsSearchQuery] = useState('')
  const [partsSearchResults, setPartsSearchResults] = useState<Part[]>([])
  const [partsSearchLoading, setPartsSearchLoading] = useState(false)
  const [linePartCache, setLinePartCache] = useState<(Part | null)[]>([])
  const [savingReceipt, setSavingReceipt] = useState(false)
  const [postingReceiptId, setPostingReceiptId] = useState<number | null>(null)
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [receiptDetailOpen, setReceiptDetailOpen] = useState(false)
  const [selectedReceiptId, setSelectedReceiptId] = useState<number | null>(null)
  const [receiptDetail, setReceiptDetail] = useState<ReceiptDocument | null>(null)
  const [receiptDetailLoading, setReceiptDetailLoading] = useState(false)
  const [editingReceiptId, setEditingReceiptId] = useState<number | null>(null)

  const [addPartOpen, setAddPartOpen] = useState(false)
  const [addPartLineIndex, setAddPartLineIndex] = useState<number | null>(null)
  const [newPartForm, setNewPartForm] = useState({
    name: '',
    part_number: '',
    brand: '',
    price: 0,
    unit: 'шт',
    category: 'other' as Part['category'],
  })
  const [savingNewPart, setSavingNewPart] = useState(false)

  const [addSupplierOpen, setAddSupplierOpen] = useState(false)
  const [newSupplierForm, setNewSupplierForm] = useState({
    name: '',
    inn: '',
    kpp: '',
    legal_address: '',
    contact: '',
    bank_name: '',
    bik: '',
    bank_account: '',
    correspondent_account: '',
  })
  const [savingNewSupplier, setSavingNewSupplier] = useState(false)

  // Низкий остаток
  const [lowStock, setLowStock] = useState<WarehouseItem[]>([])
  const [searchParams, setSearchParams] = useSearchParams()
  const receiptFromUrlDoneRef = useRef(false)

  const loadItems = (partNumberOverride?: string) => {
    setItemsLoading(true)
    setError('')
    const raw = partNumberOverride !== undefined ? partNumberOverride : itemsPartNumberSearch
    const partNumber = raw.trim().toUpperCase()
    const params = partNumber ? { part_number: partNumber } : {}
    api
      .get<WarehouseItem[]>('/warehouse/items', { params })
      .then((r) => setItems(r.data))
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка загрузки остатков'))
      .finally(() => setItemsLoading(false))
  }

  const loadTransactions = () => {
    setLoading(true)
    setError('')
    const params: Record<string, string> = {}
    if (txDateFrom) params.date_from = txDateFrom
    if (txDateTo) params.date_to = txDateTo
    if (txTypeFilter) params.transaction_type = txTypeFilter
    api
      .get<WarehouseTransactionList[]>('/warehouse/transactions', { params })
      .then((r) => setTransactions(r.data))
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка загрузки журнала'))
      .finally(() => setLoading(false))
  }

  const openPdf = (path: string) => {
    api.get(path, { responseType: 'blob' }).then((res) => {
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    }).catch(() => setError('Ошибка генерации PDF'));
  };

  const loadReceipts = () => {
    setLoading(true)
    setError('')
    api
      .get<ReceiptDocument[]>('/warehouse/receipts')
      .then((r) => setReceipts(r.data))
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка загрузки накладных'))
      .finally(() => setLoading(false))
  }

  const loadLowStock = () => {
    setLoading(true)
    setError('')
    api
      .get<WarehouseItem[]>('/warehouse/low-stock')
      .then((r) => setLowStock(r.data))
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }

  const loadSuppliers = () => {
    api.get<Supplier[]>('/suppliers/').then((r) => setSuppliers(r.data)).catch(() => {})
  }

  const handleAddSupplierSubmit = () => {
    const name = newSupplierForm.name.trim()
    if (!name) {
      setError('Укажите название поставщика')
      return
    }
    setSavingNewSupplier(true)
    setError('')
    api
      .post<Supplier>('/suppliers/', {
        name,
        inn: newSupplierForm.inn.trim() || undefined,
        kpp: newSupplierForm.kpp.trim() || undefined,
        legal_address: newSupplierForm.legal_address.trim() || undefined,
        contact: newSupplierForm.contact.trim() || undefined,
        bank_name: newSupplierForm.bank_name.trim() || undefined,
        bik: newSupplierForm.bik.trim() || undefined,
        bank_account: newSupplierForm.bank_account.trim() || undefined,
        correspondent_account: newSupplierForm.correspondent_account.trim() || undefined,
      })
      .then((r) => {
        setSuppliers((prev) => [...prev, r.data])
        setReceiptForm((prev) => ({ ...prev, supplier_id: r.data.id }))
        setNewSupplierForm({
          name: '',
          inn: '',
          kpp: '',
          legal_address: '',
          contact: '',
          bank_name: '',
          bik: '',
          bank_account: '',
          correspondent_account: '',
        })
        setAddSupplierOpen(false)
      })
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка создания поставщика'))
      .finally(() => setSavingNewSupplier(false))
  }

  useEffect(() => {
    if (tab === 0) loadItems()
    else if (tab === 1) loadTransactions()
    else if (tab === 2) loadReceipts()
    else if (tab === 3) loadLowStock()
  }, [tab])

  useEffect(() => {
    if (tab === 1) loadTransactions()
  }, [tab, txDateFrom, txDateTo, txTypeFilter])

  // Открытие накладной по ссылке из другой вкладки (?tab=2&receipt=id)
  useEffect(() => {
    if (receiptFromUrlDoneRef.current) return
    const tabParam = searchParams.get('tab')
    const receiptId = searchParams.get('receipt')
    if (tabParam === '2' && receiptId) {
      const id = parseInt(receiptId, 10)
      if (id) {
        receiptFromUrlDoneRef.current = true
        setTab(2)
        setSelectedReceiptId(id)
        setReceiptDetailOpen(true)
        setSearchParams({}, { replace: true })
      }
    }
  }, [searchParams])

  useEffect(() => {
    if (receiptDialogOpen) {
      loadSuppliers()
      setLinePartCache(receiptForm.lines.map(() => null))
    }
  }, [receiptDialogOpen])

  useEffect(() => {
    if (receiptDetailOpen && selectedReceiptId != null) {
      setReceiptDetailLoading(true)
      api
        .get<ReceiptDocument>(`/warehouse/receipts/${selectedReceiptId}`)
        .then((r) => setReceiptDetail(r.data))
        .catch(() => setReceiptDetail(null))
        .finally(() => setReceiptDetailLoading(false))
    } else {
      setReceiptDetail(null)
    }
  }, [receiptDetailOpen, selectedReceiptId])

  useEffect(() => {
    if (!receiptDialogOpen) return
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    if (!partsSearchQuery.trim()) {
      setPartsSearchResults([])
      return
    }
    searchDebounceRef.current = setTimeout(() => {
      setPartsSearchLoading(true)
      api
        .get<Part[]>('/parts/', { params: { search: partsSearchQuery.trim(), limit: 50 } })
        .then((r) => setPartsSearchResults(r.data))
        .catch(() => setPartsSearchResults([]))
        .finally(() => setPartsSearchLoading(false))
    }, 300)
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    }
  }, [partsSearchQuery, receiptDialogOpen])

  const handleAdjustmentSubmit = () => {
    if (!adjustmentItem) return
    const delta = parseFloat(adjustmentDelta)
    if (Number.isNaN(delta) || delta === 0) {
      setError('Введите ненулевое изменение остатка')
      return
    }
    setSavingAdjustment(true)
    setError('')
    const payload: WarehouseAdjustmentCreate = {
      warehouse_item_id: adjustmentItem.id,
      quantity_delta: delta,
      reason: adjustmentReason || undefined,
    }
    api
      .post('/warehouse/transactions/adjustment', payload)
      .then(() => {
        setAdjustmentOpen(false)
        setAdjustmentItem(null)
        setAdjustmentDelta('')
        setAdjustmentReason('')
        loadItems()
      })
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка корректировки'))
      .finally(() => setSavingAdjustment(false))
  }

  const handleReceiptSubmit = () => {
    const lines = receiptForm.lines.filter((l) => l.part_id > 0 && l.quantity > 0)
    if (lines.length === 0) {
      setError('Добавьте хотя бы одну строку с запчастью и количеством')
      return
    }
    setSavingReceipt(true)
    setError('')
    const payload = {
      document_date: receiptForm.document_date,
      supplier_id: receiptForm.supplier_id,
      supplier_document_number: receiptForm.supplier_document_number || undefined,
      supplier_document_date: receiptForm.supplier_document_date,
      lines,
    }
    const req = editingReceiptId
      ? api.put<ReceiptDocument>(`/warehouse/receipts/${editingReceiptId}`, payload)
      : api.post<ReceiptDocument>('/warehouse/receipts', payload)
    req
      .then(() => {
        setReceiptDialogOpen(false)
        setEditingReceiptId(null)
        setReceiptForm({
          document_date: new Date().toISOString().split('T')[0],
          supplier_id: undefined,
          supplier_document_number: '',
          supplier_document_date: undefined,
          lines: [{ part_id: 0, quantity: 1, purchase_price: 0, sale_price: 0 }],
        })
        setLinePartCache([])
        loadReceipts()
      })
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка сохранения накладной'))
      .finally(() => setSavingReceipt(false))
  }

  const openEditReceipt = async (receipt: ReceiptDocument) => {
    setReceiptForm({
      document_date: receipt.document_date,
      supplier_id: receipt.supplier_id,
      supplier_document_number: receipt.supplier_document_number || '',
      supplier_document_date: receipt.supplier_document_date,
      lines: receipt.lines.map((l) => ({
        part_id: l.part_id,
        quantity: l.quantity,
        purchase_price: l.purchase_price,
        sale_price: l.sale_price,
      })),
    })
    setEditingReceiptId(receipt.id)
    setReceiptDetailOpen(false)
    setSelectedReceiptId(null)
    setReceiptDialogOpen(true)
    const cache: (Part | null)[] = await Promise.all(
      receipt.lines.map(async (l) => {
        if (l.part && l.part.id) return l.part
        if (l.part_id) {
          try {
            const { data } = await api.get<Part>(`/parts/${l.part_id}`)
            return data
          } catch {
            return null
          }
        }
        return null
      })
    )
    setLinePartCache(cache)
  }

  const handlePostReceipt = (id: number) => {
    setPostingReceiptId(id)
    setError('')
    api
      .post(`/warehouse/receipts/${id}/post`)
      .then(() => {
        loadReceipts()
        if (tab === 0) loadItems()
      })
      .catch((e) => setError(e.response?.data?.detail || 'Ошибка проведения'))
      .finally(() => setPostingReceiptId(null))
  }

  const addReceiptLine = () => {
    setReceiptForm((prev) => ({
      ...prev,
      lines: [...prev.lines, { part_id: 0, quantity: 1, purchase_price: 0, sale_price: 0 }],
    }))
    setLinePartCache((prev) => [...prev, null])
  }

  const updateReceiptLine = (index: number, field: keyof ReceiptLineCreate, value: number) => {
    setReceiptForm((prev) => {
      const next = { ...prev, lines: [...prev.lines] }
      next.lines[index] = { ...next.lines[index], [field]: value }
      if (field === 'purchase_price') {
        next.lines[index].sale_price = value
      }
      return next
    })
  }

  const removeReceiptLine = (index: number) => {
    setReceiptForm((prev) => {
      const newLines = prev.lines.filter((_, i) => i !== index)
      if (newLines.length === 0) {
        newLines.push({ part_id: 0, quantity: 1, purchase_price: 0, sale_price: 0 })
      }
      return { ...prev, lines: newLines }
    })
    setLinePartCache((prev) => {
      const next = prev.filter((_, i) => i !== index)
      if (next.length === 0) next.push(null)
      return next
    })
  }

  const clearPartInLine = (index: number) => {
    setReceiptForm((prev) => {
      const next = { ...prev, lines: [...prev.lines] }
      next.lines[index] = { ...next.lines[index], part_id: 0, purchase_price: 0, sale_price: 0 }
      return next
    })
    setLinePartCache((prev) => {
      const next = [...prev]
      next[index] = null
      return next
    })
    setPartsSearchQuery('')
  }

  const openAddPartForLine = (lineIndex: number) => {
    setAddPartLineIndex(lineIndex)
    setNewPartForm({
      name: partsSearchQuery.trim() || '',
      part_number: partsSearchQuery.trim() || '',
      brand: '',
      price: 0,
      unit: 'шт',
      category: 'other',
    })
    setAddPartOpen(true)
  }

  const handleAddPartSubmit = () => {
    if (addPartLineIndex == null) return
    const article = newPartForm.part_number.trim()
    if (!article) {
      setError('Укажите артикул запчасти (уникален в каталоге)')
      return
    }
    setSavingNewPart(true)
    setError('')
    // Сначала поиск по артикулу; если позиции нет в базе — тогда создаём новую карточку
    api
      .get<Part[]>('/parts/', { params: { search: article, limit: 20 } })
      .then((existing) => {
        const found = existing.data.some(
          (p) => p.part_number && p.part_number.toLowerCase() === article.toLowerCase()
        )
        if (found) {
          setError('Запчасть с таким артикулом уже есть в каталоге. Выберите её в поиске по артикулу.')
          setSavingNewPart(false)
          return undefined
        }
        if (!newPartForm.name.trim()) {
          setError('Укажите название запчасти')
          setSavingNewPart(false)
          return undefined
        }
        return api.post<Part>('/parts/', {
          name: newPartForm.name.trim(),
          part_number: article,
          brand: newPartForm.brand.trim() || undefined,
          price: newPartForm.price,
          unit: newPartForm.unit,
          category: newPartForm.category,
        })
      })
      .then((res) => {
        if (!res || !('data' in res)) return
        const part = res.data as Part
        updateReceiptLine(addPartLineIndex!, 'part_id', part.id)
        updateReceiptLine(addPartLineIndex!, 'sale_price', part.price)
        updateReceiptLine(addPartLineIndex!, 'purchase_price', part.purchase_price_last ?? part.price)
        setLinePartCache((prev) => {
          const next = [...prev]
          next[addPartLineIndex!] = part
          return next
        })
        setAddPartOpen(false)
        setAddPartLineIndex(null)
      })
      .catch((e) => {
        if (!e.response?.config?.url?.includes('?search=')) {
          setError(e.response?.data?.detail || 'Ошибка создания запчасти')
        }
      })
      .finally(() => setSavingNewPart(false))
  }

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h4" component="h1">
          Склад
        </Typography>
        {tab === 2 && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditingReceiptId(null)
              setReceiptForm({
                document_date: new Date().toISOString().split('T')[0],
                supplier_id: undefined,
                supplier_document_number: '',
                supplier_document_date: undefined,
                lines: [{ part_id: 0, quantity: 1, purchase_price: 0, sale_price: 0 }],
              })
              setLinePartCache([])
              setReceiptDialogOpen(true)
            }}
          >
            Создать накладную
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab icon={<InventoryIcon />} iconPosition="start" label="Остатки" />
        <Tab icon={<HistoryIcon />} iconPosition="start" label="Журнал движений" />
        <Tab icon={<ReceiptIcon />} iconPosition="start" label="Приходные накладные" />
        <Tab icon={<LowStockIcon />} iconPosition="start" label="Низкий остаток" />
      </Tabs>

      {loading && tab !== 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {tab === 0 && (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1.5 }}>
            <TextField
              size="small"
              placeholder="Поиск по артикулу (пробелы обрежутся, буквы — верхний регистр)"
              value={itemsPartNumberSearch}
              onChange={(e) => setItemsPartNumberSearch(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && loadItems()}
              sx={{ width: 320 }}
              InputProps={{
                startAdornment: <SearchIcon sx={{ color: 'text.secondary', mr: 1, fontSize: 20 }} />,
              }}
            />
            <Button
              variant="outlined"
              size="small"
              onClick={() => loadItems()}
              disabled={itemsLoading}
            >
              {itemsLoading ? <CircularProgress size={20} /> : 'Найти'}
            </Button>
            {itemsPartNumberSearch.trim() && (
              <Button size="small" onClick={() => { setItemsPartNumberSearch(''); loadItems(''); }} disabled={itemsLoading}>
                Сбросить
              </Button>
            )}
          </Box>
          <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1 }}>
            <Table size="small" padding="none" sx={{ '& .MuiTableCell-root': { py: 0.5, px: 1.25 }, '& .MuiTableRow-root': { '&:hover': { bgcolor: 'action.hover' } } }}>
              <TableHead>
                <TableRow>
                  <TableCell>Запчасть</TableCell>
                  <TableCell>Артикул</TableCell>
                  <TableCell align="right">Кол-во</TableCell>
                  <TableCell align="right">Мин. остаток</TableCell>
                  <TableCell>Место</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {itemsLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                      <CircularProgress size={28} />
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.part?.name}</TableCell>
                      <TableCell>{item.part?.part_number || '—'}</TableCell>
                      <TableCell align="right">{item.quantity}</TableCell>
                      <TableCell align="right">{item.min_quantity}</TableCell>
                      <TableCell>{item.location || '—'}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          startIcon={<EditIcon />}
                          onClick={() => {
                            setAdjustmentItem(item)
                            setAdjustmentOpen(true)
                            setAdjustmentDelta('')
                            setAdjustmentReason('')
                          }}
                          sx={{ minWidth: 0, px: 1 }}
                        >
                          Корректировка
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {!loading && tab === 1 && (
        <>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item>
              <TextField
                size="small"
                type="date"
                label="Дата с"
                value={txDateFrom}
                onChange={(e) => setTxDateFrom(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item>
              <TextField
                size="small"
                type="date"
                label="Дата по"
                value={txDateTo}
                onChange={(e) => setTxDateTo(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Тип</InputLabel>
                <Select
                  value={txTypeFilter}
                  label="Тип"
                  onChange={(e) => setTxTypeFilter(e.target.value)}
                >
                  <MenuItem value="">Все</MenuItem>
                  <MenuItem value="incoming">Приход</MenuItem>
                  <MenuItem value="outgoing">Расход</MenuItem>
                  <MenuItem value="adjustment">Корректировка</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Дата</TableCell>
                  <TableCell>Тип</TableCell>
                  <TableCell>Артикул</TableCell>
                  <TableCell>Запчасть</TableCell>
                  <TableCell align="right">Кол-во</TableCell>
                  <TableCell align="right">Цена</TableCell>
                  <TableCell>Основание</TableCell>
                  <TableCell>Сотрудник</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>
                      {t.created_at ? new Date(t.created_at).toLocaleString('ru') : '—'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={TRANSACTION_TYPE_LABELS[t.transaction_type] || t.transaction_type}
                        color={
                          t.transaction_type === 'incoming'
                            ? 'success'
                            : t.transaction_type === 'outgoing'
                              ? 'warning'
                              : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>{t.part?.part_number ?? '—'}</TableCell>
                    <TableCell>{t.part?.name ?? '—'}</TableCell>
                    <TableCell align="right">{t.quantity}</TableCell>
                    <TableCell align="right">{t.price != null ? t.price : '—'}</TableCell>
                    <TableCell>
                      {t.order_number && t.order_id != null ? (
                        <Link
                          to={`/orders?open=${t.order_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#2563eb', fontWeight: 500, textDecoration: 'none' }}
                        >
                          Заказ {t.order_number}
                        </Link>
                      ) : t.receipt_number && t.receipt_id != null ? (
                        <Link
                          to={`/warehouse?tab=2&receipt=${t.receipt_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#2563eb', fontWeight: 500, textDecoration: 'none' }}
                        >
                          Накл. {t.receipt_number}
                        </Link>
                      ) : (
                        <>{t.order_number && `Заказ ${t.order_number}`}{t.receipt_number && ` Накл. ${t.receipt_number}`}{!t.order_number && !t.receipt_number && '—'}</>
                      )}
                    </TableCell>
                    <TableCell>{t.employee_name || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {!loading && tab === 2 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Номер</TableCell>
                <TableCell>Дата</TableCell>
                <TableCell>Поставщик</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell align="right">Итого</TableCell>
                <TableCell align="right">Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {receipts.map((r) => (
                <TableRow
                  key={r.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedReceiptId(r.id)
                    setReceiptDetailOpen(true)
                  }}
                >
                  <TableCell>{r.number}</TableCell>
                  <TableCell>{r.document_date}</TableCell>
                  <TableCell>{r.supplier?.name || '—'}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={r.status === 'posted' ? 'Проведена' : 'Черновик'}
                      color={r.status === 'posted' ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="right">
                    {r.total_amount != null
                      ? Number(r.total_amount).toLocaleString('ru-RU', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })
                      : '—'}
                  </TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    {r.status === 'draft' && (
                      <Button
                        size="small"
                        startIcon={<PostIcon />}
                        onClick={() => handlePostReceipt(r.id)}
                        disabled={postingReceiptId === r.id}
                      >
                        Провести
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Диалог просмотра накладной */}
      <Dialog
        open={receiptDetailOpen}
        onClose={() => { setReceiptDetailOpen(false); setSelectedReceiptId(null) }}
        maxWidth={false}
        fullWidth
        PaperProps={{
          sx: { maxWidth: 'calc(100vw - 48px)', width: '100%', m: 1 }
        }}
      >
        <DialogTitle>
          Накладная {receiptDetail?.number ?? selectedReceiptId}
        </DialogTitle>
        <DialogContent>
          {receiptDetailLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          )}
          {!receiptDetailLoading && receiptDetail && (
            <Grid container spacing={2} sx={{ mt: 0 }}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">Дата</Typography>
                <Typography variant="body1">{receiptDetail.document_date}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">Поставщик</Typography>
                <Typography variant="body1">{receiptDetail.supplier?.name || '—'}</Typography>
              </Grid>
              {receiptDetail.supplier_document_number && (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">№ документа поставщика</Typography>
                  <Typography variant="body1">{receiptDetail.supplier_document_number}</Typography>
                </Grid>
              )}
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Строки</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Артикул</TableCell>
                        <TableCell>Название</TableCell>
                        <TableCell align="right">Кол-во</TableCell>
                        <TableCell align="right">Закупочная</TableCell>
                        <TableCell align="right">Продажная</TableCell>
                        <TableCell align="right">Сумма</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {receiptDetail.lines?.map((line) => (
                        <TableRow key={line.id}>
                          <TableCell>{line.part?.part_number ?? '—'}</TableCell>
                          <TableCell>{line.part?.name ?? '—'}</TableCell>
                          <TableCell align="right">{line.quantity}</TableCell>
                          <TableCell align="right">{line.purchase_price}</TableCell>
                          <TableCell align="right">{line.sale_price}</TableCell>
                          <TableCell align="right">
                            {(Number(line.quantity) * Number(line.purchase_price)).toLocaleString('ru-RU', {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle1">
                  Итого: {receiptDetail.total_amount != null
                    ? Number(receiptDetail.total_amount).toLocaleString('ru-RU', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })
                    : '—'}
                  {' '}₽
                </Typography>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setReceiptDetailOpen(false); setSelectedReceiptId(null) }}>
            Закрыть
          </Button>
          {receiptDetail && (
            <Button
              variant="outlined"
              startIcon={<PrintIcon />}
              onClick={() => openPdf(`/warehouse/receipts/${receiptDetail.id}/print`)}
            >
              Печать
            </Button>
          )}
          {receiptDetail?.status === 'draft' && (
            <>
              <Button
                variant="outlined"
                startIcon={<EditIcon />}
                onClick={() => receiptDetail && openEditReceipt(receiptDetail)}
              >
                Редактировать
              </Button>
              <Button
                variant="contained"
                startIcon={<PostIcon />}
                onClick={() => {
                  if (receiptDetail?.id) {
                    handlePostReceipt(receiptDetail.id)
                    setReceiptDetailOpen(false)
                    setSelectedReceiptId(null)
                    loadReceipts()
                  }
                }}
                disabled={postingReceiptId === receiptDetail?.id}
              >
                Провести
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>

      {!loading && tab === 3 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Запчасть</TableCell>
                <TableCell>Артикул</TableCell>
                <TableCell align="right">Остаток</TableCell>
                <TableCell align="right">Мин. остаток</TableCell>
                <TableCell>Место</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lowStock.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.part?.name}</TableCell>
                  <TableCell>{item.part?.part_number || '—'}</TableCell>
                  <TableCell align="right">{item.quantity}</TableCell>
                  <TableCell align="right">{item.min_quantity}</TableCell>
                  <TableCell>{item.location || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Диалог корректировки */}
      <Dialog open={adjustmentOpen} onClose={() => setAdjustmentOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Корректировка остатка</DialogTitle>
        <DialogContent>
          {adjustmentItem && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {adjustmentItem.part?.name} (текущий остаток: {adjustmentItem.quantity})
            </Typography>
          )}
          <TextField
            fullWidth
            label="Изменение (+ или -)"
            type="number"
            value={adjustmentDelta}
            onChange={(e) => setAdjustmentDelta(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Причина (необязательно)"
            value={adjustmentReason}
            onChange={(e) => setAdjustmentReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAdjustmentOpen(false)}>Отмена</Button>
          <Button
            variant="contained"
            onClick={handleAdjustmentSubmit}
            disabled={savingAdjustment || !adjustmentDelta}
          >
            {savingAdjustment ? <CircularProgress size={24} /> : 'Сохранить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог создания/редактирования накладной */}
      <Dialog
        open={receiptDialogOpen}
        onClose={() => {
          setReceiptDialogOpen(false)
          setEditingReceiptId(null)
        }}
        maxWidth={false}
        fullWidth
        PaperProps={{
          sx: { maxWidth: 'calc(100vw - 48px)', width: '100%', m: 1 }
        }}
      >
        <DialogTitle>
          {editingReceiptId ? 'Редактирование накладной' : 'Приходная накладная'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="Дата документа"
                type="date"
                value={receiptForm.document_date}
                onChange={(e) =>
                  setReceiptForm((prev) => ({ ...prev, document_date: e.target.value }))
                }
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Поставщик</InputLabel>
                <Select
                  value={receiptForm.supplier_id ?? ''}
                  label="Поставщик"
                  onChange={(e) => {
                    const v = e.target.value
                    if (v === '__add__') {
                      setAddSupplierOpen(true)
                      return
                    }
                    setReceiptForm((prev) => ({
                      ...prev,
                      supplier_id: v ? Number(v) : undefined,
                    }))
                  }}
                >
                  <MenuItem value="">Не выбран</MenuItem>
                  {suppliers.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name}
                    </MenuItem>
                  ))}
                  <MenuItem value="__add__" sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
                    + Добавить поставщика
                  </MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                label="№ документа поставщика"
                placeholder="например YT000147365"
                value={receiptForm.supplier_document_number || ''}
                onChange={(e) =>
                  setReceiptForm((prev) => ({
                    ...prev,
                    supplier_document_number: e.target.value || undefined,
                  }))
                }
              />
            </Grid>
          </Grid>
          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
            Строки
          </Typography>
          {receiptForm.lines.map((line, idx) => {
            const partSelected = !!linePartCache[idx]
            return (
              <Grid container key={idx} spacing={1} alignItems="center" sx={{ mb: 1 }}>
                {partSelected ? (
                  <>
                    <Grid item xs={2}>
                      <TextField
                        size="small"
                        fullWidth
                        label="Артикул"
                        value={linePartCache[idx]?.part_number ?? ''}
                        placeholder="—"
                        InputProps={{ readOnly: true }}
                        sx={{ '& .MuiInputBase-input': { cursor: 'default' } }}
                      />
                    </Grid>
                    <Grid item xs={3}>
                      <TextField
                        size="small"
                        fullWidth
                        label="Название"
                        value={linePartCache[idx]?.name ?? ''}
                        placeholder="—"
                        InputProps={{ readOnly: true }}
                        sx={{ '& .MuiInputBase-input': { cursor: 'default' } }}
                      />
                    </Grid>
                    <Grid item xs={1}>
                      <TextField
                        size="small"
                        fullWidth
                        type="number"
                        label="Кол-во"
                        value={line.quantity}
                        onChange={(e) =>
                          updateReceiptLine(idx, 'quantity', parseFloat(e.target.value) || 0)
                        }
                      />
                    </Grid>
                    <Grid item xs={2}>
                      <TextField
                        size="small"
                        fullWidth
                        type="number"
                        label="Закупочная"
                        value={line.purchase_price || ''}
                        onChange={(e) =>
                          updateReceiptLine(idx, 'purchase_price', parseFloat(e.target.value) || 0)
                        }
                      />
                    </Grid>
                    <Grid item xs={2}>
                      <TextField
                        size="small"
                        fullWidth
                        type="number"
                        label="Продажная"
                        value={line.sale_price || ''}
                        onChange={(e) =>
                          updateReceiptLine(idx, 'sale_price', parseFloat(e.target.value) || 0)
                        }
                      />
                    </Grid>
                    <Grid item xs={1} sx={{ minWidth: 48 }}>
                      <IconButton
                        size="small"
                        onClick={() => clearPartInLine(idx)}
                        title="Сменить запчасть"
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Grid>
                    <Grid item xs={1} sx={{ minWidth: 48 }}>
                      <IconButton
                        size="small"
                        onClick={() => removeReceiptLine(idx)}
                        title="Удалить строку"
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Grid>
                  </>
                ) : (
                  <>
                    <Grid item xs={6}>
                      <Autocomplete<Part | { id: number; name: string }>
                        size="small"
                        value={null}
                        inputValue={partsSearchQuery}
                        onInputChange={(_, v) => setPartsSearchQuery(v)}
                        onChange={(_, option) => {
                          if (option && 'id' in option) {
                            if (option.id === -1) {
                              openAddPartForLine(idx)
                              return
                            }
                            const part = option as Part
                            updateReceiptLine(idx, 'part_id', part.id)
                            updateReceiptLine(idx, 'sale_price', part.price)
                            updateReceiptLine(idx, 'purchase_price', part.purchase_price_last ?? part.price)
                            setLinePartCache((prev) => {
                              const next = [...prev]
                              next[idx] = part
                              return next
                            })
                            setPartsSearchQuery('')
                          }
                        }}
                        options={
                          partsSearchQuery.trim() && partsSearchResults.length === 0
                            ? [{ id: -1, name: `+ Добавить «${partsSearchQuery.trim()}»` }]
                            : partsSearchResults
                        }
                        getOptionLabel={(opt) =>
                          opt.id === -1 ? opt.name : `${'part_number' in opt ? opt.part_number : ''} — ${opt.name}`
                        }
                        loading={partsSearchLoading}
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            label="Поиск по артикулу"
                            placeholder="Введите артикул или выберите из списка"
                            InputProps={{
                              ...params.InputProps,
                              startAdornment: (
                                <>
                                  <InputAdornment position="start">
                                    <SearchIcon fontSize="small" color="action" />
                                  </InputAdornment>
                                  {params.InputProps.startAdornment}
                                </>
                              ),
                              endAdornment: (
                                <>
                                  {partsSearchLoading ? (
                                    <CircularProgress color="inherit" size={20} />
                                  ) : null}
                                  {params.InputProps.endAdornment}
                                </>
                              ),
                            }}
                          />
                        )}
                      />
                    </Grid>
                    <Grid item xs={1}>
                      <TextField
                        size="small"
                        fullWidth
                        type="number"
                        label="Кол-во"
                        value={line.quantity}
                        onChange={(e) =>
                          updateReceiptLine(idx, 'quantity', parseFloat(e.target.value) || 0)
                        }
                      />
                    </Grid>
                    <Grid item xs={2}>
                      <TextField
                        size="small"
                        fullWidth
                        type="number"
                        label="Закупочная"
                        value={line.purchase_price || ''}
                        onChange={(e) =>
                          updateReceiptLine(idx, 'purchase_price', parseFloat(e.target.value) || 0)
                        }
                      />
                    </Grid>
                    <Grid item xs={2}>
                      <TextField
                        size="small"
                        fullWidth
                        type="number"
                        label="Продажная"
                        value={line.sale_price || ''}
                        onChange={(e) =>
                          updateReceiptLine(idx, 'sale_price', parseFloat(e.target.value) || 0)
                        }
                      />
                    </Grid>
                    <Grid item xs={1} sx={{ minWidth: 48 }}>
                      <IconButton
                        size="small"
                        onClick={() => removeReceiptLine(idx)}
                        title="Удалить строку"
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Grid>
                  </>
                )}
              </Grid>
            )
          })}
          <Button startIcon={<AddIcon />} onClick={addReceiptLine} size="small">
            Добавить строку
          </Button>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setReceiptDialogOpen(false)
              setEditingReceiptId(null)
            }}
          >
            Отмена
          </Button>
          <Button variant="contained" onClick={handleReceiptSubmit} disabled={savingReceipt}>
            {savingReceipt ? <CircularProgress size={24} /> : editingReceiptId ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог добавления запчасти */}
      <Dialog open={addPartOpen} onClose={() => setAddPartOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Добавить запчасть</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Название"
                value={newPartForm.name}
                onChange={(e) => setNewPartForm((p) => ({ ...p, name: e.target.value }))}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Артикул"
                value={newPartForm.part_number}
                onChange={(e) => setNewPartForm((p) => ({ ...p, part_number: e.target.value }))}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Бренд"
                value={newPartForm.brand}
                onChange={(e) => setNewPartForm((p) => ({ ...p, brand: e.target.value }))}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Цена"
                value={newPartForm.price || ''}
                onChange={(e) => setNewPartForm((p) => ({ ...p, price: parseFloat(e.target.value) || 0 }))}
              />
            </Grid>
            <Grid item xs={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Ед. изм.</InputLabel>
                <Select
                  value={newPartForm.unit}
                  label="Ед. изм."
                  onChange={(e) => setNewPartForm((p) => ({ ...p, unit: e.target.value }))}
                >
                  <MenuItem value="шт">шт</MenuItem>
                  <MenuItem value="л">л</MenuItem>
                  <MenuItem value="кг">кг</MenuItem>
                  <MenuItem value="компл">компл</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Категория</InputLabel>
                <Select
                  value={newPartForm.category}
                  label="Категория"
                  onChange={(e) => setNewPartForm((p) => ({ ...p, category: e.target.value as Part['category'] }))}
                >
                  <MenuItem value="engine">Двигатель</MenuItem>
                  <MenuItem value="transmission">Трансмиссия</MenuItem>
                  <MenuItem value="suspension">Подвеска</MenuItem>
                  <MenuItem value="brakes">Тормоза</MenuItem>
                  <MenuItem value="electrical">Электрика</MenuItem>
                  <MenuItem value="body">Кузов</MenuItem>
                  <MenuItem value="consumables">Расходники</MenuItem>
                  <MenuItem value="other">Прочее</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddPartOpen(false)}>Отмена</Button>
          <Button variant="contained" onClick={handleAddPartSubmit} disabled={savingNewPart || !newPartForm.name.trim()}>
            {savingNewPart ? <CircularProgress size={24} /> : 'Добавить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог добавления поставщика */}
      <Dialog
        open={addSupplierOpen}
        onClose={() => {
          setAddSupplierOpen(false)
          setNewSupplierForm({
            name: '',
            inn: '',
            kpp: '',
            legal_address: '',
            contact: '',
            bank_name: '',
            bik: '',
            bank_account: '',
            correspondent_account: '',
          })
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Добавить поставщика</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Название"
                value={newSupplierForm.name}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="ООО Компания"
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="ИНН"
                value={newSupplierForm.inn}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, inn: e.target.value }))}
                placeholder="10 или 12 цифр"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="КПП"
                value={newSupplierForm.kpp}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, kpp: e.target.value }))}
                placeholder="9 цифр"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Юридический адрес"
                value={newSupplierForm.legal_address}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, legal_address: e.target.value }))}
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
                value={newSupplierForm.contact}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, contact: e.target.value }))}
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
                value={newSupplierForm.bank_name}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, bank_name: e.target.value }))}
                placeholder="необязательно"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="БИК"
                value={newSupplierForm.bik}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, bik: e.target.value }))}
                placeholder="9 цифр"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Корр. счёт"
                value={newSupplierForm.correspondent_account}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, correspondent_account: e.target.value }))}
                placeholder="20 цифр"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Расчётный счёт"
                value={newSupplierForm.bank_account}
                onChange={(e) => setNewSupplierForm((p) => ({ ...p, bank_account: e.target.value }))}
                placeholder="20 цифр"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddSupplierOpen(false)}>Отмена</Button>
          <Button variant="contained" onClick={handleAddSupplierSubmit} disabled={savingNewSupplier || !newSupplierForm.name.trim()}>
            {savingNewSupplier ? <CircularProgress size={24} /> : 'Добавить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
