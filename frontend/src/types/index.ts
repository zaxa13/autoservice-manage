export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'manager' | 'mechanic' | 'accountant'
  employee_id?: number
  is_active: boolean
}

export interface Order {
  id: number
  number: string
  vehicle_id: number
  employee_id: number
  mechanic_id?: number
  status: 'new' | 'estimation' | 'in_progress' | 'ready_for_payment' | 'paid' | 'completed' | 'cancelled'
  total_amount: number
  paid_amount: number
  mileage_at_service?: number
  created_at: string
  completed_at?: string
  vehicle?: Vehicle
  mechanic?: Employee
}

export interface OrderDetail extends Order {
  vehicle: Vehicle
  employee: Employee
  mechanic?: Employee
  order_works: OrderWork[]
  order_parts: OrderPart[]
  recommendations?: string  // Только в детальной информации
  comments?: string  // Только в детальной информации
}

export interface OrderWork {
  id: number
  order_id: number
  work_id: number
  quantity: number
  price: number
  total: number
  work: Work
}

export interface OrderPart {
  id: number
  order_id: number
  part_id: number
  quantity: number
  price: number
  total: number
  part: Part
}

export interface OrderWorkCreate {
  work_id?: number | null
  work_name?: string | null
  quantity: number
  price: number
  discount?: number | null
}

export interface OrderPartCreate {
  part_id?: number | null
  part_name?: string | null
  article?: string | null
  quantity: number
  price: number
  discount?: number | null
}

export interface OrderCreate {
  vehicle_id: number
  mechanic_id?: number
  recommendations?: string
  comments?: string
  order_works: OrderWorkCreate[]
  order_parts: OrderPartCreate[]
}

export interface OrderUpdate {
  mechanic_id?: number
  status?: 'new' | 'estimation' | 'in_progress' | 'ready_for_payment' | 'paid' | 'completed' | 'cancelled'
  paid_amount?: number
  recommendations?: string
  comments?: string
  order_works?: OrderWorkCreate[]
  order_parts?: OrderPartCreate[]
}

export interface Work {
  id: number
  name: string
  description?: string
  price: number
  duration_minutes: number
  category: 'diagnostics' | 'engine' | 'transmission' | 'suspension' | 'brakes' | 'electrical' | 'cooling' | 'fuel_system' | 'exhaust' | 'climate' | 'maintenance' | 'body_work' | 'painting' | 'tire_service' | 'glass' | 'repair' | 'other'
}

export interface Part {
  id: number
  name: string
  part_number: string  // обязателен в БД
  brand?: string
  price: number
  purchase_price_last?: number
  unit: string
  category: 'engine' | 'transmission' | 'suspension' | 'brakes' | 'electrical' | 'body' | 'consumables' | 'other'
}

export interface WarehouseItem {
  id: number
  part_id: number
  quantity: number
  min_quantity: number
  location?: string
  last_updated: string
  part: Part
}

export type TransactionType = 'incoming' | 'outgoing' | 'adjustment'

export interface WarehouseTransaction {
  id: number
  warehouse_item_id: number
  transaction_type: TransactionType
  quantity: number
  price?: number
  order_id?: number
  receipt_id?: number
  employee_id: number
  created_at: string
}

export interface WarehouseTransactionList extends WarehouseTransaction {
  part?: Part
  order_number?: string
  receipt_number?: string
  employee_name?: string
}

export interface Supplier {
  id: number
  name: string
  inn?: string
  kpp?: string
  legal_address?: string
  contact?: string
  bank_name?: string
  bik?: string
  bank_account?: string
  correspondent_account?: string
}

export interface ReceiptLine {
  id: number
  receipt_id: number
  part_id: number
  quantity: number
  purchase_price: number
  sale_price: number
  part?: Part
}

export interface ReceiptDocument {
  id: number
  number: string
  document_date: string
  supplier_id?: number
  supplier_document_number?: string
  supplier_document_date?: string
  status: 'draft' | 'posted'
  created_at: string
  supplier?: Supplier
  lines: ReceiptLine[]
  total_amount?: number
}

export interface ReceiptLineCreate {
  part_id: number
  quantity: number
  purchase_price: number
  sale_price: number
}

export interface ReceiptDocumentCreate {
  document_date: string
  supplier_id?: number
  supplier_document_number?: string
  supplier_document_date?: string
  lines: ReceiptLineCreate[]
}

/** Отчёт по приходу от поставщика за период (сверка). */
export interface SupplierReceiptsReport {
  receipts: ReceiptDocument[]
  total_count: number
  total_amount: number
}

export interface WarehouseAdjustmentCreate {
  warehouse_item_id: number
  quantity_delta: number
  reason?: string
}

export interface Customer {
  id: number
  full_name: string
  phone: string
  email?: string
  address?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export interface CustomerCreate {
  full_name: string
  phone: string
  email?: string
  address?: string
  notes?: string
}

export interface BrandRef {
  id: number
  name: string
}

export interface ModelRef {
  id: number
  name: string
}

export interface Vehicle {
  id: number
  vin?: string
  license_plate?: string
  brand_id: number
  model_id: number
  brand?: BrandRef
  model?: ModelRef
  year?: number
  mileage?: number  // Пробег в км
  customer_id: number
  customer?: Customer
  created_at?: string
}

export interface VehicleCreate {
  vin?: string
  license_plate?: string
  brand_id: number
  model_id: number
  year?: number
  mileage?: number  // Пробег в км
  customer_id: number
}

export interface VehicleHistoryOrder extends OrderDetail {
  // наследует все поля OrderDetail — используется в истории автомобиля
}

export interface Employee {
  id: number
  full_name: string
  position: string
  phone?: string
  email?: string
  hire_date: string
  salary_base: number
  is_active: boolean
}

export interface OrderStatusInfo {
  value: string
  label: string
}

export type AppointmentStatus =
  | 'scheduled'   // Записан
  | 'confirmed'   // Подтверждён
  | 'waiting'     // Ожидаем авто
  | 'arrived'     // Авто на СТО
  | 'in_work'     // В работе
  | 'ready'       // Готов к выдаче
  | 'completed'   // Завершён
  | 'no_show'     // Не явился
  | 'cancelled'   // Отменён

export interface AppointmentPost {
  id: number
  name: string
  max_slots: number
  slot_times?: string[]  // слоты по времени: ["09:00", "11:00", ...]
  color?: string
  sort_order: number
  created_at: string
}

export interface AppointmentPostCreate {
  name: string
  max_slots: number
  slot_times?: string[]
  color?: string
  sort_order?: number
}

export interface AppointmentOrder {
  id: number
  number: string
}

export interface Appointment {
  id: number
  date: string  // YYYY-MM-DD format
  time: string  // HH:MM format
  customer_name: string
  customer_phone: string
  description?: string
  status: AppointmentStatus
  vehicle_id?: number
  employee_id?: number
  post_id?: number
  order_id?: number
  sort_order?: number
  created_at: string
  updated_at?: string
  vehicle?: Vehicle
  employee?: Employee
  order?: AppointmentOrder
}

export interface AppointmentCreate {
  date: string  // YYYY-MM-DD format
  time: string  // HH:MM format
  customer_name: string
  customer_phone: string
  description?: string
  status?: AppointmentStatus
  vehicle_id?: number
  employee_id?: number
  post_id?: number
  sort_order?: number
}

export interface AppointmentUpdate {
  date?: string
  time?: string
  customer_name?: string
  customer_phone?: string
  description?: string
  status?: AppointmentStatus
  vehicle_id?: number
  employee_id?: number
  post_id?: number
  order_id?: number
  sort_order?: number
}
