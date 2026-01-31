import { useState, useEffect, useMemo } from 'react';
import {
  Container, Typography, Box, Button, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Dialog, TextField, IconButton, CircularProgress,
  Alert, Divider, Stack, alpha, AppBar, Toolbar, InputAdornment, Checkbox,
  FormControlLabel, Avatar, Tabs, Tab, Grid, Collapse, MenuItem, FormControl,
  InputLabel, Select, Chip, Tooltip, DialogTitle, DialogContent, DialogContentText, DialogActions
} from '@mui/material';
import {
  AddRounded, ArrowBackRounded, DeleteOutlineRounded, DirectionsCarFilledRounded,
  BuildCircleRounded, ShoppingBagRounded, PercentRounded, NumbersRounded, BadgeRounded,
  SaveRounded, CommentRounded, EngineeringRounded, PaymentRounded, CheckCircleRounded,
  EditRounded, RestartAltRounded, WarningAmberRounded, HistoryRounded, LocalAtmRounded,
  CreditCardRounded, AccountBalanceWalletRounded
} from '@mui/icons-material';
import api from '../services/api';
import { Order, OrderCreate, Vehicle, OrderWorkCreate, OrderPartCreate, Employee, OrderStatusInfo, OrderDetail, User } from '../types';

// Цветовая индикация статусов (value бэкенда -> цвет MUI)
const STATUS_COLORS: Record<string, "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning"> = {
  new: 'default',
  estimation: 'info',
  in_progress: 'primary',
  ready_for_payment: 'warning',
  paid: 'success',
  completed: 'success',
  cancelled: 'error',
};

// Иконки для способов оплаты
const METHOD_ICONS: Record<string, any> = {
  cash: <LocalAtmRounded fontSize="small" />,
  card: <CreditCardRounded fontSize="small" />,
  yookassa: <AccountBalanceWalletRounded fontSize="small" />
};

const METHOD_LABELS: Record<string, string> = { cash: 'Наличные', card: 'Карта', yookassa: 'ЮKassa' };
const FALLBACK_LABELS: Record<string, string> = { completed: 'Завершен', cancelled: 'Отменен' };

export default function Orders() {
  // --- СОСТОЯНИЯ ОСНОВНОГО СПИСКА ---
  const [orders, setOrders] = useState<Order[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [orderStatuses, setOrderStatuses] = useState<OrderStatusInfo[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState('all');

  // --- СОСТОЯНИЯ ДИАЛОГА ЗАКАЗА ---
  const [openDialog, setOpenDialog] = useState(false);
  const [editingOrderId, setEditingOrderId] = useState<number | null>(null);
  const [searchTab, setSearchTab] = useState(0); // 0 - Госномер, 1 - VIN
  const [licensePlateSearch, setLicensePlateSearch] = useState('');
  const [vinSearch, setVinSearch] = useState('');
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [searchingVehicle, setSearchingVehicle] = useState(false);

  // --- СОСТОЯНИЯ ОПЛАТЫ ---
  const [payments, setPayments] = useState<any[]>([]);
  const [openPaymentDialog, setOpenPaymentDialog] = useState(false);
  const [openResetConfirm, setOpenResetConfirm] = useState(false);
  const [isAdminEditPayment, setIsAdminEditPayment] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paidAmountFromServer, setPaidAmountFromServer] = useState(0);

  // --- СОСТОЯНИЯ СКИДОК ---
  const [globalDiscount, setGlobalDiscount] = useState<number>(0);
  const [applyToAll, setApplyToAll] = useState(false);

  // --- ДАННЫЕ ФОРМЫ ---
  const [formData, setFormData] = useState<OrderCreate & { status?: string }>({
    vehicle_id: 0,
    mechanic_id: undefined,
    status: 'new',
    recommendations: '',
    comments: '',
    order_works: [],
    order_parts: []
  });

  // --- ПЕРВИЧНАЯ ЗАГРУЗКА ---
  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [ord, emp, st, me] = await Promise.all([
        api.get('/orders/'),
        api.get('/employees/'),
        api.get('/orders/statuses'),
        api.get('/auth/me')
      ]);
      setOrders(ord.data || []);
      setEmployees(emp.data || []);
      setOrderStatuses(st.data || []);
      setCurrentUser(me.data);
    } catch (e) {
      setError('Ошибка загрузки данных с сервера');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadInitialData(); }, []);

  // --- ХЕЛПЕРЫ ---
  const formatCurrency = (v: any) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(Number(v) || 0);

  const getStatusLabel = (val: string) => {
    const statusObj = orderStatuses.find(s => s.value === val);
    return statusObj ? statusObj.label : (FALLBACK_LABELS[val] || val);
  };

  const isAdmin = currentUser?.role === 'admin';

  // Расчеты только для UI
  const totals = useMemo(() => {
    const calc = (p: any, q: any, d: any) => (Number(p) * Number(q)) * (1 - (Number(d) || 0) / 100);
    const w = (formData.order_works || []).reduce((s, x) => s + calc(x.price, x.quantity, x.discount), 0);
    const p = (formData.order_parts || []).reduce((s, x) => s + calc(x.price, x.quantity, x.discount), 0);
    return { works: w, parts: p, grand: w + p };
  }, [formData.order_works, formData.order_parts]);

  // --- ФУНКЦИИ СИНХРОНИЗАЦИИ ДАННЫХ ---
  const fetchOrderDetails = async (id: number) => {
    try {
      const res = await api.get(`/orders/${id}`);
      const d: OrderDetail = res.data;
      setSelectedVehicle(d.vehicle);
      setPaidAmountFromServer(Number(d.paid_amount || 0));
      setFormData({
        vehicle_id: d.vehicle_id,
        mechanic_id: d.mechanic_id,
        status: d.status,
        recommendations: d.recommendations || '',
        comments: d.comments || '',
        order_works: d.order_works.map(w => ({
          work_name: w.work?.name || (w as any).work_name,
          quantity: w.quantity,
          price: Number(w.price),
          discount: (w as any).discount || 0
        })),
        order_parts: d.order_parts.map(p => ({
          part_name: p.part?.name || (p as any).part_name,
          quantity: p.quantity,
          price: Number(p.price),
          discount: (p as any).discount || 0
        }))
      });
    } catch (e) { setError('Не удалось обновить данные заказа'); }
  };

  const loadOrderPayments = async (id: number) => {
    try {
      const res = await api.get(`/orders/${id}/payments`);
      setPayments(res.data || []);
    } catch (e) { console.error("Ошибка загрузки платежей"); }
  };

  const handleOpenDialog = async (order?: Order) => {
    setError('');
    setApplyToAll(false);
    setGlobalDiscount(0);
    if (order) {
      setEditingOrderId(order.id);
      setSearchingVehicle(true);
      await fetchOrderDetails(order.id);
      await loadOrderPayments(order.id);
      setSearchingVehicle(false);
    } else {
      setEditingOrderId(null);
      setSelectedVehicle(null);
      setPaidAmountFromServer(0);
      setPayments([]);
      setFormData({ vehicle_id: 0, mechanic_id: undefined, status: 'new', order_works: [], order_parts: [], recommendations: '', comments: '' });
      setLicensePlateSearch('');
      setVinSearch('');
    }
    setOpenDialog(true);
  };

  // --- ПОИСК ---
  const handleSearchVehicle = async () => {
    const val = searchTab === 0 ? licensePlateSearch : vinSearch;
    if (!val.trim()) return;
    setSearchingVehicle(true);
    try {
      const endpoint = searchTab === 0 ? 'by-license-plate' : 'by-vin';
      const params = searchTab === 0 ? { license_plate: val.toUpperCase() } : { vin: val.toUpperCase() };
      const res = await api.get(`/vehicles/search/${endpoint}`, { params });
      setSelectedVehicle(res.data);
      setFormData(prev => ({ ...prev, vehicle_id: res.data.id }));
    } catch (e) { setError('Транспортное средство не найдено'); }
    finally { setSearchingVehicle(false); }
  };

  // --- ОПЕРАЦИИ ОПЛАТЫ ---
  const handleCreatePayment = async () => {
    if (!editingOrderId) return;
    setSaveLoading(true);
    try {
      await api.post(`/orders/${editingOrderId}/payments`, {
        order_id: editingOrderId,
        amount: parseFloat(paymentAmount),
        payment_method: paymentMethod
      });
      await fetchOrderDetails(editingOrderId);
      await loadOrderPayments(editingOrderId);
      setOpenPaymentDialog(false);
      setPaymentAmount('');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка оплаты'); }
    finally { setSaveLoading(false); }
  };

  const handleCancelAllPayments = async () => {
    if (!isAdmin || !editingOrderId) return;
    try {
      await api.post(`/orders/${editingOrderId}/payments/cancel-all`, {});
      await fetchOrderDetails(editingOrderId);
      await loadOrderPayments(editingOrderId);
      setOpenResetConfirm(false);
    } catch (e) { setError('Ошибка при сбросе оплат'); }
  };

  const handleCancelSinglePayment = async (paymentId: number) => {
    if (!isAdmin || !editingOrderId) return;
    try {
      await api.post(`/orders/${editingOrderId}/payments/${paymentId}/cancel`, {});
      await fetchOrderDetails(editingOrderId);
      await loadOrderPayments(editingOrderId);
    } catch (e) { setError('Ошибка отмены платежа'); }
  };

  // --- СОХРАНЕНИЕ И ЗАВЕРШЕНИЕ ---
  const handleSave = async (complete: boolean = false) => {
    if (!formData.vehicle_id) { setError('Выберите авто'); return; }
    setSaveLoading(true);
    try {
      const payload = { ...formData,
        order_works: formData.order_works.map(w => ({ ...w, price: Number(w.price), quantity: Number(w.quantity), discount: Number(w.discount) })),
        order_parts: formData.order_parts.map(p => ({ ...p, price: Number(p.price), quantity: Number(p.quantity), discount: Number(p.discount) }))
      };

      let id = editingOrderId;
      if (id) {
        await api.put(`/orders/${id}`, payload);
      } else {
        const res = await api.post('/orders/', payload);
        id = res.data.id;
        setEditingOrderId(id);
      }

      if (complete && id) {
        await api.post(`/orders/${id}/complete`);
        setOpenDialog(false);
        loadInitialData();
      } else if (id) {
        await fetchOrderDetails(id);
      }
      const list = await api.get('/orders/');
      setOrders(list.data || []);
    } catch (err: any) { setError(err.response?.data?.detail || 'Ошибка при сохранении'); }
    finally { setSaveLoading(false); }
  };

  // --- УПРАВЛЕНИЕ СТРОКАМИ ---
  useEffect(() => {
    if (applyToAll) {
      setFormData(prev => ({ ...prev,
        order_works: (prev.order_works || []).map(w => ({ ...w, discount: globalDiscount })),
        order_parts: (prev.order_parts || []).map(p => ({ ...p, discount: globalDiscount }))
      }));
    }
  }, [globalDiscount, applyToAll]);

  const addRow = (type: 'work' | 'part') => {
    const newRow = { work_name: '', part_name: '', quantity: 1, price: 0, discount: applyToAll ? globalDiscount : 0 };
    if (type === 'work') setFormData(p => ({ ...p, order_works: [...p.order_works, newRow as any] }));
    else setFormData(p => ({ ...p, order_parts: [...p.order_parts, newRow as any] }));
  };

  const updateRow = (type: 'work' | 'part', index: number, field: string, value: any) => {
    const key = type === 'work' ? 'order_works' : 'order_parts';
    const newList = [...formData[key]] as any[];
    if (newList[index]) {
      newList[index][field] = value;
      setFormData({ ...formData, [key]: newList });
    }
  };

  const removeRow = (type: 'work' | 'part', index: number) => {
    const key = type === 'work' ? 'order_works' : 'order_parts';
    setFormData({ ...formData, [key]: (formData[key] || []).filter((_, idx) => idx !== index) });
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 10 }}><CircularProgress /></Box>;

  return (
    <Container maxWidth={false} sx={{ px: { xs: 2, md: 5 }, py: 2 }}>
      {/* HEADER СПИСКА */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: -1.5 }}>Заказ-наряды</Typography>
        <Button variant="contained" size="large" startIcon={<AddRounded />} onClick={() => handleOpenDialog()} sx={{ borderRadius: 3, px: 4 }}>Создать заказ</Button>
      </Stack>

      {/* ГОРИЗОНТАЛЬНЫЕ ТАБЫ ФИЛЬТРАЦИИ */}
      <Box sx={{ mb: 3, borderBottom: '1px solid #E2E8F0' }}>
        <Tabs value={selectedStatusFilter} onChange={(_, v) => setSelectedStatusFilter(v)} variant="scrollable" scrollButtons="auto">
          <Tab label="Все" value="all" sx={{ fontWeight: 700, textTransform: 'none' }} />
          {orderStatuses.map(s => <Tab key={s.value} label={s.label} value={s.value} sx={{ fontWeight: 700, textTransform: 'none' }} />)}
          {!orderStatuses.find(s => s.value === 'completed') && <Tab label="Завершен" value="completed" sx={{ fontWeight: 700, textTransform: 'none' }} />}
        </Tabs>
      </Box>

      {/* ТАБЛИЦА */}
      <TableContainer component={Paper} sx={{ borderRadius: 4, border: '1px solid #E2E8F0', boxShadow: 'none' }}>
        <Table>
          <TableHead sx={{ bgcolor: '#F8FAFC' }}>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Номер</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Автомобиль</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Мастер</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Статус</TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>Сумма</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {orders.filter(o => selectedStatusFilter === 'all' || o.status === selectedStatusFilter).map(o => (
              <TableRow key={o.id} hover onClick={() => handleOpenDialog(o)} sx={{ cursor: 'pointer' }}>
                <TableCell sx={{ fontWeight: 600 }}>{o.number}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>{o.vehicle?.brand} {o.vehicle?.model}</Typography>
                  <Typography variant="caption" color="text.secondary">({o.vehicle?.license_plate})</Typography>
                </TableCell>
                <TableCell>{o.mechanic?.full_name || '—'}</TableCell>
                <TableCell><Chip label={getStatusLabel(o.status)} color={STATUS_COLORS[o.status] || 'default'} size="small" sx={{ fontWeight: 700, borderRadius: 1.5 }} /></TableCell>
                <TableCell align="right" sx={{ fontWeight: 800 }}>{formatCurrency(o.total_amount)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* --- ДИАЛОГ КАРТОЧКИ ЗАКАЗА --- */}
      <Dialog open={openDialog} fullScreen PaperProps={{ sx: { bgcolor: '#F8FAFC' } }}>
        <AppBar sx={{ position: 'sticky', bgcolor: '#fff', color: 'text.primary', boxShadow: 'none', borderBottom: '1px solid #E2E8F0', zIndex: 1100 }}>
          <Toolbar>
            <IconButton edge="start" onClick={() => setOpenDialog(false)} sx={{ mr: 2 }}><ArrowBackRounded /></IconButton>
            <Typography variant="h6" sx={{ flex: 1, fontWeight: 800 }}>{editingOrderId ? `Заказ ${orders.find(o=>o.id===editingOrderId)?.number || ''}` : 'Новый заказ-наряд'}</Typography>
            <Stack direction="row" spacing={2}>
              <Button variant="outlined" size="large" onClick={() => handleSave(false)} disabled={saveLoading} startIcon={<SaveRounded />} sx={{ borderRadius: 2 }}>Сохранить</Button>
              {paidAmountFromServer >= totals.grand - 0.01 && totals.grand > 0 && (
                <Button variant="contained" color="success" size="large" onClick={() => handleSave(true)} disabled={saveLoading} startIcon={<CheckCircleRounded />} sx={{ borderRadius: 2, px: 4 }}>Завершить заказ</Button>
              )}
            </Stack>
          </Toolbar>
        </AppBar>

        <Box sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={2} sx={{ maxWidth: '1600px', margin: '0 auto' }}>
            {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}

            {/* 1. ВЕРХНЯЯ ПАНЕЛЬ: АВТО, МАСТЕР, СТАТУС */}
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ borderRadius: 3, overflow: 'hidden', border: '1px solid #E2E8F0', minHeight: 110, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  {!selectedVehicle ? (
                    <Box>
                      <Tabs value={searchTab} onChange={(_, v) => setSearchTab(v)} sx={{ bgcolor: '#F1F5F9', minHeight: 40 }}>
                        <Tab label="Гос. номер" sx={{ minHeight: 40, fontSize: '0.8rem', fontWeight: 700 }} />
                        <Tab label="VIN номер" sx={{ minHeight: 40, fontSize: '0.8rem', fontWeight: 700 }} />
                      </Tabs>
                      <Stack direction="row" spacing={2} sx={{ p: 2 }}>
                        <TextField
                          fullWidth size="small"
                          placeholder={searchTab === 0 ? "А000АА77" : "17 символов или последние 6"}
                          label={searchTab === 0 ? "Гос. номер" : "VIN-номер"}
                          value={searchTab === 0 ? licensePlateSearch : vinSearch}
                          onChange={e => searchTab === 0 ? setLicensePlateSearch(e.target.value.toUpperCase()) : setVinSearch(e.target.value.toUpperCase())}
                        />
                        <Button variant="contained" onClick={handleSearchVehicle} disabled={searchingVehicle}>Найти</Button>
                      </Stack>
                    </Box>
                  ) : (
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 3, py: 2, bgcolor: alpha('#4F46E5', 0.02), height: '100%' }}>
                      <Stack direction="row" spacing={2} alignItems="center">
                        <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48 }}><DirectionsCarFilledRounded /></Avatar>
                        <Box><Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>{selectedVehicle.brand} {selectedVehicle.model}</Typography><Typography variant="caption" color="text.secondary">{selectedVehicle.license_plate} • VIN: {selectedVehicle.vin}</Typography></Box>
                      </Stack>
                      {!editingOrderId && <Button size="small" variant="outlined" sx={{ borderRadius: 1.5 }} onClick={() => setSelectedVehicle(null)}>Изменить авто</Button>}
                    </Stack>
                  )}
                </Paper>
              </Grid>
              <Grid item xs={12} md={3}><Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0', height: '100%', display: 'flex', alignItems: 'center' }}><FormControl fullWidth size="small"><InputLabel>Ответственный мастер</InputLabel><Select value={formData.mechanic_id || ''} label="Ответственный мастер" onChange={e => setFormData({ ...formData, mechanic_id: Number(e.target.value) })}>{employees.map(emp => <MenuItem key={emp.id} value={emp.id}>{emp.full_name}</MenuItem>)}</Select></FormControl></Paper></Grid>
              <Grid item xs={12} md={3}><Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0', height: '100%', display: 'flex', alignItems: 'center' }}><FormControl fullWidth size="small"><InputLabel>Статус заказа</InputLabel><Select value={formData.status || 'new'} label="Статус заказа" onChange={e => setFormData({ ...formData, status: e.target.value })}>{orderStatuses.map(s => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}</Select></FormControl></Paper></Grid>
            </Grid>

            {/* 2. СКИДКА */}
            <Paper sx={{ px: 3, py: 1.5, borderRadius: 3, border: '1px solid #E2E8F0' }}>
              <Stack direction="row" spacing={3} alignItems="center">
                <Typography variant="body2" sx={{ fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><PercentRounded fontSize="small" color="primary" /> Глобальная скидка:</Typography>
                <TextField type="number" size="small" sx={{ width: 80 }} value={globalDiscount} onChange={e => setGlobalDiscount(parseFloat(e.target.value) || 0)} InputProps={{ endAdornment: '%' }} />
                <FormControlLabel control={<Checkbox size="small" checked={applyToAll} onChange={e => setApplyToAll(e.target.checked)} />} label={<Typography variant="body2" sx={{ fontWeight: 600 }}>Применить ко всем автоматически</Typography>} />
              </Stack>
            </Paper>

            {/* 3. ОПЛАТА + АДМИН-ФУНКЦИИ */}
            {editingOrderId && (
              <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                  <Paper sx={{ p: 2, px: 3, borderRadius: 3, border: '1px solid #E2E8F0', bgcolor: '#fff' }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><HistoryRounded fontSize="small" color="primary" /> История платежей</Typography>
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Typography variant="h6" sx={{ fontWeight: 900, color: 'success.dark' }}>{formatCurrency(paidAmountFromServer)} / {formatCurrency(totals.grand)}</Typography>
                        {paidAmountFromServer < totals.grand - 0.01 && <Button variant="contained" color="success" size="small" startIcon={<PaymentRounded />} onClick={() => { setPaymentAmount((totals.grand - paidAmountFromServer).toFixed(0)); setOpenPaymentDialog(true); }}>Оплатить</Button>}
                        {isAdmin && <Button size="small" color="error" startIcon={<RestartAltRounded />} onClick={() => setOpenResetConfirm(true)}>Сброс</Button>}
                      </Stack>
                    </Stack>
                    <Table size="small">
                      <TableBody>
                        {payments.length === 0 ? <TableRow><TableCell colSpan={4} align="center" sx={{ py: 2, color: 'text.secondary' }}>Платежей пока нет</TableCell></TableRow> :
                        payments.map(p => (
                          <TableRow key={p.id}>
                            <TableCell sx={{ border: 'none', py: 0.5, width: 40 }}>{METHOD_ICONS[p.payment_method]}</TableCell>
                            <TableCell sx={{ border: 'none', py: 0.5 }}>{METHOD_LABELS[p.payment_method]} • {new Date(p.created_at).toLocaleString('ru-RU')}</TableCell>
                            <TableCell sx={{ border: 'none', py: 0.5, fontWeight: 700 }}>{formatCurrency(p.amount)}</TableCell>
                            <TableCell sx={{ border: 'none', py: 0.5 }} align="right">
                              {isAdmin && p.status === 'succeeded' && <IconButton size="small" color="error" onClick={() => handleCancelSinglePayment(p.id)}><DeleteOutlineRounded fontSize="small" /></IconButton>}
                              <Chip label={p.status} size="small" variant="outlined" sx={{ ml: 1, fontSize: '0.6rem', height: 20 }} />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Paper>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Collapse in={totals.grand > 0}>
                    <Paper sx={{ p: 2, px: 3, borderRadius: 3, border: '2px solid', borderColor: 'primary.main', bgcolor: '#fff', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <Typography variant="caption" color="primary" sx={{ fontWeight: 800, textTransform: 'uppercase' }}>Итого к оплате</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 950, color: 'text.primary', letterSpacing: -1 }}>{formatCurrency(totals.grand)}</Typography>
                      <Stack direction="row" spacing={2} sx={{ mt: 1 }}><Typography variant="caption">Работы: {formatCurrency(totals.works)}</Typography><Typography variant="caption">Детали: {formatCurrency(totals.parts)}</Typography></Stack>
                    </Paper>
                  </Collapse>
                </Grid>
              </Grid>
            )}

            {/* 4. РАБОТЫ */}
            <Box>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, px: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 900 }}><BuildCircleRounded fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} /> Выполненные работы</Typography>
                <Button variant="contained" size="small" startIcon={<AddRounded />} onClick={() => addRow('work')} sx={{ borderRadius: 2 }}>Добавить</Button>
              </Stack>
              <Stack spacing={1}>
                {(formData.order_works || []).map((work, idx) => (
                  <Paper key={idx} elevation={0} sx={{ p: 1.5, px: 2, borderRadius: 2, border: '1px solid #E2E8F0', bgcolor: '#fff', '&:hover': { borderColor: 'primary.main' } }}>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} lg={6}><TextField fullWidth variant="standard" placeholder="Название услуги..." value={work.work_name} onChange={e => updateRow('work', idx, 'work_name', e.target.value)} InputProps={{ disableUnderline: true, sx: { fontSize: '1rem', fontWeight: 700 } }} /></Grid>
                      <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Кол-во" type="number" value={work.quantity} onChange={e => updateRow('work', idx, 'quantity', e.target.value)} /></Grid>
                      <Grid item xs={3} lg={1.5}><TextField fullWidth size="small" label="Цена" type="number" value={work.price} onChange={e => updateRow('work', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
                      <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Скидка" type="number" value={work.discount} onChange={e => updateRow('work', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
                      <Grid item xs={2} lg={1.6} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(work.price) * Number(work.quantity)) * (1 - (Number(work.discount) || 0) / 100))}</Typography></Grid>
                      <Grid item xs={1} lg={0.5}><IconButton size="small" color="error" onClick={() => removeRow('work', idx)}><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
                    </Grid>
                  </Paper>
                ))}
              </Stack>
            </Box>

            {/* 5. ЗАПЧАСТИ */}
            <Box>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, px: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 900 }}><ShoppingBagRounded fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} /> Запчасти и расходники</Typography>
                <Button variant="contained" size="small" startIcon={<AddRounded />} onClick={() => addRow('part')} sx={{ borderRadius: 2 }}>Добавить</Button>
              </Stack>
              <Stack spacing={1}>
                {(formData.order_parts || []).map((part, idx) => (
                  <Paper key={idx} elevation={0} sx={{ p: 1.5, px: 2, borderRadius: 2, border: '1px solid #E2E8F0', bgcolor: '#fff', '&:hover': { borderColor: 'primary.main' } }}>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} lg={6}><TextField fullWidth variant="standard" placeholder="Название запчасти..." value={part.part_name} onChange={e => updateRow('part', idx, 'part_name', e.target.value)} InputProps={{ disableUnderline: true, sx: { fontSize: '1rem', fontWeight: 700 } }} /></Grid>
                      <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Кол-во" type="number" value={part.quantity} onChange={e => updateRow('part', idx, 'quantity', e.target.value)} /></Grid>
                      <Grid item xs={3} lg={1.5}><TextField fullWidth size="small" label="Цена" type="number" value={part.price} onChange={e => updateRow('part', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
                      <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Скидка" type="number" value={part.discount} onChange={e => updateRow('part', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
                      <Grid item xs={2} lg={1.6} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(part.price) * Number(part.quantity)) * (1 - (Number(part.discount) || 0) / 100))}</Typography></Grid>
                      <Grid item xs={1} lg={0.5}><IconButton size="small" color="error" onClick={() => removeRow('part', idx)}><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
                    </Grid>
                  </Paper>
                ))}
              </Stack>
            </Box>

            {/* 6. РЕКОМЕНДАЦИИ */}
            <Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0' }}>
              <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><CommentRounded fontSize="small" color="action" /> Рекомендации мастерской</Typography>
              <TextField fullWidth multiline rows={2} variant="outlined" size="small" value={formData.recommendations} onChange={e => setFormData({...formData, recommendations: e.target.value})} sx={{ '& .MuiOutlinedInput-root': { bgcolor: alpha('#F8FAFC', 0.8) } }} />
            </Paper>

          </Stack>
        </Box>
      </Dialog>

      {/* МОДАЛКИ ОПЛАТЫ */}
      <Dialog open={openPaymentDialog} onClose={() => setOpenPaymentDialog(false)} PaperProps={{ sx: { borderRadius: 3, p: 2, width: 340 } }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>Принять оплату</Typography>
        <Stack spacing={2.5}>
          <TextField fullWidth autoFocus label="Сумма платежа" type="number" value={paymentAmount} onChange={e => setPaymentAmount(e.target.value)} InputProps={{ endAdornment: '₽' }} />
          <FormControl fullWidth><InputLabel>Способ</InputLabel><Select value={paymentMethod} label="Способ" onChange={e => setPaymentMethod(e.target.value)}><MenuItem value="cash">Наличные</MenuItem><MenuItem value="card">Карта</MenuItem><MenuItem value="yookassa">ЮKassa</MenuItem></Select></FormControl>
          <Stack direction="row" spacing={1} justifyContent="flex-end"><Button onClick={() => setOpenPaymentDialog(false)} color="inherit">Отмена</Button><Button variant="contained" color="success" onClick={handleCreatePayment}>Подтвердить</Button></Stack>
        </Stack>
      </Dialog>

      <Dialog open={openResetConfirm} onClose={() => setOpenResetConfirm(false)} PaperProps={{ sx: { borderRadius: 4, p: 2, maxWidth: 400 } }}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5, fontWeight: 800 }}><WarningAmberRounded color="error" fontSize="large" /> Сброс оплат</DialogTitle>
        <DialogContent><DialogContentText sx={{ color: 'text.primary', fontWeight: 500 }}>Все платежи по этому заказу будут аннулированы. Продолжить?</DialogContentText></DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}><Button onClick={() => setOpenResetConfirm(false)} variant="outlined" color="inherit">Отмена</Button><Button onClick={handleCancelAllPayments} color="error" variant="contained">Да, сбросить</Button></DialogActions>
      </Dialog>
    </Container>
  );
}