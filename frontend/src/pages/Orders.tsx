import { useState, useEffect } from 'react'
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  Divider,
  Tabs,
  Tab,
  InputAdornment,
} from '@mui/material'
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Home as HomeIcon,
  Search as SearchIcon,
  ArrowBack as ArrowBackIcon,
  Payment as PaymentIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { OrderDetail, OrderCreate, OrderUpdate, Vehicle, Employee, Work, Part, OrderWorkCreate, OrderPartCreate, VehicleCreate, Customer, CustomerCreate, OrderStatusInfo, User } from '../types'

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  estimation: 'Проценка',
  in_progress: 'В работе',
  ready_for_payment: 'Готов к оплате',
  paid: 'Оплачен',
  completed: 'Завершен',
  cancelled: 'Отменен',
}

const STATUS_COLORS: Record<string, 'default' | 'primary' | 'success' | 'error' | 'warning' | 'info'> = {
  new: 'default',
  estimation: 'info',
  in_progress: 'primary',
  ready_for_payment: 'warning',
  paid: 'success',
  completed: 'default',
  cancelled: 'error',
}

export default function Orders() {
  const navigate = useNavigate()
  const [orders, setOrders] = useState<Order[]>([])
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [works, setWorks] = useState<Work[]>([])
  const [parts, setParts] = useState<Part[]>([])
  const [orderStatuses, setOrderStatuses] = useState<OrderStatusInfo[]>([])
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [openDialog, setOpenDialog] = useState(false)
  const [editingOrder, setEditingOrder] = useState<OrderDetail | null>(null)
  
  // Форма
  const [formData, setFormData] = useState<OrderCreate>({
    vehicle_id: 0,
    mechanic_id: undefined,
    recommendations: undefined,
    comments: undefined,
    order_works: [],
    order_parts: [],
  })
  
  // Поиск транспортного средства
  const [vehicleSearchTab, setVehicleSearchTab] = useState(0) // 0 - гос номер, 1 - VIN
  const [licensePlateSearch, setLicensePlateSearch] = useState('')
  const [vinSearch, setVinSearch] = useState('')
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null)
  const [searchingVehicle, setSearchingVehicle] = useState(false)
  
  // Диалог добавления нового автомобиля
  const [openAddVehicleDialog, setOpenAddVehicleDialog] = useState(false)
  const [newVehicleData, setNewVehicleData] = useState<VehicleCreate>({
    brand: '',
    model: '',
    license_plate: '',
    vin: '',
    year: undefined,
    customer_id: 0,
  })
  // Диалог редактирования транспортного средства/клиента
  const [openEditVehicleDialog, setOpenEditVehicleDialog] = useState(false)
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null)
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)
  const [editingVehicleData, setEditingVehicleData] = useState({
    brand: '',
    model: '',
    license_plate: '',
    vin: '',
    year: undefined as number | undefined,
  })
  const [editingCustomerData, setEditingCustomerData] = useState({
    full_name: '',
    phone: '',
    email: '',
    address: '',
    notes: '',
  })
  const [savingEdit, setSavingEdit] = useState(false)
  const [editMode, setEditMode] = useState<'vehicle' | 'customer'>('vehicle')
  // Поиск и данные клиента
  const [customerPhone, setCustomerPhone] = useState('+7')
  const [searchingCustomer, setSearchingCustomer] = useState(false)
  const [foundCustomers, setFoundCustomers] = useState<Customer[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [customerSearchAttempted, setCustomerSearchAttempted] = useState(false)
  const [newCustomerData, setNewCustomerData] = useState<CustomerCreate>({
    full_name: '',
    phone: '',
    email: undefined,
  })
  const [creatingVehicle, setCreatingVehicle] = useState(false)
  
  // Временные данные для добавления работ/запчастей
  const [selectedWork, setSelectedWork] = useState<number>(0)
  const [workQuantity, setWorkQuantity] = useState(1)
  const [selectedPart, setSelectedPart] = useState<number>(0)
  const [partQuantity, setPartQuantity] = useState(1)
  
  // Диалог оплаты
  const [openPaymentDialog, setOpenPaymentDialog] = useState(false)
  const [paymentAmount, setPaymentAmount] = useState<string>('')
  const [originalPaidAmount, setOriginalPaidAmount] = useState<number>(0) // Исходная оплаченная сумма для вычисления разницы

  useEffect(() => {
    loadOrders()
    loadOrderStatuses()
    loadCurrentUser()
    // Загружаем только при необходимости (при открытии диалога)
  }, [])

  useEffect(() => {
    // Перезагружаем заказы при изменении фильтра
    if (selectedStatusFilter !== undefined) {
      loadOrders()
    }
  }, [selectedStatusFilter])

  const loadCurrentUser = async () => {
    try {
      const response = await api.get('/auth/me')
      setCurrentUser(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки текущего пользователя:', err)
    }
  }

  const loadOrders = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (selectedStatusFilter) {
        params.status = selectedStatusFilter
      }
      const response = await api.get('/orders/', { params })
      setOrders(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки заказ-нарядов')
    } finally {
      setLoading(false)
    }
  }

  const loadVehicles = async () => {
    try {
      const response = await api.get('/vehicles/')
      setVehicles(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки транспортных средств:', err)
    }
  }

  const loadEmployees = async () => {
    try {
      const response = await api.get('/employees/')
      setEmployees(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки сотрудников:', err)
    }
  }

  const loadWorks = async () => {
    try {
      const response = await api.get('/works/')
      setWorks(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки работ:', err)
    }
  }

  const loadParts = async () => {
    try {
      const response = await api.get('/parts/')
      setParts(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки запчастей:', err)
    }
  }

  const loadOrderStatuses = async () => {
    try {
      const response = await api.get('/orders/statuses')
      setOrderStatuses(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки статусов заказов:', err)
    }
  }

  const handleOpenDialog = async (order?: Order) => {
    // Загружаем необходимые данные только при открытии диалога
    await Promise.all([
      loadVehicles(),
      loadEmployees(),
      loadWorks(),
      loadParts(),
      loadOrderStatuses()
    ])

    if (order) {
      // Загружаем детальную информацию о заказе только при открытии диалога
      try {
        const detailResponse = await api.get(`/orders/${order.id}`)
        const orderDetail: OrderDetail = detailResponse.data
        setEditingOrder(orderDetail)
        setOriginalPaidAmount(Number(orderDetail.paid_amount || 0)) // Сохраняем исходную оплаченную сумму
        setFormData({
          vehicle_id: orderDetail.vehicle_id,
          mechanic_id: orderDetail.mechanic_id || undefined,
          recommendations: orderDetail.recommendations || undefined,
          comments: orderDetail.comments || undefined,
          order_works: orderDetail.order_works.map(ow => ({
            work_id: (ow as any).work_id || null,
            work_name: (ow as any).work_name || null,
            quantity: ow.quantity,
            price: Number(ow.price),
            discount: (ow as any).discount || 0,
          })) as any,
          order_parts: orderDetail.order_parts.map(op => ({
            part_id: (op as any).part_id || null,
            part_name: (op as any).part_name || null,
            article: (op as any).article || null,
            quantity: op.quantity,
            price: Number(op.price),
            discount: (op as any).discount || 0,
          })) as any,
        })
        setSelectedVehicle(orderDetail.vehicle)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка загрузки заказ-наряда')
        return
      }
    } else {
      setEditingOrder(null)
      setFormData({
        vehicle_id: 0,
        mechanic_id: undefined,
        order_works: [],
        order_parts: [],
        recommendations: undefined,
        comments: undefined,
      })
      setSelectedVehicle(null)
      setLicensePlateSearch('')
      setVinSearch('')
      setVehicleSearchTab(0)
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingOrder(null)
    setSelectedVehicle(null)
    setLicensePlateSearch('')
    setVinSearch('')
    setError('')
    setOriginalPaidAmount(0) // Сбрасываем исходную оплаченную сумму
  }

  const handleSearchVehicle = async () => {
    if (vehicleSearchTab === 0 && !licensePlateSearch.trim()) {
      setError('Введите гос номер для поиска')
      return
    }
    if (vehicleSearchTab === 1 && vinSearch.trim().length !== 17) {
      setError('VIN номер должен содержать 17 символов')
      return
    }

    try {
      setSearchingVehicle(true)
      setError('')
      let response
      
      if (vehicleSearchTab === 0) {
        response = await api.get('/vehicles/search/by-license-plate', {
          params: { license_plate: licensePlateSearch.trim() }
        })
      } else {
        response = await api.get('/vehicles/search/by-vin', {
          params: { vin: vinSearch.trim().toUpperCase() }
        })
      }

      const vehicle = response.data
      setSelectedVehicle(vehicle)
      setFormData({ ...formData, vehicle_id: vehicle.id })
      
      // Обновляем список транспортных средств, если его там нет
      if (!vehicles.find(v => v.id === vehicle.id)) {
        setVehicles([...vehicles, vehicle])
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        // Авто не найдено, открываем диалог добавления
        if (vehicleSearchTab === 0) {
          setNewVehicleData({
            ...newVehicleData,
            license_plate: licensePlateSearch.trim().toUpperCase(),
          })
        } else {
          setNewVehicleData({
            ...newVehicleData,
            vin: vinSearch.trim().toUpperCase(),
          })
        }
        resetVehicleForm()
        setOpenAddVehicleDialog(true)
      } else {
        setError(err.response?.data?.detail || 'Ошибка поиска транспортного средства')
      }
    } finally {
      setSearchingVehicle(false)
    }
  }

  const handleSearchCustomer = async () => {
    if (!customerPhone || customerPhone.length < 4) {
      setError('Введите номер телефона для поиска')
      return
    }

    try {
      setSearchingCustomer(true)
      setError('')
      setCustomerSearchAttempted(true)
      const response = await api.get('/customers/search/by-phone', {
        params: { phone: customerPhone }
      })
      const customers = response.data
      setFoundCustomers(customers)
      
      if (customers.length === 1) {
        // Если найден один клиент, выбираем его автоматически
        setSelectedCustomer(customers[0])
        setNewVehicleData({ ...newVehicleData, customer_id: customers[0].id })
      } else if (customers.length > 1) {
        // Если найдено несколько, показываем список для выбора
        setSelectedCustomer(null)
      }
    } catch (err: any) {
      if (err.response?.status === 404 || err.response?.data?.detail?.includes('не найдено')) {
        // Клиент не найден, можно создать нового
        setFoundCustomers([])
        setSelectedCustomer(null)
      } else {
        setError(err.response?.data?.detail || 'Ошибка поиска клиента')
      }
    } finally {
      setSearchingCustomer(false)
    }
  }

  const handleCreateOrSelectCustomer = async () => {
    if (!newVehicleData.brand || !newVehicleData.model) {
      setError('Заполните марку и модель транспортного средства')
      return
    }

    try {
      setCreatingVehicle(true)
      setError('')
      // Создаем или используем существующего клиента
      let customerId = selectedCustomer?.id
      
      if (!customerId) {
        // Проверяем, что данные клиента заполнены
        if (!newCustomerData.full_name || !newCustomerData.phone) {
          setError('Заполните ФИО и телефон клиента')
          return
        }
        // Создаем нового клиента
        const customerResponse = await api.post('/customers/', newCustomerData)
        customerId = customerResponse.data.id
        setSelectedCustomer(customerResponse.data)
      }

      // Создаем транспортное средство
      const vehicleResponse = await api.post('/vehicles/', {
        ...newVehicleData,
        customer_id: customerId,
      })
      const vehicle = vehicleResponse.data
      
      setSelectedVehicle(vehicle)
      setFormData({ ...formData, vehicle_id: vehicle.id })
      setVehicles([...vehicles, vehicle])
      setOpenAddVehicleDialog(false)
      
      // Очищаем форму
      resetVehicleForm()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка создания транспортного средства')
    } finally {
      setCreatingVehicle(false)
    }
  }

  const handlePaymentConfirm = async () => {
    if (!editingOrder) return

    const paymentAmountNum = parseFloat(paymentAmount.replace(/\s/g, '').replace(',', '.'))
    const totalAmount = Number(editingOrder.total_amount)
    const currentPaidAmount = Number(editingOrder.paid_amount || 0)

    if (isNaN(paymentAmountNum) || paymentAmountNum <= 0) {
      setError('Введите корректную сумму оплаты')
      return
    }

    // Проверяем, не превышает ли новый платеж остаток к оплате
    const remainingAmount = totalAmount - currentPaidAmount
    if (paymentAmountNum > remainingAmount + 0.01) {
      setError(`Сумма платежа (${formatCurrency(paymentAmountNum)}) превышает остаток к оплате (${formatCurrency(remainingAmount)})`)
      return
    }

    // Обновляем paid_amount: добавляем новый платеж к уже оплаченной сумме
    const newPaidAmount = currentPaidAmount + paymentAmountNum
    // Статус переходит в "оплачен" только если сумма полностью оплачена (с учетом округления)
    const isFullyPaid = newPaidAmount >= totalAmount - 0.01

    setEditingOrder({
      ...editingOrder,
      paid_amount: newPaidAmount,
      status: isFullyPaid ? 'paid' : editingOrder.status
    })

    setOpenPaymentDialog(false)
    setPaymentAmount('')
    setError('') // Очищаем ошибки при успешной оплате
  }

  const handleSaveEdit = async () => {
    if (!selectedVehicle) return

    try {
      setSavingEdit(true)
      setError('')

      if (editMode === 'vehicle') {
        // Обновляем транспортное средство
        const updateData: any = {}
        if (editingVehicleData.brand) updateData.brand = editingVehicleData.brand
        if (editingVehicleData.model) updateData.model = editingVehicleData.model
        if (editingVehicleData.year !== undefined) updateData.year = editingVehicleData.year
        if (editingVehicleData.license_plate !== undefined) updateData.license_plate = editingVehicleData.license_plate || null
        if (editingVehicleData.vin !== undefined) updateData.vin = editingVehicleData.vin || null

        const response = await api.put(`/vehicles/${selectedVehicle.id}`, updateData)
        
        // Обновляем selectedVehicle с новыми данными
        const updatedVehicle = response.data
        setSelectedVehicle(updatedVehicle)
        setEditingVehicle(updatedVehicle)
      } else if (editMode === 'customer' && selectedVehicle.customer) {
        // Обновляем клиента
        const updateData: any = {}
        if (editingCustomerData.full_name) updateData.full_name = editingCustomerData.full_name
        if (editingCustomerData.phone) updateData.phone = editingCustomerData.phone
        if (editingCustomerData.email !== undefined) updateData.email = editingCustomerData.email || null
        if (editingCustomerData.address !== undefined) updateData.address = editingCustomerData.address || null
        if (editingCustomerData.notes !== undefined) updateData.notes = editingCustomerData.notes || null

        const response = await api.put(`/customers/${selectedVehicle.customer.id}`, updateData)
        
        // Обновляем selectedVehicle с новыми данными клиента
        const updatedCustomer = response.data
        if (selectedVehicle) {
          const updatedVehicle = {
            ...selectedVehicle,
            customer: updatedCustomer
          }
          setSelectedVehicle(updatedVehicle as Vehicle)
          setEditingVehicle(updatedVehicle as Vehicle)
        }
      }

      setOpenEditVehicleDialog(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка сохранения изменений')
    } finally {
      setSavingEdit(false)
    }
  }

  const resetVehicleForm = () => {
      setNewVehicleData({
        brand: '',
        model: '',
        license_plate: '',
        vin: '',
        year: undefined,
      customer_id: 0,
    })
    setCustomerPhone('+7')
    setFoundCustomers([])
    setSelectedCustomer(null)
    setCustomerSearchAttempted(false)
    setNewCustomerData({
      full_name: '',
      phone: '',
      email: undefined,
    })
  }

  // Обработчик изменения телефона с маской
  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value
    
    // Убираем все кроме цифр и +
    const digits = value.replace(/[^\d+]/g, '')
    
    // Если номер не начинается с +7, добавляем +7
    if (!digits.startsWith('+7')) {
      if (digits.startsWith('7')) {
        value = '+7' + digits.slice(1)
      } else if (digits.startsWith('8')) {
        value = '+7' + digits.slice(1)
      } else {
        value = '+7' + digits.replace(/^\+?/, '')
      }
    }
    
    // Ограничиваем длину (макс 12 символов: +7XXXXXXXXXX)
    if (value.length > 12) {
      value = value.slice(0, 12)
    }

    setCustomerPhone(value)
    setNewCustomerData({ ...newCustomerData, phone: value })
  }

  const handlePhoneKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Предотвращаем удаление +7 при нажатии Backspace, если курсор находится в начале
    const input = e.currentTarget
    if (e.key === 'Backspace' && input.selectionStart !== null && input.selectionStart <= 2) {
      e.preventDefault()
    }
    // Предотвращаем перемещение курсора влево от +7
    if (e.key === 'ArrowLeft' && input.selectionStart !== null && input.selectionStart <= 2) {
      e.preventDefault()
      input.setSelectionRange(2, 2)
    }
  }

  const handlePhoneFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    // Устанавливаем курсор после +7
    const input = e.currentTarget
    if (!input.value || input.value === '+7') {
      input.setSelectionRange(2, 2)
    }
  }

  const handleVINChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 17)
    setVinSearch(value)
  }

  const handleAddWork = () => {
        const newWork: OrderWorkCreate = {
      work_id: null,
      work_name: null,
      quantity: 1,
      price: 0,
      discount: 0,
        }
        setFormData({
          ...formData,
          order_works: [...formData.order_works, newWork],
        })
  }

  const handleUpdateWork = (index: number, field: keyof OrderWorkCreate, value: any) => {
    const updated = [...formData.order_works]
    updated[index] = { ...updated[index], [field]: value }
    setFormData({ ...formData, order_works: updated })
  }

  const handleRemoveWork = (index: number) => {
    setFormData({
      ...formData,
      order_works: formData.order_works.filter((_, i) => i !== index),
    })
  }

  const handleAddPart = () => {
        const newPart: OrderPartCreate = {
      part_id: null,
      part_name: null,
      article: null,
      quantity: 1,
      price: 0,
      discount: 0,
        }
        setFormData({
          ...formData,
          order_parts: [...formData.order_parts, newPart],
        })
  }

  const handleUpdatePart = (index: number, field: keyof OrderPartCreate, value: any) => {
    const updated = [...formData.order_parts]
    updated[index] = { ...updated[index], [field]: value }
    setFormData({ ...formData, order_parts: updated })
  }

  const handleRemovePart = (index: number) => {
    setFormData({
      ...formData,
      order_parts: formData.order_parts.filter((_, i) => i !== index),
    })
  }

  const calculateWorkRowTotal = (work: OrderWorkCreate) => {
    const discount = work.discount || 0
    const priceWithDiscount = work.price * (1 - discount / 100)
    return priceWithDiscount * work.quantity
  }

  const calculatePartRowTotal = (part: OrderPartCreate) => {
    const discount = part.discount || 0
    const priceWithDiscount = part.price * (1 - discount / 100)
    return priceWithDiscount * part.quantity
  }

  const calculateTotal = () => {
    const worksTotal = formData.order_works.reduce((sum, ow) => sum + calculateWorkRowTotal(ow), 0)
    const partsTotal = formData.order_parts.reduce((sum, op) => sum + calculatePartRowTotal(op), 0)
    return worksTotal + partsTotal
  }

  const handleSave = async () => {
    if (!formData.vehicle_id) {
      setError('Выберите транспортное средство')
      return
    }

    try {
      setError('')
      setLoading(true)

      // Отправляем все поля включая discount, work_name/part_name, article
      const orderWorksToSend = formData.order_works.map(ow => ({
        work_id: ow.work_id || null,
        work_name: ow.work_name || null,
        quantity: ow.quantity,
        price: ow.price,
        discount: ow.discount || 0,
      }))

      const orderPartsToSend = formData.order_parts.map(op => ({
        part_id: op.part_id || null,
        part_name: op.part_name || null,
        article: op.article || null,
        quantity: op.quantity,
        price: op.price,
        discount: op.discount || 0,
      }))

      if (editingOrder) {
        // Вычисляем сумму нового платежа, если она была изменена через диалог оплаты
        // Если paid_amount изменился относительно исходного значения, отправляем разницу как новый платеж
        const currentPaidAmount = Number(editingOrder.paid_amount || 0)
        const paymentIncrement = currentPaidAmount !== originalPaidAmount ? currentPaidAmount - originalPaidAmount : undefined

        const updateData: OrderUpdate = {
          mechanic_id: formData.mechanic_id || undefined,
          status: editingOrder.status || undefined,
          // Отправляем только сумму нового платежа (разницу), а не итоговую сумму
          paid_amount: paymentIncrement !== undefined && paymentIncrement > 0 ? paymentIncrement : undefined,
          recommendations: formData.recommendations || undefined,
          comments: formData.comments || undefined,
          order_works: orderWorksToSend.length > 0 ? orderWorksToSend : undefined,
          order_parts: orderPartsToSend.length > 0 ? orderPartsToSend : undefined,
        }
        await api.put(`/orders/${editingOrder.id}`, updateData)
      } else {
        const createData = {
          ...formData,
          order_works: orderWorksToSend,
          order_parts: orderPartsToSend,
        }
        await api.post('/orders/', createData)
      }

      handleCloseDialog()
      loadOrders()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка сохранения заказ-наряда')
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = async (orderId: number) => {
    try {
      setLoading(true)
      await api.post(`/orders/${orderId}/complete`)
      loadOrders()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка завершения заказ-наряда')
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (orderId: number, newStatus: string) => {
    try {
      setLoading(true)
      const updateData: OrderUpdate = {
        status: newStatus as any,
      }
      await api.put(`/orders/${orderId}`, updateData)
      loadOrders()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка изменения статуса')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (orderId: number) => {
    if (!window.confirm('Вы уверены, что хотите отменить этот заказ-наряд?')) {
      return
    }

    try {
      setLoading(true)
      await api.post(`/orders/${orderId}/cancel`)
      loadOrders()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка отмены заказ-наряда')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ru-RU')
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
    }).format(amount)
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <IconButton onClick={() => navigate('/')} color="primary">
              <HomeIcon />
            </IconButton>
            <Typography variant="h4" component="h1">
              Заказ-наряды
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Создать заказ-наряд
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Фильтр по статусу */}
        <Box sx={{ mb: 2 }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Фильтр по статусу</InputLabel>
            <Select
              value={selectedStatusFilter}
              onChange={(e) => setSelectedStatusFilter(e.target.value)}
              label="Фильтр по статусу"
            >
              <MenuItem value="">
                <em>Все статусы</em>
              </MenuItem>
              {orderStatuses.map((status) => (
                <MenuItem key={status.value} value={status.value}>
                  {status.label}
                </MenuItem>
              ))}
              {/* Для админов добавляем статус "Завершен" в фильтр */}
              {currentUser?.role === 'admin' && (
                <MenuItem value="completed">
                  Завершен
                </MenuItem>
              )}
            </Select>
          </FormControl>
        </Box>

        {loading && !orders.length ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Номер</TableCell>
                  <TableCell>Транспортное средство</TableCell>
                  <TableCell>Клиент</TableCell>
                  <TableCell>Механик</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>Сумма</TableCell>
                  <TableCell>Оплачено</TableCell>
                  <TableCell>Дата создания</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell>{order.number}</TableCell>
                    <TableCell>
                      {order.vehicle ? (
                        <>
                          {order.vehicle.brand} {order.vehicle.model}
                          {order.vehicle.license_plate && ` (${order.vehicle.license_plate})`}
                        </>
                      ) : '-'}
                    </TableCell>
                    <TableCell>{order.vehicle?.customer?.full_name || '-'}</TableCell>
                    <TableCell>
                      {order.mechanic ? order.mechanic.full_name : '-'}
                    </TableCell>
                    <TableCell>
                      {order.status === 'completed' || order.status === 'cancelled' ? (
                      <Chip
                          label={STATUS_LABELS[order.status] || order.status}
                          color={STATUS_COLORS[order.status] || 'default'}
                        size="small"
                      />
                      ) : (
                        <FormControl size="small" sx={{ minWidth: 150 }}>
                          <Select
                            value={order.status}
                            onChange={(e) => handleStatusChange(order.id, e.target.value)}
                            size="small"
                          >
                            {orderStatuses.map((status) => (
                              <MenuItem key={status.value} value={status.value}>
                                {status.label}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      )}
                    </TableCell>
                    <TableCell>{formatCurrency(Number(order.total_amount))}</TableCell>
                    <TableCell>{formatCurrency(Number(order.paid_amount))}</TableCell>
                    <TableCell>{formatDate(order.created_at)}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(order)}
                        disabled={
                          currentUser?.role !== 'admin' && 
                          (order.status === 'paid' || order.status === 'cancelled' || order.status === 'completed')
                        }
                      >
                        <EditIcon />
                      </IconButton>
                      {(order.status === 'ready_for_payment' || order.status === 'paid') && (
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => handleComplete(order.id)}
                        >
                          <CheckCircleIcon />
                        </IconButton>
                      )}
                      {order.status !== 'cancelled' && order.status !== 'completed' && order.status !== 'paid' && (
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleCancel(order.id)}
                        >
                          <CancelIcon />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Диалог создания/редактирования */}
        <Dialog 
          open={openDialog} 
          onClose={handleCloseDialog} 
          fullScreen
          PaperProps={{
            sx: {
              height: '100vh',
              maxHeight: '100vh',
            }
          }}
        >
          <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 2, borderBottom: 1, borderColor: 'divider' }}>
            <IconButton onClick={handleCloseDialog} color="primary" sx={{ mr: 1 }}>
              <ArrowBackIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {editingOrder ? 'Редактировать заказ-наряд' : 'Создать заказ-наряд'}
            </Typography>
          </DialogTitle>
          <DialogContent sx={{ overflowY: 'auto', flex: 1, py: 2 }}>
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="subtitle1" gutterBottom>
                    Транспортное средство *
                  </Typography>
                  {editingOrder ? (
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body1">
                          {selectedVehicle?.brand} {selectedVehicle?.model}
                          {selectedVehicle?.license_plate && ` (${selectedVehicle.license_plate})`}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Владелец: {selectedVehicle?.customer?.full_name || '-'}
                        </Typography>
                      </CardContent>
                    </Card>
                  ) : (
                    <Box>
                      <Tabs value={vehicleSearchTab} onChange={(_, newValue) => setVehicleSearchTab(newValue)} sx={{ mb: 2 }}>
                        <Tab label="По гос номеру" />
                        <Tab label="По VIN номеру" />
                      </Tabs>
                      
                      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                        {vehicleSearchTab === 0 ? (
                          <TextField
                            fullWidth
                            label="Гос номер"
                            value={licensePlateSearch}
                            onChange={(e) => setLicensePlateSearch(e.target.value.toUpperCase())}
                            placeholder="Например: А123БВ777"
                            InputProps={{
                              endAdornment: (
                                <InputAdornment position="end">
                                  <IconButton
                                    onClick={handleSearchVehicle}
                                    disabled={!licensePlateSearch.trim() || searchingVehicle}
                                    edge="end"
                                  >
                                    {searchingVehicle ? <CircularProgress size={20} /> : <SearchIcon />}
                                  </IconButton>
                                </InputAdornment>
                              ),
                            }}
                            onKeyPress={(e) => {
                              if (e.key === 'Enter' && licensePlateSearch.trim()) {
                                handleSearchVehicle()
                              }
                            }}
                          />
                        ) : (
                          <TextField
                            fullWidth
                            label="VIN номер"
                            value={vinSearch}
                            onChange={handleVINChange}
                            placeholder="17 символов"
                            inputProps={{
                              maxLength: 17,
                              pattern: '[A-Z0-9]{17}',
                            }}
                            helperText={`${vinSearch.length}/17 символов`}
                            InputProps={{
                              endAdornment: (
                                <InputAdornment position="end">
                                  <IconButton
                                    onClick={handleSearchVehicle}
                                    disabled={vinSearch.length !== 17 || searchingVehicle}
                                    edge="end"
                                  >
                                    {searchingVehicle ? <CircularProgress size={20} /> : <SearchIcon />}
                                  </IconButton>
                                </InputAdornment>
                              ),
                            }}
                            onKeyPress={(e) => {
                              if (e.key === 'Enter' && vinSearch.length === 17) {
                                handleSearchVehicle()
                              }
                            }}
                          />
                        )}
                      </Box>

                      {selectedVehicle && (
                        <Card variant="outlined" sx={{ bgcolor: 'success.light', bgOpacity: 0.1, mb: 2 }}>
                          <CardContent>
                            <Typography variant="subtitle2" gutterBottom color="success.main">
                              ✓ Транспортное средство найдено
                            </Typography>
                            <Typography variant="body1" gutterBottom>
                              {selectedVehicle.brand} {selectedVehicle.model}
                              {selectedVehicle.year && ` (${selectedVehicle.year})`}
                            </Typography>
                            {selectedVehicle.license_plate && (
                              <Typography variant="body2" color="text.secondary">
                                Гос номер: {selectedVehicle.license_plate}
                              </Typography>
                            )}
                            {selectedVehicle.vin && (
                              <Typography variant="body2" color="text.secondary">
                                VIN: {selectedVehicle.vin}
                              </Typography>
                            )}
                            {selectedVehicle.customer && (
                              <>
                            <Typography variant="body2" color="text.secondary">
                                  Владелец: {selectedVehicle.customer.full_name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                  Телефон: {selectedVehicle.customer.phone}
                            </Typography>
                                {selectedVehicle.customer.email && (
                              <Typography variant="body2" color="text.secondary">
                                    Email: {selectedVehicle.customer.email}
                              </Typography>
                                )}
                              </>
                            )}
                            <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<EditIcon />}
                                onClick={() => {
                                  if (selectedVehicle) {
                                    setEditingVehicle(selectedVehicle)
                                    setEditingVehicleData({
                                      brand: selectedVehicle.brand,
                                      model: selectedVehicle.model,
                                      license_plate: selectedVehicle.license_plate || '',
                                      vin: selectedVehicle.vin || '',
                                      year: selectedVehicle.year,
                                    })
                                    setEditMode('vehicle')
                                    setOpenEditVehicleDialog(true)
                                  }
                                }}
                              >
                                Редактировать
                              </Button>
                            <Button
                              size="small"
                              onClick={() => {
                                setSelectedVehicle(null)
                                setFormData({ ...formData, vehicle_id: 0 })
                                setLicensePlateSearch('')
                                setVinSearch('')
                              }}
                            >
                              Выбрать другое
                            </Button>
                            </Box>
                          </CardContent>
                        </Card>
                      )}
                    </Box>
                  )}
                </Grid>

                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>Механик (опционально)</InputLabel>
                    <Select
                      value={formData.mechanic_id || ''}
                      onChange={(e) => setFormData({ ...formData, mechanic_id: e.target.value ? Number(e.target.value) : undefined })}
                      label="Механик (опционально)"
                    >
                      <MenuItem value="">
                        <em>Не назначен</em>
                      </MenuItem>
                      {employees.map((employee) => (
                        <MenuItem key={employee.id} value={employee.id}>
                          {employee.full_name} ({employee.position})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                {editingOrder && (
                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth>
                      <InputLabel>Статус</InputLabel>
                      <Select
                        value={editingOrder.status}
                        onChange={(e) => {
                          const newStatus = e.target.value as string
                          setEditingOrder({ ...editingOrder, status: newStatus as any })
                        }}
                        label="Статус"
                      >
                        {/* Базовые статусы из API */}
                        {orderStatuses.map((status) => (
                          <MenuItem key={status.value} value={status.value}>
                            {status.label}
                          </MenuItem>
                        ))}
                        {/* Для админов добавляем статус "Завершен" */}
                        {currentUser?.role === 'admin' && (
                          <MenuItem value="completed">
                            Завершен
                          </MenuItem>
                        )}
                      </Select>
                    </FormControl>
                  </Grid>
                )}

                {editingOrder && (
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                      <Typography variant="body2" color="text.secondary">
                        Сумма: <strong>{formatCurrency(Number(editingOrder.total_amount))}</strong>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Оплачено: <strong>{formatCurrency(Number(editingOrder.paid_amount))}</strong>
                      </Typography>
                      {editingOrder.status !== 'paid' && editingOrder.status !== 'completed' && editingOrder.status !== 'cancelled' && (
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<PaymentIcon />}
                          onClick={() => {
                            setPaymentAmount(Number(editingOrder.total_amount).toFixed(2))
                            setOpenPaymentDialog(true)
                          }}
                          sx={{ ml: 'auto' }}
                        >
                          Оплата
                        </Button>
                      )}
                    </Box>
                  </Grid>
                )}

                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6">Работы</Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={handleAddWork}
                    >
                      Добавить работу
                    </Button>
                  </Box>

                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                          <TableCell width="30%">Работа</TableCell>
                          <TableCell align="right" width="10%">Количество</TableCell>
                          <TableCell align="right" width="12%">Цена</TableCell>
                          <TableCell align="right" width="10%">Скидка (%)</TableCell>
                          <TableCell align="right" width="12%">Цена со скидкой</TableCell>
                          <TableCell align="right" width="12%">Итого</TableCell>
                          <TableCell align="center" width="10%">Действия</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                        {formData.order_works.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                              Нет добавленных работ
                            </TableCell>
                          </TableRow>
                        ) : (
                          formData.order_works.map((ow, index) => {
                            const discount = ow.discount || 0
                            const priceWithDiscount = ow.price * (1 - discount / 100)
                            const rowTotal = calculateWorkRowTotal(ow)
                            return (
                              <TableRow key={index}>
                                <TableCell>
                                  <TextField
                                    placeholder="Название работы"
                                    value={ow.work_name || ''}
                                    onChange={(e) => handleUpdateWork(index, 'work_name', e.target.value)}
                                    size="small"
                                    fullWidth
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <TextField
                                    type="number"
                                    value={ow.quantity}
                                    onChange={(e) => handleUpdateWork(index, 'quantity', Number(e.target.value) || 1)}
                                    size="small"
                                    inputProps={{ min: 1, style: { textAlign: 'right' } }}
                                    sx={{ width: 80 }}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <TextField
                                    type="number"
                                    value={ow.price}
                                    onChange={(e) => handleUpdateWork(index, 'price', Number(e.target.value) || 0)}
                                    size="small"
                                    inputProps={{ min: 0, step: 0.01, style: { textAlign: 'right' } }}
                                    sx={{ width: 100 }}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <TextField
                                    type="number"
                                    value={discount}
                                    onChange={(e) => handleUpdateWork(index, 'discount', Number(e.target.value) || 0)}
                                    size="small"
                                    inputProps={{ min: 0, max: 100, step: 0.01, style: { textAlign: 'right' } }}
                                    sx={{ width: 80 }}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  {formatCurrency(priceWithDiscount)}
                                </TableCell>
                                <TableCell align="right">
                                  <strong>{formatCurrency(rowTotal)}</strong>
                                </TableCell>
                                <TableCell align="center">
                                  <IconButton
                                    size="small"
                                    color="error"
                                    onClick={() => handleRemoveWork(index)}
                                  >
                                    <DeleteIcon />
                                  </IconButton>
                                </TableCell>
                              </TableRow>
                            )
                          })
                        )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                </Grid>

                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2, mt: 3 }}>
                    <Typography variant="h6">Запчасти</Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={handleAddPart}
                    >
                      Добавить запчасть
                    </Button>
                  </Box>

                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell width="25%">Запчасть</TableCell>
                            <TableCell width="10%">Артикул</TableCell>
                            <TableCell align="right" width="8%">Количество</TableCell>
                            <TableCell align="right" width="10%">Цена</TableCell>
                            <TableCell align="right" width="8%">Скидка (%)</TableCell>
                            <TableCell align="right" width="11%">Цена со скидкой</TableCell>
                            <TableCell align="right" width="12%">Итого</TableCell>
                            <TableCell align="center" width="8%">Действия</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                        {formData.order_parts.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={8} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                              Нет добавленных запчастей
                            </TableCell>
                          </TableRow>
                        ) : (
                          formData.order_parts.map((op, index) => {
                            const discount = op.discount || 0
                            const priceWithDiscount = op.price * (1 - discount / 100)
                            const rowTotal = calculatePartRowTotal(op)
                            return (
                              <TableRow key={index}>
                                <TableCell>
                                  <TextField
                                    placeholder="Название запчасти"
                                    value={op.part_name || ''}
                                    onChange={(e) => handleUpdatePart(index, 'part_name', e.target.value)}
                                    size="small"
                                    fullWidth
                                  />
                                </TableCell>
                                <TableCell>
                                  <TextField
                                    placeholder="Артикул"
                                    value={op.article || ''}
                                    onChange={(e) => handleUpdatePart(index, 'article', e.target.value)}
                                    size="small"
                                    fullWidth
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <TextField
                                    type="number"
                                    value={op.quantity}
                                    onChange={(e) => handleUpdatePart(index, 'quantity', Number(e.target.value) || 1)}
                                    size="small"
                                    inputProps={{ min: 1, style: { textAlign: 'right' } }}
                                    sx={{ width: 80 }}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <TextField
                                    type="number"
                                    value={op.price}
                                    onChange={(e) => handleUpdatePart(index, 'price', Number(e.target.value) || 0)}
                                    size="small"
                                    inputProps={{ min: 0, step: 0.01, style: { textAlign: 'right' } }}
                                    sx={{ width: 100 }}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  <TextField
                                    type="number"
                                    value={discount}
                                    onChange={(e) => handleUpdatePart(index, 'discount', Number(e.target.value) || 0)}
                                    size="small"
                                    inputProps={{ min: 0, max: 100, step: 0.01, style: { textAlign: 'right' } }}
                                    sx={{ width: 80 }}
                                  />
                                </TableCell>
                                <TableCell align="right">
                                  {formatCurrency(priceWithDiscount)}
                                </TableCell>
                                <TableCell align="right">
                                  <strong>{formatCurrency(rowTotal)}</strong>
                                </TableCell>
                                <TableCell align="center">
                                  <IconButton
                                    size="small"
                                    color="error"
                                    onClick={() => handleRemovePart(index)}
                                  >
                                    <DeleteIcon />
                                  </IconButton>
                                </TableCell>
                              </TableRow>
                            )
                          })
                        )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Рекомендации"
                    value={formData.recommendations || ''}
                    onChange={(e) => setFormData({ ...formData, recommendations: e.target.value })}
                    multiline
                    rows={3}
                    placeholder="Рекомендации по обслуживанию..."
                  />
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Комментарии"
                    value={formData.comments || ''}
                    onChange={(e) => setFormData({ ...formData, comments: e.target.value })}
                    multiline
                    rows={3}
                    placeholder="Дополнительные комментарии..."
                  />
                </Grid>

                <Grid item xs={12}>
                  <Card variant="outlined" sx={{ bgcolor: 'background.default' }}>
                    <CardContent>
                      <Typography variant="h6" align="right">
                        Итого: {formatCurrency(calculateTotal())}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          </DialogContent>
          <DialogActions sx={{ borderTop: 1, borderColor: 'divider', px: 3, py: 2 }}>
            <Button onClick={handleCloseDialog} size="large">Отмена</Button>
            <Button
              onClick={handleSave}
              variant="contained"
              size="large"
              disabled={loading || !formData.vehicle_id}
            >
              {loading ? <CircularProgress size={24} /> : 'Сохранить'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Диалог добавления нового автомобиля */}
        <Dialog open={openAddVehicleDialog} onClose={() => {
          setOpenAddVehicleDialog(false)
          resetVehicleForm()
        }} maxWidth="sm" fullWidth>
          <DialogTitle>Добавить новое транспортное средство</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Марка *"
                    value={newVehicleData.brand}
                    onChange={(e) => setNewVehicleData({ ...newVehicleData, brand: e.target.value })}
                    required
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Модель *"
                    value={newVehicleData.model}
                    onChange={(e) => setNewVehicleData({ ...newVehicleData, model: e.target.value })}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Год выпуска"
                    type="number"
                    value={newVehicleData.year || ''}
                    onChange={(e) => setNewVehicleData({ 
                      ...newVehicleData, 
                      year: e.target.value ? Number(e.target.value) : undefined 
                    })}
                    inputProps={{ min: 1900, max: new Date().getFullYear() + 1 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Гос номер"
                    value={newVehicleData.license_plate || ''}
                    onChange={(e) => setNewVehicleData({ 
                      ...newVehicleData, 
                      license_plate: e.target.value.toUpperCase() 
                    })}
                    placeholder="А123БВ777"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="VIN номер"
                    value={newVehicleData.vin || ''}
                    onChange={(e) => {
                      const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 17)
                      setNewVehicleData({ ...newVehicleData, vin: value })
                    }}
                    inputProps={{ maxLength: 17 }}
                    helperText={`${(newVehicleData.vin || '').length}/17 символов`}
                    placeholder="17 символов"
                  />
                </Grid>
                <Grid item xs={12}>
                  <Divider sx={{ my: 1 }}>Клиент</Divider>
                </Grid>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                      label="Телефон клиента *"
                      value={customerPhone}
                      onChange={handlePhoneChange}
                      onKeyDown={handlePhoneKeyDown}
                      onFocus={handlePhoneFocus}
                      placeholder="+7 123 456 78 90"
                    required
                      InputProps={{
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton
                              onClick={handleSearchCustomer}
                              disabled={customerPhone.length < 4 || searchingCustomer}
                              edge="end"
                            >
                              {searchingCustomer ? <CircularProgress size={20} /> : <SearchIcon />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }}
                    />
                  </Box>
                </Grid>

                {customerSearchAttempted && foundCustomers.length === 0 && !selectedCustomer && (
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="ФИО клиента *"
                      value={newCustomerData.full_name}
                      onChange={(e) => setNewCustomerData({ ...newCustomerData, full_name: e.target.value })}
                      required
                      sx={{ mb: 2 }}
                    />
                    <TextField
                      fullWidth
                      label="Email"
                      type="email"
                      value={newCustomerData.email || ''}
                      onChange={(e) => setNewCustomerData({ 
                        ...newCustomerData, 
                        email: e.target.value || undefined 
                      })}
                      placeholder="email@example.com"
                    />
                  </Grid>
                )}

                {foundCustomers.length > 1 && !selectedCustomer && (
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Найдено несколько клиентов. Выберите:
                    </Typography>
                    {foundCustomers.map((customer) => (
                      <Card
                        key={customer.id}
                        variant="outlined"
                        sx={{ mb: 1, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                        onClick={() => {
                          setSelectedCustomer(customer)
                          setNewVehicleData({ ...newVehicleData, customer_id: customer.id })
                        }}
                      >
                        <CardContent>
                          <Typography variant="body2">{customer.full_name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {customer.phone} {customer.email && `• ${customer.email}`}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))}
                  </Grid>
                )}

                {selectedCustomer && (
                  <Grid item xs={12}>
                    <Card variant="outlined" sx={{ bgcolor: 'success.light', bgOpacity: 0.1 }}>
                      <CardContent>
                        <Typography variant="subtitle2" color="success.main">
                          ✓ Клиент найден
                        </Typography>
                        <Typography variant="body2">{selectedCustomer.full_name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {selectedCustomer.phone} {selectedCustomer.email && `• ${selectedCustomer.email}`}
                        </Typography>
                        <Button
                          size="small"
                          onClick={() => {
                            setSelectedCustomer(null)
                            setFoundCustomers([])
                            setCustomerSearchAttempted(false)
                            setNewVehicleData({ ...newVehicleData, customer_id: 0 })
                          }}
                          sx={{ mt: 1 }}
                        >
                          Выбрать другого
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                )}

              </Grid>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setOpenAddVehicleDialog(false)
              resetVehicleForm()
            }}>Отмена</Button>
            <Button
              onClick={handleCreateOrSelectCustomer}
              variant="contained"
              disabled={creatingVehicle || !newVehicleData.brand || !newVehicleData.model || (!selectedCustomer && !newCustomerData.full_name)}
            >
              {creatingVehicle ? <CircularProgress size={24} /> : 'Добавить'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Диалог редактирования транспортного средства/клиента */}
        <Dialog open={openEditVehicleDialog} onClose={() => {
          setOpenEditVehicleDialog(false)
          setEditMode('vehicle') // Сбрасываем режим при закрытии
        }} maxWidth="sm" fullWidth>
          <DialogTitle>
            {editMode === 'vehicle' ? 'Редактировать транспортное средство' : 'Редактировать клиента'}
          </DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              {editMode === 'vehicle' ? (
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                  <TextField
                    fullWidth
                      label="Марка *"
                      value={editingVehicleData.brand}
                      onChange={(e) => setEditingVehicleData({ ...editingVehicleData, brand: e.target.value })}
                    required
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Модель *"
                      value={editingVehicleData.model}
                      onChange={(e) => setEditingVehicleData({ ...editingVehicleData, model: e.target.value })}
                      required
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="Год выпуска"
                      type="number"
                      value={editingVehicleData.year || ''}
                      onChange={(e) => setEditingVehicleData({ ...editingVehicleData, year: e.target.value ? parseInt(e.target.value) : undefined })}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="Гос номер"
                      value={editingVehicleData.license_plate || ''}
                      onChange={(e) => setEditingVehicleData({ ...editingVehicleData, license_plate: e.target.value.toUpperCase() })}
                      placeholder="А123БВ777"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="VIN номер"
                      value={editingVehicleData.vin || ''}
                      onChange={(e) => {
                        const value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 17)
                        setEditingVehicleData({ ...editingVehicleData, vin: value })
                      }}
                      inputProps={{ maxLength: 17 }}
                      helperText={`${(editingVehicleData.vin || '').length}/17 символов`}
                      placeholder="17 символов"
                    />
                  </Grid>
                  {selectedVehicle?.customer && (
                    <Grid item xs={12}>
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          Клиент: {selectedVehicle.customer.full_name}
                        </Typography>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            if (selectedVehicle.customer) {
                              setEditingCustomer(selectedVehicle.customer)
                              setEditingCustomerData({
                                full_name: selectedVehicle.customer.full_name,
                                phone: selectedVehicle.customer.phone,
                                email: selectedVehicle.customer.email || '',
                                address: selectedVehicle.customer.address || '',
                                notes: selectedVehicle.customer.notes || '',
                              })
                              setEditMode('customer')
                            }
                          }}
                        >
                          Редактировать клиента
                        </Button>
                      </Box>
                    </Grid>
                  )}
                </Grid>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Box sx={{ mb: 2 }}>
                      <Button
                        size="small"
                        startIcon={<ArrowBackIcon />}
                        onClick={() => {
                          // Возвращаемся к редактированию машины
                          if (selectedVehicle) {
                            setEditingVehicleData({
                              brand: selectedVehicle.brand,
                              model: selectedVehicle.model,
                              license_plate: selectedVehicle.license_plate || '',
                              vin: selectedVehicle.vin || '',
                              year: selectedVehicle.year,
                            })
                          }
                          setEditMode('vehicle')
                        }}
                      >
                        Назад к редактированию транспортного средства
                      </Button>
                    </Box>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="ФИО *"
                      value={editingCustomerData.full_name}
                      onChange={(e) => setEditingCustomerData({ ...editingCustomerData, full_name: e.target.value })}
                      required
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Телефон *"
                      value={editingCustomerData.phone}
                      onChange={(e) => {
                        let value = e.target.value
                        const digits = value.replace(/[^\d+]/g, '')
                        if (!digits.startsWith('+7')) {
                          if (digits.startsWith('7')) {
                            value = '+7' + digits.slice(1)
                          } else if (digits.startsWith('8')) {
                            value = '+7' + digits.slice(1)
                          } else {
                            value = '+7' + digits.replace(/^\+?/, '')
                          }
                        }
                        if (value.length > 12) {
                          value = value.slice(0, 12)
                        }
                        setEditingCustomerData({ ...editingCustomerData, phone: value })
                      }}
                      placeholder="+7 123 456 78 90"
                      required
                    />
                  </Grid>
                  <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Email"
                    type="email"
                      value={editingCustomerData.email}
                      onChange={(e) => setEditingCustomerData({ ...editingCustomerData, email: e.target.value })}
                    placeholder="email@example.com"
                  />
                </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Адрес"
                      value={editingCustomerData.address}
                      onChange={(e) => setEditingCustomerData({ ...editingCustomerData, address: e.target.value })}
                      multiline
                      rows={2}
                    />
              </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Заметки"
                      value={editingCustomerData.notes}
                      onChange={(e) => setEditingCustomerData({ ...editingCustomerData, notes: e.target.value })}
                      multiline
                      rows={2}
                    />
                  </Grid>
                </Grid>
              )}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setOpenEditVehicleDialog(false)
              setEditMode('vehicle') // Сбрасываем режим при закрытии
            }}>Отмена</Button>
            <Button
              onClick={handleSaveEdit}
              variant="contained"
              disabled={savingEdit || (editMode === 'vehicle' && (!editingVehicleData.brand || !editingVehicleData.model)) || (editMode === 'customer' && (!editingCustomerData.full_name || !editingCustomerData.phone))}
            >
              {savingEdit ? <CircularProgress size={24} /> : 'Сохранить'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Диалог оплаты */}
        <Dialog open={openPaymentDialog} onClose={() => setOpenPaymentDialog(false)} maxWidth="xs" fullWidth>
          <DialogTitle>Оплата заказа</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              {editingOrder && (() => {
                const total = Number(editingOrder.total_amount)
                const paid = Number(editingOrder.paid_amount || 0)
                const remaining = total - paid
                const paymentAmountNum = parseFloat(paymentAmount) || 0
                const newPaid = paid + paymentAmountNum
                const willBeFullyPaid = newPaid >= total - 0.01

                return (
                  <>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Сумма заказа: <strong>{formatCurrency(total)}</strong>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Уже оплачено: <strong>{formatCurrency(paid)}</strong>
                      </Typography>
                    </Box>
                    <TextField
                      fullWidth
                      label="Сумма оплаты *"
                      type="number"
                      value={paymentAmount}
                      onChange={(e) => setPaymentAmount(e.target.value)}
                      inputProps={{ step: '0.01', min: '0' }}
                      placeholder="0.00"
                    />
                    {remaining > 0 && (
                      <Typography variant="body2" color="primary" sx={{ mt: 1, fontWeight: 'medium' }}>
                        Осталось к оплате: <strong>{formatCurrency(remaining)}</strong>
                      </Typography>
                    )}
                    {willBeFullyPaid && (
                      <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>
                        Заказ будет автоматически переведен в статус "Оплачен"
                      </Typography>
                    )}
                  </>
                )
              })()}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setOpenPaymentDialog(false)
              setPaymentAmount('')
            }}>Отмена</Button>
            <Button
              onClick={handlePaymentConfirm}
              variant="contained"
              disabled={!paymentAmount || isNaN(parseFloat(paymentAmount.replace(/\s/g, '').replace(',', '.')))}
            >
              Применить
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  )
}
