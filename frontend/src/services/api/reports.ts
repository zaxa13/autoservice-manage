import api from '../api'
import {
  RevenueReportResponse,
  MechanicsReportResponse,
  OrdersReportResponse,
  PartsReportResponse,
} from '../../types'

export interface ReportDateRange {
  date_from: string
  date_to: string
}

export const reportsApi = {
  getRevenueReport: (params: ReportDateRange): Promise<RevenueReportResponse> =>
    api.get('/reports/revenue', { params }).then((r) => r.data),

  getMechanicsReport: (params: ReportDateRange): Promise<MechanicsReportResponse> =>
    api.get('/reports/mechanics', { params }).then((r) => r.data),

  getOrdersReport: (
    params: ReportDateRange & { status?: string }
  ): Promise<OrdersReportResponse> =>
    api.get('/reports/orders', { params }).then((r) => r.data),

  getPartsReport: (params: ReportDateRange): Promise<PartsReportResponse> =>
    api.get('/reports/parts', { params }).then((r) => r.data),
}
