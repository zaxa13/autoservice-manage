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
  CreditCardRounded, AccountBalanceWalletRounded, ContactPhoneRounded, SpeedRounded
} from '@mui/icons-material';
import api from '../services/api';
import { Order, OrderCreate, Vehicle, OrderWorkCreate, OrderPartCreate, Employee, OrderStatusInfo, OrderDetail, User, Customer, CustomerCreate } from '../types';

// Конфигурация цветов для статусов
const STATUS_COLORS: Record<string, "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning"> = {
  new: 'default', estimation: 'info', in_progress: 'primary', ready_for_payment: 'warning', paid: 'success', completed: 'success', cancelled: 'error',
};

const METHOD_ICONS: Record<string, any> = {
  cash: <LocalAtmRounded fontSize="small" />, card: <CreditCardRounded fontSize="small" />, yookassa: <AccountBalanceWalletRounded fontSize="small" />
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

  // --- СОСТОЯНИЯ ДИАЛОГА ---
  const [openDialog, setOpenDialog] = useState(false);
  const [editingOrderId, setEditingOrderId] = useState<number | null>(null);
  const [searchTab, setSearchTab] = useState(0);
  const [licensePlateSearch, setLicensePlateSearch] = useState('');
  const [vinSearch, setVinSearch] = useState('');
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [searchingVehicle, setSearchingVehicle] = useState(false);

  // --- СПРАВОЧНИКИ БРЕНДОВ И МОДЕЛЕЙ ---
  const [brands, setBrands] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // --- ДОБАВЛЕНИЕ/РЕДАКТИРОВАНИЕ АВТО ---
  const [openAddVehicleDialog, setOpenAddVehicleDialog] = useState(false);
  const [openEditVehicleDialog, setOpenEditVehicleDialog] = useState(false);
  const [searchingCustomer, setSearchingCustomer] = useState(false);
  const [foundCustomers, setFoundCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [customerSearchAttempted, setCustomerSearchAttempted] = useState(false);

  const [newVehicleData, setNewVehicleData] = useState({
    brand_id: '', model_id: '', license_plate: '', vin: '', year: new Date().getFullYear(), mileage: ''
  });
  const [newCustomerData, setNewCustomerData] = useState<CustomerCreate>({ full_name: '', phone: '', email: '' });

  // --- ОПЛАТЫ ---
  const [payments, setPayments] = useState<any[]>([]);
  const [openPaymentDialog, setOpenPaymentDialog] = useState(false);
  const [openResetConfirm, setOpenResetConfirm] = useState(false);
  const [isAdminEditPayment, setIsAdminEditPayment] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paidAmountFromServer, setPaidAmountFromServer] = useState(0);
  const [originalPaidAmount, setOriginalPaidAmount] = useState(0);

  // --- СКИДКИ ---
  const [globalDiscount, setGlobalDiscount] = useState<number>(0);
  const [applyToAll, setApplyToAll] = useState(false);

  // --- ФОРМА ЗАКАЗА ---
  const [formData, setFormData] = useState<OrderCreate & { status?: string }>({
    vehicle_id: 0, mechanic_id: undefined, status: 'new', recommendations: '', comments: '', order_works: [], order_parts: []
  });

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [ord, emp, st, me] = await Promise.all([
        api.get('/orders/'), api.get('/employees/'), api.get('/orders/statuses'), api.get('/auth/me')
      ]);
      setOrders(ord.data || []); setEmployees(emp.data || []); setOrderStatuses(st.data || []); setCurrentUser(me.data);
    } catch (e) { setError('Ошибка загрузки данных'); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadInitialData(); }, []);

  // Бренды
  useEffect(() => {
    if (openAddVehicleDialog || openEditVehicleDialog) {
      api.get('/vehicle-brands/').then(res => setBrands(res.data.brands || []));
    }
  }, [openAddVehicleDialog, openEditVehicleDialog]);

  const handleBrandChange = async (brandId: number) => {
    setNewVehicleData(prev => ({ ...prev, brand_id: brandId as any, model_id: '' }));
    setLoadingModels(true);
    try {
      const res = await api.post('/vehicle-brands/models', { brand_id: brandId });
      setModels(res.data.models || []);
    } catch (e) { setError('Ошибка загрузки моделей'); }
    finally { setLoadingModels(false); }
  };

  const getStatusLabel = (val: string) => orderStatuses.find(s => s.value === val)?.label || FALLBACK_LABELS[val] || val;
  const isAdmin = currentUser?.role === 'admin';
  const formatCurrency = (v: any) => new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(Number(v) || 0);

  const totals = useMemo(() => {
    const calc = (p: any, q: any, d: any) => (Number(p) * Number(q)) * (1 - (Number(d) || 0) / 100);
    const w = (formData.order_works || []).reduce((s, x) => s + calc(x.price, x.quantity, x.discount), 0);
    const p = (formData.order_parts || []).reduce((s, x) => s + calc(x.price, x.quantity, x.discount), 0);
    return { works: w, parts: p, grand: w + p };
  }, [formData.order_works, formData.order_parts]);

  const fetchOrderDetails = async (id: number) => {
    const res = await api.get(`/orders/${id}`);
    const d: OrderDetail = res.data;
    setSelectedVehicle(d.vehicle);
    setOriginalPaidAmount(Number(d.paid_amount || 0));
    setPaidAmountFromServer(Number(d.paid_amount || 0));
    setFormData({
      vehicle_id: d.vehicle_id, mechanic_id: d.mechanic_id, status: d.status, recommendations: d.recommendations || '', comments: d.comments || '',
      order_works: (d.order_works || []).map(w => ({ work_name: w.work?.name || (w as any).work_name || '', quantity: w.quantity, price: Number(w.price), discount: (w as any).discount || 0 })),
      order_parts: (d.order_parts || []).map(p => ({ part_name: p.part?.name || (p as any).part_name || '', quantity: p.quantity, price: Number(p.price), discount: (p as any).discount || 0 }))
    });
  };

  const loadOrderPayments = async (id: number) => {
    try {
      const res = await api.get(`/orders/${id}/payments`);
      setPayments(res.data || []);
    } catch (e) { console.error("Ошибка платежей"); }
  };

  const handleOpenDialog = async (order?: Order) => {
    setError(''); setApplyToAll(false); setGlobalDiscount(0);
    if (order) {
      setEditingOrderId(order.id);
      setSearchingVehicle(true);
      await fetchOrderDetails(order.id);
      await loadOrderPayments(order.id);
      setSearchingVehicle(false);
    } else {
      setEditingOrderId(null); setSelectedVehicle(null); setPaidAmountFromServer(0); setOriginalPaidAmount(0); setPayments([]);
      setFormData({ vehicle_id: 0, mechanic_id: undefined, status: 'new', order_works: [], order_parts: [], recommendations: '', comments: '' });
      setLicensePlateSearch(''); setVinSearch('');
    }
    setOpenDialog(true);
  };

  const handleOpenEditVehicle = async () => {
    if (!selectedVehicle) return;
    const bId = selectedVehicle.brand_id || (selectedVehicle.brand as any)?.id || '';
    setNewVehicleData({
      brand_id: bId as any,
      model_id: (selectedVehicle.model_id || (selectedVehicle.model as any)?.id || '') as any,
      license_plate: selectedVehicle.license_plate || '',
      vin: selectedVehicle.vin || '',
      year: selectedVehicle.year || new Date().getFullYear(),
      mileage: selectedVehicle.mileage?.toString() || ''
    });
    if (bId) {
        setLoadingModels(true);
        const res = await api.post('/vehicle-brands/models', { brand_id: bId });
        setModels(res.data.models || []);
        setLoadingModels(false);
    }
    setOpenEditVehicleDialog(true);
  };

  const handleUpdateVehicle = async () => {
    if (!selectedVehicle) return;
    try {
      setSaveLoading(true);
      await api.put(`/vehicles/${selectedVehicle.id}`, { ...newVehicleData, mileage: Number(newVehicleData.mileage) || 0 });
      if (editingOrderId) await fetchOrderDetails(editingOrderId);
      setOpenEditVehicleDialog(false);
    } catch (e) { setError('Не удалось обновить автомобиль'); }
    finally { setSaveLoading(false); }
  };

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
    } catch (e: any) {
      if (e.response?.status === 404) {
        setNewVehicleData({ brand_id: '', model_id: '', license_plate: licensePlateSearch.toUpperCase(), vin: vinSearch.toUpperCase(), year: new Date().getFullYear(), mileage: '' });
        setOpenAddVehicleDialog(true);
      } else { setError('Ошибка поиска'); }
    } finally { setSearchingVehicle(false); }
  };

  const handleSearchCustomer = async () => {
    if (!newCustomerData.phone || newCustomerData.phone.length < 5) return;
    setSearchingCustomer(true); setCustomerSearchAttempted(true);
    try {
      const res = await api.get('/customers/search/by-phone', { params: { phone: newCustomerData.phone } });
      setFoundCustomers(res.data || []);
      if (res.data?.length === 1) setSelectedCustomer(res.data[0]);
    } catch (e) { setFoundCustomers([]); setSelectedCustomer(null); }
    finally { setSearchingCustomer(false); }
  };

  const handleCreateVehicle = async () => {
    try {
      setSaveLoading(true);
      let cId = selectedCustomer?.id;
      if (!cId) { const res = await api.post('/customers/', newCustomerData); cId = res.data.id; }
      const res = await api.post('/vehicles/', { ...newVehicleData, mileage: Number(newVehicleData.mileage) || 0, customer_id: cId });
      setSelectedVehicle(res.data); setFormData(p => ({ ...p, vehicle_id: res.data.id }));
      setOpenAddVehicleDialog(false);
    } catch (e) { setError('Ошибка создания'); } finally { setSaveLoading(false); }
  };

  const handleSave = async (complete: boolean = false) => {
    if (!formData.vehicle_id) { setError('Выберите авто'); return; }
    setSaveLoading(true);
    try {
      const payload = { ...formData,
        order_works: (formData.order_works || []).map(w => ({ ...w, price: Number(w.price), quantity: Number(w.quantity), discount: Number(w.discount) })),
        order_parts: (formData.order_parts || []).map(p => ({ ...p, price: Number(p.price), quantity: Number(p.quantity), discount: Number(p.discount) }))
      };
      let id = editingOrderId;
      if (id) await api.put(`/orders/${id}`, payload);
      else { const res = await api.post('/orders/', payload); id = res.data.id; setEditingOrderId(id); }
      if (complete && id) {
        await api.post(`/orders/${id}/complete`);
        setOpenDialog(false);
        loadInitialData();
      } else if (id) {
        await fetchOrderDetails(id);
      }
      const list = await api.get('/orders/'); setOrders(list.data || []);
    } catch (err: any) { setError(err.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaveLoading(false); }
  };

  const handleCreatePayment = async () => {
    if (!editingOrderId) return;
    setSaveLoading(true);
    try {
      await api.post(`/orders/${editingOrderId}/payments`, { order_id: editingOrderId, amount: parseFloat(paymentAmount), payment_method: paymentMethod });
      await fetchOrderDetails(editingOrderId);
      await loadOrderPayments(editingOrderId);
      setOpenPaymentDialog(false); setPaymentAmount('');
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
    } catch (e) { setError('Ошибка сброса'); }
  };

  const handleCancelSinglePayment = async (pId: number) => {
    if (!isAdmin || !editingOrderId) return;
    try {
      await api.post(`/orders/${editingOrderId}/payments/${pId}/cancel`, {});
      await fetchOrderDetails(editingOrderId);
      await loadOrderPayments(editingOrderId);
    } catch (e) { setError('Ошибка отмены'); }
  };

  const addRow = (t: 'work' | 'part') => {
    const row = { work_name: '', part_name: '', quantity: 1, price: 0, discount: applyToAll ? globalDiscount : 0 };
    setFormData(p => t === 'work' ? ({ ...p, order_works: [...(p.order_works || []), row as any] }) : ({ ...p, order_parts: [...(p.order_parts || []), row as any] }));
  };

  const updateRow = (t: 'work' | 'part', i: number, f: string, v: any) => {
    const key = t === 'work' ? 'order_works' : 'order_parts';
    const list = [...(formData[key] || [])] as any[];
    if (list[i]) { list[i][f] = v; setFormData({ ...formData, [key]: list }); }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}><CircularProgress /></Box>;

  return (
    <Container maxWidth={false} sx={{ px: { xs: 2, md: 5 }, py: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 900 }}>Заказ-наряды</Typography>
        <Button variant="contained" size="large" startIcon={<AddRounded />} onClick={() => handleOpenDialog()} sx={{ borderRadius: 3, px: 4 }}>Создать заказ</Button>
      </Stack>

      <Box sx={{ mb: 3, borderBottom: '1px solid #E2E8F0' }}>
        <Tabs value={selectedStatusFilter} onChange={(_, v) => setSelectedStatusFilter(v)} variant="scrollable" scrollButtons="auto">
          <Tab label="Все" value="all" sx={{ fontWeight: 700 }} />
          {orderStatuses.map(s => <Tab key={s.value} label={s.label} value={s.value} sx={{ fontWeight: 700 }} />)}
          <Tab label="Завершен" value="completed" sx={{ fontWeight: 700 }} />
        </Tabs>
      </Box>

      <TableContainer component={Paper} sx={{ borderRadius: 4, border: '1px solid #E2E8F0', boxShadow: 'none' }}>
        <Table>
          <TableHead sx={{ bgcolor: '#F8FAFC' }}>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Номер</TableCell><TableCell sx={{ fontWeight: 700 }}>Автомобиль</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Мастер</TableCell><TableCell sx={{ fontWeight: 700 }}>Статус</TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>Сумма</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {orders.filter(o => selectedStatusFilter === 'all' || o.status === selectedStatusFilter).map(o => (
              <TableRow key={o.id} hover onClick={() => handleOpenDialog(o)} sx={{ cursor: 'pointer' }}>
                <TableCell sx={{ fontWeight: 600 }}>{o.number}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>{o.vehicle?.brand?.name} {o.vehicle?.model?.name}</Typography>
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

      <Dialog open={openDialog} fullScreen PaperProps={{ sx: { bgcolor: '#F8FAFC' } }}>
        <AppBar sx={{ position: 'sticky', bgcolor: '#fff', color: 'text.primary', boxShadow: 'none', borderBottom: '1px solid #E2E8F0', zIndex: 1100 }}>
          <Toolbar>
            <IconButton edge="start" onClick={() => setOpenDialog(false)} sx={{ mr: 2 }}><ArrowBackRounded /></IconButton>
            <Typography variant="h6" sx={{ flex: 1, fontWeight: 800 }}>{editingOrderId ? `Редактирование заказа` : 'Новый заказ-наряд'}</Typography>
            <Stack direction="row" spacing={2}>
              <Button variant="outlined" size="large" onClick={() => handleSave(false)} disabled={saveLoading} startIcon={<SaveRounded />}>Сохранить</Button>
              {paidAmountFromServer >= totals.grand - 0.01 && totals.grand > 0 && <Button variant="contained" color="success" onClick={() => handleSave(true)} disabled={saveLoading} startIcon={<CheckCircleRounded />}>Завершить заказ</Button>}
            </Stack>
          </Toolbar>
        </AppBar>

        <Box sx={{ p: 3 }}><Stack spacing={2} sx={{ maxWidth: '1600px', margin: '0 auto' }}>
          {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}><Paper sx={{ borderRadius: 3, border: '1px solid #E2E8F0', minHeight: 110, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              {!selectedVehicle ? (<Box><Tabs value={searchTab} onChange={(_, v) => setSearchTab(v)} sx={{ minHeight: 40 }}><Tab label="Гос. номер" sx={{ fontWeight: 700 }} /><Tab label="VIN номер" sx={{ fontWeight: 700 }} /></Tabs>
                <Stack direction="row" spacing={2} sx={{ p: 2 }}>
                  <TextField fullWidth size="small" placeholder={searchTab === 0 ? "А000АА77" : "17 символов или последние 6"} label={searchTab === 0 ? "Гос. номер" : "VIN-номер"} value={searchTab === 0 ? licensePlateSearch : vinSearch} onChange={e => searchTab === 0 ? setLicensePlateSearch(e.target.value.toUpperCase()) : setVinSearch(e.target.value.toUpperCase())} />
                  <Button variant="contained" onClick={handleSearchVehicle} disabled={searchingVehicle}>Найти</Button>
                </Stack></Box>
              ) : (<Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 3, py: 2, bgcolor: alpha('#4F46E5', 0.02) }}>
                  <Stack direction="row" spacing={2} alignItems="center"><Avatar sx={{ bgcolor: 'primary.main' }}><DirectionsCarFilledRounded /></Avatar><Box><Typography variant="subtitle1" sx={{ fontWeight: 800 }}>{selectedVehicle.brand?.name} {selectedVehicle.model?.name}</Typography><Typography variant="caption">{selectedVehicle.license_plate} • VIN: {selectedVehicle.vin} • Пробег: {selectedVehicle.mileage || 0} км • {selectedVehicle.customer?.full_name}</Typography></Box></Stack>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" variant="outlined" startIcon={<EditRounded />} onClick={handleOpenEditVehicle}>Редактировать</Button>
                    {!editingOrderId && <Button size="small" color="secondary" onClick={() => setSelectedVehicle(null)}>Сменить</Button>}
                  </Stack>
              </Stack>)}
            </Paper></Grid>
            <Grid item xs={12} md={3}><Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0', height: '100%', display: 'flex', alignItems: 'center' }}><FormControl fullWidth size="small"><InputLabel>Ответственный мастер</InputLabel><Select value={formData.mechanic_id || ''} label="Ответственный мастер" onChange={e => setFormData({ ...formData, mechanic_id: Number(e.target.value) })}>{employees.map(e => <MenuItem key={e.id} value={e.id}>{e.full_name}</MenuItem>)}</Select></FormControl></Paper></Grid>
            <Grid item xs={12} md={3}><Paper sx={{ p: 2.5, borderRadius: 3, border: '1px solid #E2E8F0', height: '100%', display: 'flex', alignItems: 'center' }}><FormControl fullWidth size="small"><InputLabel>Статус заказа</InputLabel><Select value={formData.status || 'new'} label="Статус заказа" onChange={e => setFormData({ ...formData, status: e.target.value })}>{orderStatuses.map(s => <MenuItem key={s.value} value={s.value}>{s.label}</MenuItem>)}</Select></FormControl></Paper></Grid>
          </Grid>

          {editingOrderId && (
            <Paper sx={{ p: 2, px: 3, borderRadius: 3, border: '1px solid #E2E8F0', bgcolor: '#fff' }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><HistoryRounded fontSize="small" color="primary" /> Оплаты: {formatCurrency(paidAmountFromServer)} / {formatCurrency(totals.grand)}</Typography>
                <Stack direction="row" spacing={1}>
                  {paidAmountFromServer < totals.grand - 0.01 && <Button variant="contained" color="success" size="small" startIcon={<PaymentRounded />} onClick={() => { setPaymentAmount((totals.grand - paidAmountFromServer).toFixed(0)); setOpenPaymentDialog(true); }}>Оплатить</Button>}
                  {isAdmin && <Button size="small" color="error" startIcon={<RestartAltRounded />} onClick={() => setOpenResetConfirm(true)}>Сбросить всё</Button>}
                </Stack>
              </Stack>
              <Table size="small">
                <TableBody>
                  {payments.map(p => (
                    <TableRow key={p.id}>
                      <TableCell sx={{ border: 'none', py: 0.5, width: 40 }}>{METHOD_ICONS[p.payment_method]}</TableCell>
                      <TableCell sx={{ border: 'none', py: 0.5 }}>{METHOD_LABELS[p.payment_method]} • {new Date(p.created_at).toLocaleString()}</TableCell>
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
          )}

          <Paper sx={{ px: 3, py: 1, borderRadius: 3, border: '1px solid #E2E8F0' }}><Stack direction="row" spacing={3} alignItems="center"><Typography variant="body2" sx={{ fontWeight: 800 }}>Глобальная скидка:</Typography><TextField type="number" size="small" sx={{ width: 80 }} value={globalDiscount} onChange={e => setGlobalDiscount(parseFloat(e.target.value) || 0)} InputProps={{ endAdornment: '%' }} /><FormControlLabel control={<Checkbox size="small" checked={applyToAll} onChange={e => setApplyToAll(e.target.checked)} />} label="Применить ко всем" /></Stack></Paper>

          <Box><Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, px: 1 }}><Typography variant="subtitle1" sx={{ fontWeight: 900 }}><BuildCircleRounded fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} /> Работы</Typography><Button variant="contained" size="small" startIcon={<AddRounded />} onClick={() => addRow('work')}>Добавить</Button></Stack>
            <Stack spacing={1}>{(formData.order_works || []).map((work, idx) => (<Paper key={idx} elevation={0} sx={{ p: 1.5, px: 2, borderRadius: 2, border: '1px solid #E2E8F0', bgcolor: '#fff', '&:hover': { borderColor: 'primary.main' } }}><Grid container spacing={2} alignItems="center">
              <Grid item xs={12} lg={6}><TextField fullWidth variant="standard" placeholder="Услуга..." value={work.work_name} onChange={e => updateRow('work', idx, 'work_name', e.target.value)} InputProps={{ disableUnderline: true, sx: { fontSize: '1rem', fontWeight: 700 } }} /></Grid>
              <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Кол-во" type="number" value={work.quantity} onChange={e => updateRow('work', idx, 'quantity', e.target.value)} /></Grid>
              <Grid item xs={3} lg={1.5}><TextField fullWidth size="small" label="Цена" type="number" value={work.price} onChange={e => updateRow('work', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
              <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Скидка" type="number" value={work.discount} onChange={e => updateRow('work', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
              <Grid item xs={2} lg={1.6} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(work.price) * Number(work.quantity)) * (1 - (Number(work.discount) || 0) / 100))}</Typography></Grid>
              <Grid item xs={1} lg={0.5}><IconButton color="error" size="small" onClick={() => removeRow('work', idx)}><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
            </Grid></Paper>))}</Stack></Box>

          <Box><Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, px: 1 }}><Typography variant="subtitle1" sx={{ fontWeight: 900 }}><ShoppingBagRounded fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} /> Запчасти</Typography><Button variant="contained" size="small" startIcon={<AddRounded />} onClick={() => addRow('part')}>Добавить</Button></Stack>
            <Stack spacing={1}>{(formData.order_parts || []).map((part, idx) => (<Paper key={idx} elevation={0} sx={{ p: 1.5, px: 2, borderRadius: 2, border: '1px solid #E2E8F0', bgcolor: '#fff', '&:hover': { borderColor: 'primary.main' } }}><Grid container spacing={2} alignItems="center">
              <Grid item xs={12} lg={6}><TextField fullWidth variant="standard" placeholder="Название..." value={part.part_name} onChange={e => updateRow('part', idx, 'part_name', e.target.value)} InputProps={{ disableUnderline: true, sx: { fontSize: '1rem', fontWeight: 700 } }} /></Grid>
              <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Кол-во" type="number" value={part.quantity} onChange={e => updateRow('part', idx, 'quantity', e.target.value)} /></Grid>
              <Grid item xs={3} lg={1.5}><TextField fullWidth size="small" label="Цена" type="number" value={part.price} onChange={e => updateRow('part', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
              <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Скидка" type="number" value={part.discount} onChange={e => updateRow('part', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
              <Grid item xs={2} lg={1.6} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(part.price) * Number(part.quantity)) * (1 - (Number(part.discount) || 0) / 100))}</Typography></Grid>
              <Grid item xs={1} lg={0.5}><IconButton color="error" size="small" onClick={() => removeRow('part', idx)}><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
            </Grid></Paper>))}</Stack></Box>

          <Collapse in={totals.grand > 0}><Paper sx={{ p: 2, px: 4, borderRadius: 3, border: '2px solid', borderColor: 'primary.main', bgcolor: '#fff' }}><Stack direction="row" justifyContent="space-between" alignItems="center"><Stack direction="row" spacing={4}><Box><Typography variant="caption">Работы</Typography><Typography variant="body1" sx={{ fontWeight: 700 }}>{formatCurrency(totals.works)}</Typography></Box><Box><Typography variant="caption">Запчасти</Typography><Typography variant="body1" sx={{ fontWeight: 700 }}>{formatCurrency(totals.parts)}</Typography></Box></Stack><Box sx={{ textAlign: 'right' }}><Typography variant="caption" color="primary" sx={{ fontWeight: 800 }}>ИТОГО</Typography><Typography variant="h4" sx={{ fontWeight: 950 }}>{formatCurrency(totals.grand)}</Typography></Box></Stack></Paper></Collapse>
          <Paper sx={{ p: 2, borderRadius: 3, border: '1px solid #E2E8F0' }}><Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><CommentRounded fontSize="small" color="action" /> Рекомендации</Typography><TextField fullWidth multiline rows={2} variant="outlined" size="small" value={formData.recommendations} onChange={e => setFormData({...formData, recommendations: e.target.value})} /></Paper>
        </Stack></Box>
      </Dialog>

      <Dialog open={openEditVehicleDialog} onClose={() => setOpenEditVehicleDialog(false)} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: 4 } }}>
        <DialogTitle sx={{ fontWeight: 800 }}>Редактировать автомобиль</DialogTitle>
        <DialogContent dividers sx={{ bgcolor: '#F8FAFC' }}>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <FormControl fullWidth><InputLabel>Марка *</InputLabel><Select value={newVehicleData.brand_id} label="Марка *" onChange={e => handleBrandChange(Number(e.target.value))}>{brands.map(b => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}</Select></FormControl>
            <FormControl fullWidth disabled={loadingModels}><InputLabel>Модель *</InputLabel><Select value={newVehicleData.model_id} label="Модель *" onChange={e => setNewVehicleData({...newVehicleData, model_id: e.target.value as any})}>{loadingModels ? <MenuItem disabled><CircularProgress size={20} /></MenuItem> : models.map(m => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}</Select></FormControl>
            <Stack direction="row" spacing={2}><TextField fullWidth label="Гос. номер" value={newVehicleData.license_plate} onChange={e => setNewVehicleData({...newVehicleData, license_plate: e.target.value.toUpperCase()})} /><TextField fullWidth label="Год" type="number" value={newVehicleData.year} onChange={e => setNewVehicleData({...newVehicleData, year: Number(e.target.value)})} /></Stack>
            <Stack direction="row" spacing={2}><TextField fullWidth label="VIN" value={newVehicleData.vin} onChange={e => setNewVehicleData({...newVehicleData, vin: e.target.value.toUpperCase()})} /><TextField fullWidth label="Пробег (км)" type="number" value={newVehicleData.mileage} onChange={e => setNewVehicleData({...newVehicleData, mileage: e.target.value})} /></Stack>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}><Button onClick={() => setOpenEditVehicleDialog(false)} color="inherit">Отмена</Button><Button variant="contained" onClick={handleUpdateVehicle} disabled={saveLoading}>Сохранить</Button></DialogActions>
      </Dialog>

      <Dialog open={openAddVehicleDialog} onClose={() => setOpenAddVehicleDialog(false)} maxWidth="md" fullWidth><DialogTitle sx={{ fontWeight: 800 }}>Новый автомобиль и владелец</DialogTitle>
        <DialogContent dividers sx={{ bgcolor: '#F8FAFC' }}><Grid container spacing={3} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}><Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 700 }}>АВТОМОБИЛЬ</Typography>
              <Stack spacing={2}><FormControl fullWidth><InputLabel>Марка *</InputLabel><Select value={newVehicleData.brand_id} label="Марка *" onChange={e => handleBrandChange(Number(e.target.value))}>{brands.map(b => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>)}</Select></FormControl>
                <FormControl fullWidth disabled={!newVehicleData.brand_id || loadingModels}><InputLabel>Модель *</InputLabel><Select value={newVehicleData.model_id} label="Модель *" onChange={e => setNewVehicleData({...newVehicleData, model_id: e.target.value as any})}>{loadingModels ? <MenuItem disabled><CircularProgress size={20} /></MenuItem> : models.map(m => <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}</Select></FormControl>
                <Stack direction="row" spacing={2}><TextField fullWidth label="Гос. номер" value={newVehicleData.license_plate} onChange={e => setNewVehicleData({...newVehicleData, license_plate: e.target.value.toUpperCase()})} /><TextField fullWidth label="Год" type="number" value={newVehicleData.year} onChange={e => setNewVehicleData({...newVehicleData, year: Number(e.target.value)})} /></Stack>
                <Stack direction="row" spacing={2}><TextField fullWidth label="VIN" value={newVehicleData.vin} onChange={e => setNewVehicleData({...newVehicleData, vin: e.target.value.toUpperCase()})} /><TextField fullWidth label="Пробег" type="number" value={newVehicleData.mileage} onChange={e => setNewVehicleData({...newVehicleData, mileage: e.target.value})} /></Stack>
              </Stack></Grid>
            <Grid item xs={12} md={6}><Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 700 }}>ВЛАДЕЛЕЦ</Typography>
              <Stack spacing={2}><TextField fullWidth label="Телефон *" value={newCustomerData.phone} onChange={e => {setNewCustomerData({...newCustomerData, phone: e.target.value}); setCustomerSearchAttempted(false);}} InputProps={{ endAdornment: <IconButton onClick={handleSearchCustomer} disabled={searchingCustomer}>{searchingCustomer ? <CircularProgress size={20} /> : <ContactPhoneRounded color="primary" />}</IconButton> }} />
                {selectedCustomer ? (<Paper sx={{ p: 2, bgcolor: alpha('#10B981', 0.05), border: '1px solid #10B981' }}><Typography variant="body1" sx={{ fontWeight: 700 }}>{selectedCustomer.full_name}</Typography><Button size="small" onClick={() => setSelectedCustomer(null)}>Другой</Button></Paper>
                ) : (<>{customerSearchAttempted && foundCustomers.length > 0 && <Stack spacing={1}>{foundCustomers.map(c => <Button key={c.id} variant="outlined" size="small" onClick={() => setSelectedCustomer(c)}>{c.full_name}</Button>)}</Stack>}<TextField fullWidth label="ФИО *" value={newCustomerData.full_name} onChange={e => setNewCustomerData({...newCustomerData, full_name: e.target.value})} /><TextField fullWidth label="Email" value={newCustomerData.email} onChange={e => setNewCustomerData({...newCustomerData, email: e.target.value})} /></>)}
              </Stack></Grid>
        </Grid></DialogContent><DialogActions sx={{ p: 3 }}><Button onClick={() => setOpenAddVehicleDialog(false)}>Отмена</Button><Button variant="contained" onClick={handleCreateVehicle} disabled={!newVehicleData.brand_id || !newVehicleData.model_id || (!selectedCustomer && !newCustomerData.full_name)}>Создать</Button></DialogActions></Dialog>

      <Dialog open={openPaymentDialog} onClose={() => setOpenPaymentDialog(false)} PaperProps={{ sx: { borderRadius: 3, p: 2, width: 340 } }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>Принять оплату</Typography><Stack spacing={2.5}><TextField fullWidth autoFocus type="number" value={paymentAmount} onChange={e => setPaymentAmount(e.target.value)} InputProps={{ endAdornment: '₽' }} /><FormControl fullWidth><InputLabel>Способ</InputLabel><Select value={paymentMethod} label="Способ" onChange={e => setPaymentMethod(e.target.value)}><MenuItem value="cash">Наличные</MenuItem><MenuItem value="card">Карта</MenuItem><MenuItem value="yookassa">ЮKassa</MenuItem></Select></FormControl><Stack direction="row" spacing={1} justifyContent="flex-end"><Button onClick={() => setOpenPaymentDialog(false)}>Отмена</Button><Button variant="contained" color="success" onClick={handleCreatePayment}>Подтвердить</Button></Stack></Stack></Dialog>

      <Dialog open={openResetConfirm} onClose={() => setOpenResetConfirm(false)} PaperProps={{ sx: { p: 2, maxWidth: 400, borderRadius: 4 } }}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5, fontWeight: 800 }}><WarningAmberRounded color="error" fontSize="large" /> Сброс оплат</DialogTitle>
        <DialogContent><DialogContentText sx={{ color: 'text.primary', fontWeight: 500 }}>Все проведенные платежи по этому заказу будут аннулированы. Продолжить?</DialogContentText></DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}><Button onClick={() => setOpenResetConfirm(false)} variant="outlined" color="inherit">Отмена</Button><Button onClick={handleCancelAllPayments} color="error" variant="contained">Да, сбросить</Button></DialogActions>
      </Dialog>
    </Container>
  );
}