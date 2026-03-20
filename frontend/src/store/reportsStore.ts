import { create } from 'zustand'
import { format, startOfMonth, endOfMonth } from 'date-fns'
import {
  RevenueReportResponse,
  MechanicsReportResponse,
  OrdersReportResponse,
  PartsReportResponse,
} from '../types'
import { reportsApi } from '../services/api/reports'

export type ReportTab = 'revenue' | 'mechanics' | 'orders' | 'parts'

interface ReportsState {
  // Date range shared across all tabs
  dateFrom: string
  dateTo: string

  // Active tab
  activeTab: ReportTab

  // Data per report type
  revenueReport: RevenueReportResponse | null
  mechanicsReport: MechanicsReportResponse | null
  ordersReport: OrdersReportResponse | null
  partsReport: PartsReportResponse | null

  // Loading / error state
  loading: boolean
  error: string | null

  // Orders report filter
  ordersStatusFilter: string

  // Actions
  setDateFrom: (d: string) => void
  setDateTo: (d: string) => void
  setActiveTab: (tab: ReportTab) => void
  setOrdersStatusFilter: (s: string) => void
  fetchReport: () => Promise<void>
}

const today = new Date()

export const useReportsStore = create<ReportsState>((set, get) => ({
  dateFrom: format(startOfMonth(today), 'yyyy-MM-dd'),
  dateTo: format(endOfMonth(today), 'yyyy-MM-dd'),
  activeTab: 'revenue',
  revenueReport: null,
  mechanicsReport: null,
  ordersReport: null,
  partsReport: null,
  loading: false,
  error: null,
  ordersStatusFilter: '',

  setDateFrom: (d) => set({ dateFrom: d }),
  setDateTo: (d) => set({ dateTo: d }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setOrdersStatusFilter: (s) => set({ ordersStatusFilter: s }),

  fetchReport: async () => {
    const { activeTab, dateFrom, dateTo, ordersStatusFilter } = get()
    set({ loading: true, error: null })
    try {
      const params = { date_from: dateFrom, date_to: dateTo }
      switch (activeTab) {
        case 'revenue': {
          const data = await reportsApi.getRevenueReport(params)
          set({ revenueReport: data })
          break
        }
        case 'mechanics': {
          const data = await reportsApi.getMechanicsReport(params)
          set({ mechanicsReport: data })
          break
        }
        case 'orders': {
          const data = await reportsApi.getOrdersReport({
            ...params,
            ...(ordersStatusFilter ? { status: ordersStatusFilter } : {}),
          })
          set({ ordersReport: data })
          break
        }
        case 'parts': {
          const data = await reportsApi.getPartsReport(params)
          set({ partsReport: data })
          break
        }
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Ошибка загрузки отчёта'
      set({ error: message })
    } finally {
      set({ loading: false })
    }
  },
}))
