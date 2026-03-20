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
  mechanic_id?: number | null
  mechanic?: Employee | null
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
  mechanic_id?: number | null
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
  stock_quantity: number  // текущий остаток на складе (из warehouse_items)
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

// ── Reports ───────────────────────────────────────────────────────────────────

export interface RevenueByDayItem {
  date: string
  revenue: number
  orders_count: number
}

export interface RevenueByWorkCategoryItem {
  category: string
  category_label: string
  revenue: number
  orders_count: number
}

export interface RevenueByPaymentMethodItem {
  method: string
  method_label: string
  amount: number
  payments_count: number
}

export interface RevenueReportResponse {
  date_from: string
  date_to: string
  total_revenue: number
  total_orders: number
  avg_check: number
  by_day: RevenueByDayItem[]
  by_work_category: RevenueByWorkCategoryItem[]
  by_payment_method: RevenueByPaymentMethodItem[]
}

export interface MechanicReportItem {
  employee_id: number
  full_name: string
  orders_completed: number
  orders_in_progress: number
  revenue: number
  avg_check: number
  works_count: number
  salary_total: number | null
}

export interface MechanicsReportResponse {
  date_from: string
  date_to: string
  mechanics: MechanicReportItem[]
  team_total_revenue: number
  team_total_orders: number
  team_avg_check: number
}

export interface OrderReportItem {
  id: number
  number: string
  status: string
  status_label: string
  created_at: string
  completed_at: string | null
  customer_name: string | null
  vehicle_info: string | null
  mechanic_name: string | null
  total_amount: number
  paid_amount: number
  works_total: number
  parts_total: number
}

export interface OrderStatusBreakdownItem {
  status: string
  status_label: string
  count: number
}

export interface OrdersReportResponse {
  date_from: string
  date_to: string
  total_count: number
  total_amount: number
  total_paid: number
  by_status: OrderStatusBreakdownItem[]
  orders: OrderReportItem[]
}

export interface PartUsageItem {
  part_id: number
  part_name: string
  part_number: string
  category: string
  category_label: string
  total_quantity: number
  total_revenue: number
  total_cost: number
  total_margin: number
  margin_pct: number
  orders_count: number
  current_stock: number
}

export interface PartsReportResponse {
  date_from: string
  date_to: string
  total_parts_revenue: number
  total_quantity_sold: number
  total_parts_cost: number
  total_parts_margin: number
  total_margin_pct: number
  top_parts: PartUsageItem[]
  low_stock_parts: PartUsageItem[]
}
