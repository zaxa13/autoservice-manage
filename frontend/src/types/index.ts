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
  status: 'new' | 'estimation' | 'in_progress' | 'ready_for_payment' | 'paid' | 'cancelled'
  total_amount: number
  paid_amount: number
  created_at: string
  completed_at?: string
  vehicle?: Vehicle  // Опциональное для отображения в списке
  mechanic?: Employee  // Опциональное для отображения в списке
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
  category: 'diagnostics' | 'repair' | 'maintenance' | 'body_work' | 'painting' | 'other'
}

export interface Part {
  id: number
  name: string
  part_number?: string
  brand?: string
  price: number
  unit: string
  category: 'engine' | 'transmission' | 'suspension' | 'brakes' | 'electrical' | 'body' | 'consumables' | 'other'
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

export interface Vehicle {
  id: number
  vin?: string
  license_plate?: string
  brand: string
  model: string
  year?: number
  customer_id: number
  customer?: Customer
  created_at?: string
}

export interface VehicleCreate {
  vin?: string
  license_plate?: string
  brand: string
  model: string
  year?: number
  customer_id: number
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

export interface Appointment {
  id: number
  date: string  // YYYY-MM-DD format
  time: string  // HH:MM format
  customer_name: string
  customer_phone: string
  description?: string
  vehicle_id?: number
  employee_id?: number
  created_at: string
  updated_at?: string
  vehicle?: Vehicle
  employee?: Employee
}

export interface AppointmentCreate {
  date: string  // YYYY-MM-DD format
  time: string  // HH:MM format
  customer_name: string
  customer_phone: string
  description?: string
  vehicle_id?: number
  employee_id?: number
}

export interface AppointmentUpdate {
  date?: string
  time?: string
  customer_name?: string
  customer_phone?: string
  description?: string
  vehicle_id?: number
  employee_id?: number
}
