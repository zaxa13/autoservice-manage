import api from '../api'
import type {
  CashAccount,
  CashAccountCreate,
  CashAccountUpdate,
  CashTransaction,
  CashTransactionCreate,
  CashTransactionUpdate,
  CashflowListResponse,
  CashflowSummary,
  TransactionCategory,
  TransactionCategoryCreate,
  CashTransactionType,
} from '../../types'

// ── Accounts ──────────────────────────────────────────────────────────────────

export const getAccounts = async (includeInactive = false): Promise<CashAccount[]> => {
  const res = await api.get('/cashflow/accounts', {
    params: { include_inactive: includeInactive },
  })
  return res.data
}

export const getAccount = async (id: number): Promise<CashAccount> => {
  const res = await api.get(`/cashflow/accounts/${id}`)
  return res.data
}

export const createAccount = async (data: CashAccountCreate): Promise<CashAccount> => {
  const res = await api.post('/cashflow/accounts', data)
  return res.data
}

export const updateAccount = async (id: number, data: CashAccountUpdate): Promise<CashAccount> => {
  const res = await api.patch(`/cashflow/accounts/${id}`, data)
  return res.data
}

export const deleteAccount = async (id: number): Promise<void> => {
  await api.delete(`/cashflow/accounts/${id}`)
}

// ── Categories ────────────────────────────────────────────────────────────────

export const getCategories = async (
  transactionType?: CashTransactionType
): Promise<TransactionCategory[]> => {
  const res = await api.get('/cashflow/categories', {
    params: transactionType ? { transaction_type: transactionType } : {},
  })
  return res.data
}

export const createCategory = async (data: TransactionCategoryCreate): Promise<TransactionCategory> => {
  const res = await api.post('/cashflow/categories', data)
  return res.data
}

export const deleteCategory = async (id: number): Promise<void> => {
  await api.delete(`/cashflow/categories/${id}`)
}

// ── Transactions ──────────────────────────────────────────────────────────────

export interface TransactionFilters {
  account_id?: number
  transaction_type?: CashTransactionType
  category_id?: number
  date_from?: string
  date_to?: string
  skip?: number
  limit?: number
}

export const getTransactions = async (filters: TransactionFilters = {}): Promise<CashflowListResponse> => {
  const res = await api.get('/cashflow/transactions', { params: filters })
  return res.data
}

export const getTransaction = async (id: number): Promise<CashTransaction> => {
  const res = await api.get(`/cashflow/transactions/${id}`)
  return res.data
}

export const createTransaction = async (data: CashTransactionCreate): Promise<CashTransaction> => {
  const res = await api.post('/cashflow/transactions', data)
  return res.data
}

export const updateTransaction = async (id: number, data: CashTransactionUpdate): Promise<CashTransaction> => {
  const res = await api.patch(`/cashflow/transactions/${id}`, data)
  return res.data
}

export const deleteTransaction = async (id: number): Promise<void> => {
  await api.delete(`/cashflow/transactions/${id}`)
}

// ── Summary ───────────────────────────────────────────────────────────────────

export const getCashflowSummary = async (dateFrom?: string, dateTo?: string): Promise<CashflowSummary> => {
  const res = await api.get('/cashflow/summary', {
    params: {
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    },
  })
  return res.data
}
