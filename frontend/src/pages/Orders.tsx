import { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Container, Typography, Box, Button, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Dialog, TextField, IconButton, CircularProgress,
  Alert, Divider, Stack, alpha, AppBar, Toolbar, InputAdornment, Checkbox,
  FormControlLabel, Avatar, Tabs, Tab, Grid, Collapse, MenuItem, FormControl,
  InputLabel, Select, Chip, Tooltip, DialogTitle, DialogContent, DialogContentText, DialogActions,
  Autocomplete, Snackbar, Popover
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import {
  AddRounded, ArrowBackRounded, DeleteOutlineRounded, DirectionsCarFilledRounded,
  BuildCircleRounded, ShoppingBagRounded, PercentRounded, NumbersRounded, BadgeRounded,
  SaveRounded, CommentRounded, EngineeringRounded, PaymentRounded, CheckCircleRounded,
  EditRounded, RestartAltRounded, WarningAmberRounded, HistoryRounded, LocalAtmRounded,
  CreditCardRounded, AccountBalanceWalletRounded, ContactPhoneRounded, SpeedRounded,
  PhoneRounded, PersonRounded, SearchOffRounded, ContentCopyRounded,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import api from '../services/api';
import { Order, OrderCreate, Vehicle, OrderWorkCreate, OrderPartCreate, Employee, OrderStatusInfo, OrderDetail, User, Customer, CustomerCreate, Part, Work } from '../types';

// Категории работ
const WORK_CATEGORIES: { value: string; label: string; color: string }[] = [
  { value: 'diagnostics', label: 'Диагностика', color: '#6366f1' },
  { value: 'engine', label: 'Двигатель', color: '#ef4444' },
  { value: 'transmission', label: 'КПП', color: '#f97316' },
  { value: 'suspension', label: 'Подвеска', color: '#eab308' },
  { value: 'brakes', label: 'Тормоза', color: '#dc2626' },
  { value: 'electrical', label: 'Электрика', color: '#3b82f6' },
  { value: 'cooling', label: 'Охлаждение', color: '#06b6d4' },
  { value: 'fuel_system', label: 'Топливо', color: '#84cc16' },
  { value: 'exhaust', label: 'Выхлоп', color: '#78716c' },
  { value: 'climate', label: 'Климат', color: '#0ea5e9' },
  { value: 'maintenance', label: 'ТО', color: '#22c55e' },
  { value: 'body_work', label: 'Кузов', color: '#a855f7' },
  { value: 'painting', label: 'Покраска', color: '#ec4899' },
  { value: 'tire_service', label: 'Шиномонтаж', color: '#14b8a6' },
  { value: 'glass', label: 'Стёкла', color: '#64748b' },
  { value: 'other', label: 'Прочее', color: '#94a3b8' },
];

// Конфигурация цветов для статусов
const STATUS_COLORS: Record<string, "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning"> = {
  new: 'default', estimation: 'info', in_progress: 'primary', ready_for_payment: 'warning', paid: 'success', completed: 'success', cancelled: 'error',
};

const METHOD_ICONS: Record<string, any> = {
  cash: <LocalAtmRounded fontSize="small" />,
  card: <CreditCardRounded fontSize="small" />,
  yookassa: <AccountBalanceWalletRounded fontSize="small" />
};

const METHOD_LABELS: Record<string, string> = { 
  cash: 'Наличные', 
  card: 'Карта', 
  yookassa: 'ЮKassa' 
};
const FALLBACK_LABELS: Record<string, string> = { completed: 'Завершен', cancelled: 'Отменен' };
const PAYMENT_STATUS_LABELS: Record<string, string> = { 
  succeeded: 'Проведён', 
  cancelled: 'Отменён', 
  pending: 'В обработке', 
  failed: 'Ошибка' 
};

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
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteOrderConfirm, setDeleteOrderConfirm] = useState<Order | null>(null);
  const [deletingOrder, setDeletingOrder] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // --- ПОИСК РАБОТ ИЗ КАТАЛОГА ---
  const [worksSearchQuery, setWorksSearchQuery] = useState('');
  const [worksSearchCategory, setWorksSearchCategory] = useState('');
  const [allWorks, setAllWorks] = useState<Work[]>([]);
  const [worksSearchLoading, setWorksSearchLoading] = useState(false);
  const [editingWorkIdx, setEditingWorkIdx] = useState<number | null>(null);

  // --- CREATE ON THE FLY ---
  const [createPopover, setCreatePopover] = useState<{ anchorEl: HTMLElement; name: string; rowIdx: number } | null>(null);
  const [createCategory, setCreateCategory] = useState('');
  const [creatingWork, setCreatingWork] = useState(false);
  const workRowRefs = useRef<{ [idx: number]: HTMLDivElement | null }>({});
  const preventBlurReset = useRef(false);
  const skipNextFocus = useRef(false);

  // --- INLINE ПРОБЕГ ---
  const [inlineMileage, setInlineMileage] = useState('');
  const [savingMileage, setSavingMileage] = useState(false);

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
  const [editingPaymentId, setEditingPaymentId] = useState<number | null>(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paidAmountFromServer, setPaidAmountFromServer] = useState(0);
  const [originalPaidAmount, setOriginalPaidAmount] = useState(0);

  // --- СКИДКИ ---
  const [globalDiscount, setGlobalDiscount] = useState<number>(0);
  const [applyToAll, setApplyToAll] = useState(false);

  // --- ПОИСК ЗАПЧАСТЕЙ ДЛЯ ЗАКАЗА ---
  const [orderPartsSearchQuery, setOrderPartsSearchQuery] = useState('');
  const [orderPartsSearchResults, setOrderPartsSearchResults] = useState<Part[]>([]);
  const [orderPartsSearchLoading, setOrderPartsSearchLoading] = useState(false);
  const [orderPartCache, setOrderPartCache] = useState<(Part | null)[]>([]);
  const orderPartsSearchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [editingPartIdx, setEditingPartIdx] = useState<number | null>(null);
  const [openAddPartOrder, setOpenAddPartOrder] = useState(false);
  const [addPartOrderLineIndex, setAddPartOrderLineIndex] = useState<number | null>(null);
  const [newPartFormOrder, setNewPartFormOrder] = useState({ name: '', part_number: '', brand: '', price: 0, unit: 'шт', category: 'other' as Part['category'] });
  const [savingNewPartOrder, setSavingNewPartOrder] = useState(false);

  // --- ФОРМА ЗАКАЗА ---
  const [formData, setFormData] = useState<OrderCreate & { status?: string }>({
    vehicle_id: 0, mechanic_id: undefined, status: 'new', recommendations: '', comments: '', order_works: [], order_parts: []
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const [orderIdFromUrl, setOrderIdFromUrl] = useState<number | null>(null);

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

  // Открытие заказа по ссылке из другой вкладки (?open=orderId)
  useEffect(() => {
    const openId = searchParams.get('open');
    if (!openId) return;
    
    const id = parseInt(openId, 10);
    if (!id || isNaN(id)) return;
    
    // Если уже обрабатывали этот ID - пропускаем
    if (orderIdFromUrl === id) return;

    setOrderIdFromUrl(id);

    // Очищаем параметр из URL
    setSearchParams({}, { replace: true });

    // Загружаем заказ напрямую по ID
    api.get(`/orders/${id}`)
      .then((r) => handleOpenDialog(r.data))
      .catch((err) => {
        console.error('Failed to load order:', err);
        setError('Не удалось загрузить заказ');
        setOrderIdFromUrl(null);
      });
  }, [searchParams, orderIdFromUrl]);

  // Ctrl+S для сохранения
  useEffect(() => {
    if (!openDialog) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [openDialog, formData]);

  // Загрузка всего каталога работ при открытии диалога
  useEffect(() => {
    if (!openDialog || allWorks.length > 0) return;
    setWorksSearchLoading(true);
    api.get<Work[]>('/works/', { params: { limit: 500 } })
      .then((r) => setAllWorks(r.data))
      .catch(() => {})
      .finally(() => setWorksSearchLoading(false));
  }, [openDialog]);

  // Фильтрация работ клиентски (по категории + поисковой строке)
  const filteredWorks = useMemo(() => {
    let result = allWorks;
    if (worksSearchCategory) result = result.filter(w => w.category === worksSearchCategory);
    if (worksSearchQuery.trim()) {
      const q = worksSearchQuery.trim().toLowerCase();
      result = result.filter(w => w.name.toLowerCase().includes(q) || (w.description || '').toLowerCase().includes(q));
    }
    return result;
  }, [allWorks, worksSearchCategory, worksSearchQuery]);

  // Поиск запчастей по артикулу (для строк заказа)
  useEffect(() => {
    if (!openDialog) return;
    if (orderPartsSearchDebounceRef.current) clearTimeout(orderPartsSearchDebounceRef.current);
    if (!orderPartsSearchQuery.trim()) {
      setOrderPartsSearchResults([]);
      return;
    }
    orderPartsSearchDebounceRef.current = setTimeout(() => {
      setOrderPartsSearchLoading(true);
      api.get<Part[]>('/parts/', { params: { search: orderPartsSearchQuery.trim(), limit: 50 } })
        .then((r) => setOrderPartsSearchResults(r.data))
        .catch(() => setOrderPartsSearchResults([]))
        .finally(() => setOrderPartsSearchLoading(false));
    }, 300);
    return () => { if (orderPartsSearchDebounceRef.current) clearTimeout(orderPartsSearchDebounceRef.current); };
  }, [orderPartsSearchQuery, openDialog]);

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
    setInlineMileage(d.vehicle?.mileage?.toString() ?? '');
    setOriginalPaidAmount(Number(d.paid_amount || 0));
    setPaidAmountFromServer(Number(d.paid_amount || 0));
    const parts = (d.order_parts || []).map((p: any) => ({
      part_id: p.part_id ?? 0,
      part_name: p.part?.name || p.part_name || '',
      article: p.part?.part_number ?? p.article ?? '',
      quantity: p.quantity,
      price: Number(p.price),
      discount: (p.discount ?? 0) as number
    }));
    setFormData({
      vehicle_id: d.vehicle_id, mechanic_id: d.mechanic_id, status: d.status, recommendations: d.recommendations || '', comments: d.comments || '',
      order_works: (d.order_works || []).map(w => ({ work_name: w.work?.name || (w as any).work_name || '', quantity: w.quantity, price: Number(w.price), discount: (w as any).discount || 0 })),
      order_parts: parts
    });
    setOrderPartCache((d.order_parts || []).map((p: any) => p.part || (p.part_id && p.part_name ? { id: p.part_id, part_number: p.article ?? '', name: p.part_name, price: p.price ?? 0, unit: 'шт', category: 'other' as const } as Part : null)));
  };

  const loadOrderPayments = async (id: number) => {
    try {
      const res = await api.get(`/orders/${id}/payments`);
      setPayments(res.data || []);
    } catch (e) { 
      console.error("Error loading payments:", e); 
    }
  };

  const handleOpenDialog = async (order?: Order) => {
    setError(''); setApplyToAll(false); setGlobalDiscount(0);
    setEditingWorkIdx(null); setWorksSearchQuery(''); setWorksSearchCategory('');
    if (order) {
      setEditingOrderId(order.id);
      setSearchingVehicle(true);
      await fetchOrderDetails(order.id);
      await loadOrderPayments(order.id);
      setSearchingVehicle(false);
      setInlineMileage(order.vehicle?.mileage?.toString() ?? '');
    } else {
      setEditingOrderId(null); setSelectedVehicle(null); setPaidAmountFromServer(0); setOriginalPaidAmount(0); setPayments([]);
      setFormData({ vehicle_id: 0, mechanic_id: undefined, status: 'new', order_works: [], order_parts: [], recommendations: '', comments: '' });
      setOrderPartCache([]);
      setLicensePlateSearch(''); setVinSearch('');
      setInlineMileage('');
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

  const handleUpdateMileage = async () => {
    if (!selectedVehicle || !inlineMileage) return;
    setSavingMileage(true);
    try {
      await api.put(`/vehicles/${selectedVehicle.id}`, { mileage: Number(inlineMileage) || 0 });
      setSelectedVehicle({ ...selectedVehicle, mileage: Number(inlineMileage) || 0 });
    } catch { setError('Не удалось обновить пробег'); }
    finally { setSavingMileage(false); }
  };

  const selectWorkFromCatalog = (idx: number, work: Work) => {
    skipNextFocus.current = true;
    updateRow('work', idx, 'work_name', work.name);
    setEditingWorkIdx(null);
    setWorksSearchQuery('');
    setWorksSearchCategory('');
  };

  const handleCreateWork = async () => {
    if (!createPopover || !createCategory) return;
    const { rowIdx, name } = createPopover;
    setCreatingWork(true);
    try {
      const res = await api.post<Work>('/works/', {
        name,
        category: createCategory,
        price: 0,
        duration_minutes: 60,
      });
      setAllWorks(prev => [...prev, res.data]);
      setCreatePopover(null);
      setCreateCategory('');
      selectWorkFromCatalog(rowIdx, res.data);
    } catch {
      // silent — пользователь может просто закрыть и использовать freeSolo
    } finally {
      setCreatingWork(false);
    }
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
        setSaveSuccess(true);
      }
      const list = await api.get('/orders/'); setOrders(list.data || []);
    } catch (err: any) { setError(err.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaveLoading(false); }
  };

  const handleCreatePayment = async () => {
    if (!editingOrderId) return;
    setSaveLoading(true);
    try {
      if (editingPaymentId) {
        // Редактирование существующего платежа
        await api.put(`/orders/${editingOrderId}/payments/${editingPaymentId}`, {
          order_id: editingOrderId,
          amount: parseFloat(paymentAmount),
          payment_method: paymentMethod
        });
      } else {
        // Создание нового платежа
        await api.post(`/orders/${editingOrderId}/payments`, {
          order_id: editingOrderId,
          amount: parseFloat(paymentAmount),
          payment_method: paymentMethod
        });
      }
      await fetchOrderDetails(editingOrderId);
      await loadOrderPayments(editingOrderId);
      setOpenPaymentDialog(false);
      setPaymentAmount('');
      setEditingPaymentId(null);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка оплаты');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleEditPayment = (payment: any) => {
    setEditingPaymentId(payment.id);
    setPaymentAmount(payment.amount.toString());
    setPaymentMethod(payment.payment_method);
    setOpenPaymentDialog(true);
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
    if (t === 'work') {
      const row = { work_name: '', part_name: '', quantity: 1, price: 0, discount: applyToAll ? globalDiscount : 0 };
      setFormData(p => ({ ...p, order_works: [...(p.order_works || []), row as any] }));
    } else {
      const row = { part_id: 0, part_name: '', article: '', quantity: 1, price: 0, discount: applyToAll ? globalDiscount : 0 };
      setFormData(p => ({ ...p, order_parts: [...(p.order_parts || []), row as any] }));
      setOrderPartCache(prev => [...prev, null]);
    }
  };

  const updateRow = (t: 'work' | 'part', i: number, f: string, v: any) => {
    const key = t === 'work' ? 'order_works' : 'order_parts';
    const list = [...(formData[key] || [])] as any[];
    if (list[i]) { list[i][f] = v; setFormData({ ...formData, [key]: list }); }
  };

  const setOrderPartLine = (idx: number, part: Part) => {
    setFormData(p => {
      const list = [...(p.order_parts || [])];
      if (!list[idx]) return p;
      list[idx] = { ...list[idx], part_id: part.id, part_name: part.name ?? '', article: part.part_number ?? '', quantity: list[idx].quantity, price: Number(part.price ?? 0), discount: list[idx].discount };
      return { ...p, order_parts: list };
    });
    setOrderPartCache(prev => { const n = [...prev]; n[idx] = part; return n; });
    setOrderPartsSearchQuery('');
  };

  const removeRow = (t: 'work' | 'part', idx: number) => {
    if (t === 'work') {
      setFormData(p => ({ ...p, order_works: (p.order_works || []).filter((_, i) => i !== idx) }));
    } else {
      setFormData(p => {
        const next = (p.order_parts || []).filter((_, i) => i !== idx);
        if (next.length === 0) next.push({ part_id: 0, part_name: '', article: '', quantity: 1, price: 0, discount: applyToAll ? globalDiscount : 0 });
        return { ...p, order_parts: next };
      });
      setOrderPartCache(prev => {
        const next = prev.filter((_, i) => i !== idx);
        if (next.length === 0) next.push(null);
        return next;
      });
    }
  };

  const clearPartInOrderLine = (idx: number) => {
    const list = [...(formData.order_parts || [])] as any[];
    if (list[idx]) {
      list[idx] = { ...list[idx], part_id: 0, part_name: '', article: '', price: 0 };
      setFormData({ ...formData, order_parts: list });
    }
    setOrderPartCache(prev => {
      const next = [...prev];
      next[idx] = null;
      return next;
    });
    setOrderPartsSearchQuery('');
  };

  const handleAddPartOrderSubmit = async () => {
    if (addPartOrderLineIndex == null) return;
    const article = newPartFormOrder.part_number.trim();
    if (!article) { setError('Укажите артикул запчасти'); return; }
    setSavingNewPartOrder(true);
    setError('');
    try {
      const existing = await api.get<Part[]>('/parts/', { params: { search: article, limit: 20 } });
      const found = existing.data.some((p) => p.part_number && p.part_number.toLowerCase() === article.toLowerCase());
      if (found) {
        setError('Запчасть с таким артикулом уже есть. Выберите её в поиске по артикулу.');
        return;
      }
      if (!newPartFormOrder.name.trim()) { setError('Укажите название запчасти'); return; }
      const res = await api.post<Part>('/parts/', {
        name: newPartFormOrder.name.trim(),
        part_number: article,
        brand: newPartFormOrder.brand.trim() || undefined,
        price: newPartFormOrder.price,
        unit: newPartFormOrder.unit,
        category: newPartFormOrder.category
      });
      const part = res.data;
      setOrderPartLine(addPartOrderLineIndex, part);
      setOpenAddPartOrder(false);
      setAddPartOrderLineIndex(null);
    } catch (e: any) {
      if (!e.response?.config?.url?.includes('?search=')) setError(e.response?.data?.detail || 'Ошибка создания запчасти');
    } finally {
      setSavingNewPartOrder(false);
    }
  };

  const filteredOrders = useMemo(() => {
    let result = orders;
    if (selectedStatusFilter !== 'all') result = result.filter(o => o.status === selectedStatusFilter);
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(o =>
        o.number?.toLowerCase().includes(q) ||
        o.vehicle?.license_plate?.toLowerCase().includes(q) ||
        o.vehicle?.customer?.full_name?.toLowerCase().includes(q) ||
        o.vehicle?.customer?.phone?.includes(q) ||
        `${o.vehicle?.brand?.name ?? ''} ${o.vehicle?.model?.name ?? ''}`.toLowerCase().includes(q) ||
        o.mechanic?.full_name?.toLowerCase().includes(q)
      );
    }
    return result;
  }, [orders, selectedStatusFilter, searchQuery]);

  const handleDeleteOrder = async () => {
    if (!deleteOrderConfirm) return;
    setDeletingOrder(true);
    try {
      await api.delete(`/orders/${deleteOrderConfirm.id}`);
      setDeleteOrderConfirm(null);
      loadInitialData();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка удаления заказа');
    } finally {
      setDeletingOrder(false);
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}><CircularProgress /></Box>;

  return (
    <Container maxWidth={false} sx={{ px: { xs: 2, md: 5 }, py: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 900 }}>Заказ-наряды</Typography>
        <Button variant="contained" size="large" startIcon={<AddRounded />} onClick={() => handleOpenDialog()} sx={{ borderRadius: 3, px: 4 }}>Создать заказ</Button>
      </Stack>

      <TextField
        fullWidth
        size="small"
        placeholder="Поиск по номеру, клиенту, гос.номеру, мастеру..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        InputProps={{
          startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" color="action" /></InputAdornment>,
        }}
        sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 3, bgcolor: '#fff' } }}
      />

      <Box sx={{ mb: 3, borderBottom: '1px solid #E2E8F0' }}>
        <Tabs value={selectedStatusFilter} onChange={(_, v) => setSelectedStatusFilter(v)} variant="scrollable" scrollButtons="auto">
          <Tab label={`Все (${orders.length})`} value="all" sx={{ fontWeight: 700 }} />
          {orderStatuses.map(s => {
            const count = orders.filter(o => o.status === s.value).length;
            return <Tab key={s.value} label={`${s.label} (${count})`} value={s.value} sx={{ fontWeight: 700 }} />;
          })}
          <Tab label={`Завершён (${orders.filter(o => o.status === 'completed').length})`} value="completed" sx={{ fontWeight: 700 }} />
        </Tabs>
      </Box>

      <TableContainer component={Paper} sx={{ borderRadius: 4, border: '1px solid #E2E8F0', boxShadow: 'none' }}>
        <Table>
          <TableHead sx={{ bgcolor: '#F8FAFC' }}>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Номер</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Автомобиль</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Клиент</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Мастер</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Статус</TableCell>
              <TableCell align="right" sx={{ fontWeight: 700 }}>Сумма</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Создан</TableCell>
              {isAdmin && <TableCell sx={{ fontWeight: 700, width: 48 }} />}
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredOrders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={isAdmin ? 8 : 7} sx={{ textAlign: 'center', py: 6 }}>
                  <SearchOffRounded sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
                  <Typography color="text.secondary">
                    {searchQuery.trim() ? 'Ничего не найдено' : 'Нет заказов с таким статусом'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : filteredOrders.map(o => (
              <TableRow
                key={o.id}
                hover
                onClick={() => window.open(`/orders?open=${o.id}`, '_blank')}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell sx={{ fontWeight: 600 }}>{o.number}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>{o.vehicle?.brand?.name} {o.vehicle?.model?.name}</Typography>
                  <Typography variant="caption" color="text.secondary">{o.vehicle?.license_plate}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>{o.vehicle?.customer?.full_name || '—'}</Typography>
                  {o.vehicle?.customer?.phone && (
                    <Typography variant="caption" color="text.secondary">{o.vehicle.customer.phone}</Typography>
                  )}
                </TableCell>
                <TableCell>{o.mechanic?.full_name || '—'}</TableCell>
                <TableCell><Chip label={getStatusLabel(o.status)} color={STATUS_COLORS[o.status] || 'default'} size="small" sx={{ fontWeight: 700, borderRadius: 1.5 }} /></TableCell>
                <TableCell align="right" sx={{ fontWeight: 800 }}>{formatCurrency(o.total_amount)}</TableCell>
                <TableCell>
                  <Tooltip title={o.created_at ? new Date(o.created_at).toLocaleString('ru-RU') : ''}>
                    <Typography variant="caption" color="text.secondary">
                      {o.created_at ? formatDistanceToNow(new Date(o.created_at), { addSuffix: true, locale: ru }) : '—'}
                    </Typography>
                  </Tooltip>
                </TableCell>
                {isAdmin && (
                  <TableCell sx={{ px: 0.5 }}>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={(e) => { e.stopPropagation(); setDeleteOrderConfirm(o); }}
                      title="Удалить заказ"
                    >
                      <DeleteOutlineRounded fontSize="small" />
                    </IconButton>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} fullScreen PaperProps={{ sx: { bgcolor: '#F8FAFC' } }}>
        <AppBar sx={{ position: 'sticky', bgcolor: '#fff', color: 'text.primary', boxShadow: 'none', borderBottom: '1px solid #E2E8F0', zIndex: 1100 }}>
          <Toolbar>
            <IconButton edge="start" onClick={() => setOpenDialog(false)} sx={{ mr: 2 }}><ArrowBackRounded /></IconButton>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ flex: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                {editingOrderId
                  ? `Заказ-наряд #${orders.find(o => o.id === editingOrderId)?.number ?? editingOrderId}`
                  : 'Новый заказ-наряд'}
              </Typography>
              {editingOrderId && (
                <Tooltip title="Скопировать номер">
                  <IconButton size="small" onClick={() => {
                    const num = orders.find(o => o.id === editingOrderId)?.number ?? '';
                    navigator.clipboard.writeText(num);
                  }}>
                    <ContentCopyRounded sx={{ fontSize: 16 }} />
                  </IconButton>
                </Tooltip>
              )}
            </Stack>
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
                  <TextField fullWidth size="small" placeholder={searchTab === 0 ? "А000АА77" : "17 символов или последние 6"} label={searchTab === 0 ? "Гос. номер" : "VIN-номер"} value={searchTab === 0 ? licensePlateSearch : vinSearch} onChange={e => searchTab === 0 ? setLicensePlateSearch(e.target.value.toUpperCase()) : setVinSearch(e.target.value.toUpperCase())} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleSearchVehicle(); } }} />
                  <Button variant="contained" onClick={handleSearchVehicle} disabled={searchingVehicle}>Найти</Button>
                </Stack></Box>
              ) : (<Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 3, py: 2, bgcolor: alpha('#4F46E5', 0.02) }}>
                  <Stack direction="row" spacing={2} alignItems="center"><Avatar sx={{ bgcolor: 'primary.main' }}><DirectionsCarFilledRounded /></Avatar><Box><Typography variant="subtitle1" sx={{ fontWeight: 800 }}>{selectedVehicle.brand?.name} {selectedVehicle.model?.name}</Typography><Typography variant="caption">{selectedVehicle.license_plate} • VIN: {selectedVehicle.vin}</Typography>
                    <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mt: 0.25 }}>
                      <SpeedRounded sx={{ fontSize: 14, color: 'text.secondary' }} />
                      <TextField
                        variant="standard"
                        size="small"
                        placeholder="Пробег"
                        value={inlineMileage}
                        onChange={e => setInlineMileage(e.target.value.replace(/\D/g, ''))}
                        onBlur={() => { if (inlineMileage && Number(inlineMileage) !== selectedVehicle.mileage) handleUpdateMileage(); }}
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleUpdateMileage(); } }}
                        InputProps={{ disableUnderline: false, sx: { fontSize: '0.75rem', fontWeight: 600, width: 80 } }}
                      />
                      <Typography variant="caption" color="text.secondary">км</Typography>
                      {savingMileage && <CircularProgress size={12} />}
                    </Stack>
                    {selectedVehicle.customer && (
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 0.5 }}>
                        <Stack direction="row" spacing={0.5} alignItems="center"><PersonRounded sx={{ fontSize: 14, color: 'text.secondary' }} /><Typography variant="caption" sx={{ fontWeight: 600 }}>{selectedVehicle.customer.full_name}</Typography></Stack>
                        {selectedVehicle.customer.phone && (
                          <Stack direction="row" spacing={0.5} alignItems="center">
                            <PhoneRounded sx={{ fontSize: 14, color: 'text.secondary' }} />
                            <Typography component="a" href={`tel:${selectedVehicle.customer.phone}`} variant="caption" sx={{ fontWeight: 600, color: 'primary.main', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }} onClick={(e) => e.stopPropagation()}>{selectedVehicle.customer.phone}</Typography>
                          </Stack>
                        )}
                      </Stack>
                    )}</Box></Stack>
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
                  {paidAmountFromServer < totals.grand - 0.01 && <Button variant="contained" color="success" size="small" startIcon={<PaymentRounded />} onClick={() => { setEditingPaymentId(null); setPaymentAmount((totals.grand - paidAmountFromServer).toFixed(0)); setPaymentMethod('cash'); setOpenPaymentDialog(true); }}>Оплатить</Button>}
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
                        {isAdmin && p.status === 'succeeded' && (
                          <>
                            <IconButton size="small" onClick={() => handleEditPayment(p)} title="Редактировать платёж">
                              <EditRounded fontSize="small" />
                            </IconButton>
                            <IconButton size="small" color="error" onClick={() => handleCancelSinglePayment(p.id)} title="Отменить платёж">
                              <DeleteOutlineRounded fontSize="small" />
                            </IconButton>
                          </>
                        )}
                        <Chip label={PAYMENT_STATUS_LABELS[p.status] || p.status} size="small" variant="outlined" sx={{ ml: 1, fontSize: '0.6rem', height: 20 }} />
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
              <Grid item xs={12} lg={6} ref={(el) => { workRowRefs.current[idx] = el as HTMLDivElement | null; }}>
                {editingWorkIdx === idx && (
                  <Box sx={{ mb: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    <Chip
                      label="Все"
                      size="small"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => setWorksSearchCategory('')}
                      variant={worksSearchCategory === '' ? 'filled' : 'outlined'}
                      color={worksSearchCategory === '' ? 'primary' : 'default'}
                      sx={{ fontWeight: 700, fontSize: '0.7rem', height: 22 }}
                    />
                    {WORK_CATEGORIES.map(cat => (
                      <Chip
                        key={cat.value}
                        label={cat.label}
                        size="small"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => setWorksSearchCategory(worksSearchCategory === cat.value ? '' : cat.value)}
                        variant={worksSearchCategory === cat.value ? 'filled' : 'outlined'}
                        sx={{
                          fontWeight: 700,
                          fontSize: '0.7rem',
                          height: 22,
                          bgcolor: worksSearchCategory === cat.value ? cat.color : 'transparent',
                          color: worksSearchCategory === cat.value ? '#fff' : cat.color,
                          borderColor: cat.color,
                          '&:hover': { bgcolor: cat.color, color: '#fff', opacity: 0.9 },
                        }}
                      />
                    ))}
                  </Box>
                )}
                <Autocomplete
                  freeSolo
                  size="small"
                  value={null as any}
                  inputValue={editingWorkIdx === idx ? worksSearchQuery : (work.work_name || '')}
                  onInputChange={(_: any, v: string, reason: string) => {
                    if (reason === 'input') {
                      setEditingWorkIdx(idx);
                      setWorksSearchQuery(v);
                      updateRow('work', idx, 'work_name', v);
                    }
                  }}
                  onFocus={() => {
                    if (skipNextFocus.current) { skipNextFocus.current = false; return; }
                    setEditingWorkIdx(idx);
                  }}
                  onChange={(_: any, option: any) => {
                    if (!option || typeof option === 'string') return;
                    if (option.__isCreate) {
                      preventBlurReset.current = true;
                      setCreatePopover({ anchorEl: workRowRefs.current[idx]!, name: option.name, rowIdx: idx });
                      setCreateCategory(worksSearchCategory || '');
                      return;
                    }
                    if (option.id > 0) selectWorkFromCatalog(idx, option as Work);
                  }}
                  onBlur={() => {
                    if (preventBlurReset.current) { preventBlurReset.current = false; return; }
                    if (editingWorkIdx === idx) {
                      setEditingWorkIdx(null);
                      setWorksSearchQuery('');
                      setWorksSearchCategory('');
                    }
                  }}
                  options={editingWorkIdx === idx ? filteredWorks : []}
                  getOptionLabel={(opt: any) => typeof opt === 'string' ? opt : opt.name}
                  groupBy={(opt: any) => {
                    if (opt.__isCreate || worksSearchCategory) return '';
                    const cat = WORK_CATEGORIES.find(c => c.value === opt.category);
                    return cat ? cat.label : 'Прочее';
                  }}
                  renderOption={(props: any, opt: any) => {
                    if (opt.__isCreate) {
                      return (
                        <li {...props} key="__create" onMouseDown={(e: any) => e.preventDefault()}
                          style={{ borderTop: '1px solid #e2e8f0', marginTop: 4, paddingTop: 8 }}>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <AddRounded fontSize="small" color="primary" />
                            <Typography variant="body2" color="primary" fontWeight={700}>
                              Добавить «{opt.name}» в каталог
                            </Typography>
                          </Stack>
                        </li>
                      );
                    }
                    return (
                      <li {...props} key={opt.id}>
                        <Typography variant="body2">{opt.name}</Typography>
                      </li>
                    );
                  }}
                  loading={worksSearchLoading && editingWorkIdx === idx}
                  filterOptions={(options: any) => {
                    const result = [...options];
                    if (worksSearchQuery.trim() && editingWorkIdx === idx) {
                      result.push({ __isCreate: true, id: '__create', name: worksSearchQuery.trim() });
                    }
                    return result;
                  }}
                  renderInput={(params: any) => (
                    <TextField
                      {...params}
                      variant="standard"
                      placeholder={editingWorkIdx === idx ? 'Поиск по каталогу или введите вручную...' : 'Услуга...'}
                      InputProps={{ ...params.InputProps, disableUnderline: true, sx: { fontSize: '1rem', fontWeight: 700 } }}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Кол-во" type="number" value={work.quantity} onChange={e => updateRow('work', idx, 'quantity', e.target.value)} /></Grid>
              <Grid item xs={3} lg={1.5}><TextField fullWidth size="small" label="Цена" type="number" value={work.price} onChange={e => updateRow('work', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
              <Grid item xs={3} lg={1.2}><TextField fullWidth size="small" label="Скидка" type="number" value={work.discount} onChange={e => updateRow('work', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
              <Grid item xs={2} lg={1.6} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(work.price) * Number(work.quantity)) * (1 - (Number(work.discount) || 0) / 100))}</Typography></Grid>
              <Grid item xs={1} lg={0.5}><IconButton color="error" size="small" onClick={() => removeRow('work', idx)}><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
            </Grid></Paper>))}</Stack></Box>

          <Box><Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, px: 1 }}><Typography variant="subtitle1" sx={{ fontWeight: 900 }}><ShoppingBagRounded fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} /> Запчасти</Typography><Button variant="contained" size="small" startIcon={<AddRounded />} onClick={() => addRow('part')}>Добавить строку</Button></Stack>
            <Stack spacing={1}>{(formData.order_parts || []).map((part, idx) => {
              const partSelected = !!orderPartCache[idx];
              return (
                <Paper key={idx} elevation={0} sx={{ p: 1.5, px: 2, borderRadius: 2, border: '1px solid #E2E8F0', bgcolor: '#fff', '&:hover': { borderColor: 'primary.main' } }}>
                  <Grid container spacing={2} alignItems="center">
                    {partSelected ? (
                      <>
                        <Grid item xs={2} lg={1.5}><TextField size="small" fullWidth label="Артикул" value={orderPartCache[idx]?.part_number ?? ''} InputProps={{ readOnly: true }} sx={{ '& .MuiInputBase-input': { cursor: 'default' } }} /></Grid>
                        <Grid item xs={2} lg={2.5}><TextField size="small" fullWidth label="Название" value={orderPartCache[idx]?.name ?? ''} InputProps={{ readOnly: true }} sx={{ '& .MuiInputBase-input': { cursor: 'default' } }} /></Grid>
                        <Grid item xs={1} lg={1}><TextField size="small" fullWidth label="Кол-во" type="number" value={part.quantity} onChange={e => updateRow('part', idx, 'quantity', e.target.value)} /></Grid>
                        <Grid item xs={2} lg={1.5}><TextField size="small" fullWidth label="Цена (клиент)" type="number" value={part.price} onChange={e => updateRow('part', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
                        <Grid item xs={1} lg={1}><TextField size="small" fullWidth label="Скидка" type="number" value={part.discount} onChange={e => updateRow('part', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
                        <Grid item xs={2} lg={1.5} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(part.price) * Number(part.quantity)) * (1 - (Number(part.discount) || 0) / 100))}</Typography></Grid>
                        <Grid item xs={1}><IconButton size="small" onClick={() => clearPartInOrderLine(idx)} title="Сменить запчасть"><EditRounded fontSize="small" /></IconButton></Grid>
                        <Grid item xs={1}><IconButton color="error" size="small" onClick={() => removeRow('part', idx)} title="Удалить строку"><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
                      </>
                    ) : (
                      <>
                        <Grid item xs={12} lg={6}>
                          <Autocomplete<Part | { id: number; name: string }>
                            size="small"
                            value={null}
                            inputValue={orderPartsSearchQuery}
                            onInputChange={(_, v) => setOrderPartsSearchQuery(v)}
                            onChange={(_, option) => {
                              if (option && 'id' in option) {
                                if (option.id === -1) {
                                  setAddPartOrderLineIndex(idx);
                                  setNewPartFormOrder({ name: orderPartsSearchQuery.trim() || '', part_number: orderPartsSearchQuery.trim() || '', brand: '', price: 0, unit: 'шт', category: 'other' });
                                  setOpenAddPartOrder(true);
                                  return;
                                }
                                setOrderPartLine(idx, option as Part);
                              }
                            }}
                            options={orderPartsSearchQuery.trim() && orderPartsSearchResults.length === 0 ? [{ id: -1, name: `+ Добавить «${orderPartsSearchQuery.trim()}»` }] : orderPartsSearchResults}
                            getOptionLabel={(opt) => opt.id === -1 ? opt.name : `${(opt as Part).part_number ?? ''} — ${(opt as Part).name}`}
                            loading={orderPartsSearchLoading}
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                label="Поиск по артикулу"
                                placeholder="Введите артикул или выберите из списка"
                                InputProps={{
                                  ...params.InputProps,
                                  startAdornment: (<><InputAdornment position="start"><SearchIcon fontSize="small" color="action" /></InputAdornment>{params.InputProps.startAdornment}</>),
                                  endAdornment: (<>{orderPartsSearchLoading ? <CircularProgress color="inherit" size={20} /> : null}{params.InputProps.endAdornment}</>)
                                }}
                              />
                            )}
                          />
                        </Grid>
                        <Grid item xs={2} lg={1}><TextField size="small" fullWidth label="Кол-во" type="number" value={part.quantity} onChange={e => updateRow('part', idx, 'quantity', e.target.value)} /></Grid>
                        <Grid item xs={2} lg={1.5}><TextField size="small" fullWidth label="Цена" type="number" value={part.price} onChange={e => updateRow('part', idx, 'price', e.target.value)} InputProps={{ endAdornment: '₽' }} /></Grid>
                        <Grid item xs={1} lg={1}><TextField size="small" fullWidth label="Скидка" type="number" value={part.discount} onChange={e => updateRow('part', idx, 'discount', e.target.value)} InputProps={{ endAdornment: '%' }} /></Grid>
                        <Grid item xs={2} lg={1.5} sx={{ textAlign: 'right' }}><Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main' }}>{formatCurrency((Number(part.price) * Number(part.quantity)) * (1 - (Number(part.discount) || 0) / 100))}</Typography></Grid>
                        <Grid item xs={1}><IconButton color="error" size="small" onClick={() => removeRow('part', idx)} title="Удалить строку"><DeleteOutlineRounded fontSize="small" /></IconButton></Grid>
                      </>
                    )}
                  </Grid>
                </Paper>
              );
            })}</Stack></Box>

          <Collapse in={totals.grand > 0}><Paper sx={{ p: 2, px: 4, borderRadius: 3, border: '2px solid', borderColor: 'primary.main', bgcolor: '#fff' }}><Stack direction="row" justifyContent="space-between" alignItems="center"><Stack direction="row" spacing={4}><Box><Typography variant="caption">Работы</Typography><Typography variant="body1" sx={{ fontWeight: 700 }}>{formatCurrency(totals.works)}</Typography></Box><Box><Typography variant="caption">Запчасти</Typography><Typography variant="body1" sx={{ fontWeight: 700 }}>{formatCurrency(totals.parts)}</Typography></Box></Stack><Box sx={{ textAlign: 'right' }}><Typography variant="caption" color="primary" sx={{ fontWeight: 800 }}>ИТОГО</Typography><Typography variant="h4" sx={{ fontWeight: 950 }}>{formatCurrency(totals.grand)}</Typography></Box></Stack></Paper></Collapse>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2, borderRadius: 3, border: '1px solid #E2E8F0', height: '100%', transition: 'all 0.2s ease' }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><CommentRounded fontSize="small" color="action" /> Рекомендации</Typography>
                <TextField fullWidth multiline minRows={2} maxRows={12} variant="outlined" size="small" placeholder="Рекомендации для клиента..." value={formData.recommendations} onChange={e => setFormData({...formData, recommendations: e.target.value})} sx={{ '& .MuiOutlinedInput-root': { transition: 'height 0.15s ease' } }} />
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2, borderRadius: 3, border: '1px solid #E2E8F0', height: '100%', transition: 'all 0.2s ease' }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}><EditRounded fontSize="small" color="action" /> Комментарии (внутренние)</Typography>
                <TextField fullWidth multiline minRows={2} maxRows={12} variant="outlined" size="small" placeholder="Заметки для мастеров и менеджеров..." value={formData.comments} onChange={e => setFormData({...formData, comments: e.target.value})} sx={{ '& .MuiOutlinedInput-root': { transition: 'height 0.15s ease' } }} />
              </Paper>
            </Grid>
          </Grid>
        </Stack></Box>
      </Dialog>

      <Dialog open={openAddPartOrder} onClose={() => setOpenAddPartOrder(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Добавить запчасть</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={12}><TextField fullWidth size="small" label="Название" value={newPartFormOrder.name} onChange={e => setNewPartFormOrder(p => ({ ...p, name: e.target.value }))} required /></Grid>
            <Grid item xs={12}><TextField fullWidth size="small" label="Артикул" value={newPartFormOrder.part_number} onChange={e => setNewPartFormOrder(p => ({ ...p, part_number: e.target.value }))} /></Grid>
            <Grid item xs={12}><TextField fullWidth size="small" label="Бренд" value={newPartFormOrder.brand} onChange={e => setNewPartFormOrder(p => ({ ...p, brand: e.target.value }))} /></Grid>
            <Grid item xs={6}><TextField fullWidth size="small" type="number" label="Цена" value={newPartFormOrder.price || ''} onChange={e => setNewPartFormOrder(p => ({ ...p, price: parseFloat(e.target.value) || 0 }))} /></Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddPartOrder(false)}>Отмена</Button>
          <Button variant="contained" onClick={handleAddPartOrderSubmit} disabled={savingNewPartOrder}>{savingNewPartOrder ? <CircularProgress size={24} /> : 'Добавить'}</Button>
        </DialogActions>
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

      <Dialog open={openPaymentDialog} onClose={() => { setOpenPaymentDialog(false); setEditingPaymentId(null); setPaymentAmount(''); }} PaperProps={{ sx: { borderRadius: 3, p: 2, width: 340 } }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>
          {editingPaymentId ? 'Редактировать платёж' : 'Принять оплату'}
        </Typography>
        <Stack spacing={2.5}>
          <TextField 
            fullWidth 
            autoFocus 
            type="number" 
            label="Сумма"
            value={paymentAmount} 
            onChange={e => setPaymentAmount(e.target.value)} 
            InputProps={{ endAdornment: '₽' }} 
          />
          <FormControl fullWidth>
            <InputLabel>Способ</InputLabel>
            <Select value={paymentMethod} label="Способ" onChange={e => setPaymentMethod(e.target.value)}>
              <MenuItem value="cash">Наличные</MenuItem>
              <MenuItem value="card">Карта</MenuItem>
              <MenuItem value="yookassa">ЮKassa</MenuItem>
            </Select>
          </FormControl>
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button onClick={() => { setOpenPaymentDialog(false); setEditingPaymentId(null); setPaymentAmount(''); }}>Отмена</Button>
            <Button variant="contained" color="success" onClick={handleCreatePayment} disabled={saveLoading}>
              {saveLoading ? <CircularProgress size={24} /> : (editingPaymentId ? 'Сохранить' : 'Подтвердить')}
            </Button>
          </Stack>
        </Stack>
      </Dialog>

      <Dialog open={openResetConfirm} onClose={() => setOpenResetConfirm(false)} PaperProps={{ sx: { p: 2, maxWidth: 400, borderRadius: 4 } }}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5, fontWeight: 800 }}><WarningAmberRounded color="error" fontSize="large" /> Сброс оплат</DialogTitle>
        <DialogContent><DialogContentText sx={{ color: 'text.primary', fontWeight: 500 }}>Все проведенные платежи по этому заказу будут аннулированы. Продолжить?</DialogContentText></DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}><Button onClick={() => setOpenResetConfirm(false)} variant="outlined" color="inherit">Отмена</Button><Button onClick={handleCancelAllPayments} color="error" variant="contained">Да, сбросить</Button></DialogActions>
      </Dialog>

      {/* Popover: добавить работу в каталог */}
      <Popover
        open={!!createPopover}
        anchorEl={createPopover?.anchorEl}
        onClose={() => { setCreatePopover(null); setCreateCategory(''); }}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        disableAutoFocus
        disableEnforceFocus
        PaperProps={{ sx: { p: 2, width: 320, borderRadius: 2, boxShadow: '0 8px 32px rgba(0,0,0,0.12)' } }}
      >
        <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 0.5 }}>
          Добавить в каталог работ
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          «{createPopover?.name}»
        </Typography>
        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
          <InputLabel>Категория</InputLabel>
          <Select
            value={createCategory}
            label="Категория"
            onChange={(e) => setCreateCategory(e.target.value)}
          >
            {WORK_CATEGORIES.map(cat => (
              <MenuItem key={cat.value} value={cat.value}>
                <Box component="span" sx={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', bgcolor: cat.color, mr: 1 }} />
                {cat.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button size="small" onClick={() => { setCreatePopover(null); setCreateCategory(''); }}>
            Отмена
          </Button>
          <Button
            size="small"
            variant="contained"
            disabled={!createCategory || creatingWork}
            onClick={handleCreateWork}
            startIcon={creatingWork ? <CircularProgress size={14} /> : <AddRounded />}
          >
            Добавить
          </Button>
        </Stack>
      </Popover>

      {/* Snackbar при сохранении */}
      <Snackbar
        open={saveSuccess}
        autoHideDuration={2000}
        onClose={() => setSaveSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSaveSuccess(false)} severity="success" variant="filled" sx={{ borderRadius: 2 }}>
          Заказ-наряд сохранён
        </Alert>
      </Snackbar>

      {/* Подтверждение удаления заказа */}
      <Dialog
        open={deleteOrderConfirm !== null}
        onClose={() => !deletingOrder && setDeleteOrderConfirm(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5, fontWeight: 800 }}>
          <WarningAmberRounded color="error" fontSize="large" /> Удалить заказ-наряд?
        </DialogTitle>
        <DialogContent>
          {deleteOrderConfirm && (
            <Typography>
              Заказ-наряд <b>#{deleteOrderConfirm.number}</b> будет удалён вместе со всеми работами, запчастями и платежами. Это действие необратимо.
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteOrderConfirm(null)} disabled={deletingOrder} variant="outlined" color="inherit">
            Отмена
          </Button>
          <Button variant="contained" color="error" onClick={handleDeleteOrder} disabled={deletingOrder}>
            {deletingOrder ? <CircularProgress size={24} /> : 'Удалить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}