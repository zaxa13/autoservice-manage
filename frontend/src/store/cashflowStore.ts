import { create } from 'zustand'
import type {
  CashAccount,
  CashAccountCreate,
  CashAccountUpdate,
  CashTransaction,
  CashTransactionCreate,
  CashTransactionUpdate,
  CashflowSummary,
  TransactionCategory,
  TransactionCategoryCreate,
  CashTransactionType,
} from '../types'
import {
  getAccounts,
  createAccount,
  updateAccount,
  deleteAccount,
  getCategories,
  createCategory,
  deleteCategory,
  getTransactions,
  createTransaction,
  updateTransaction,
  deleteTransaction,
  getCashflowSummary,
  type TransactionFilters,
} from '../services/api/cashflow'

interface CashflowState {
  accounts: CashAccount[]
  categories: TransactionCategory[]
  transactions: CashTransaction[]
  transactionsTotal: number
  summary: CashflowSummary | null
  loading: boolean
  error: string | null

  fetchAccounts: (includeInactive?: boolean) => Promise<void>
  addAccount: (data: CashAccountCreate) => Promise<void>
  editAccount: (id: number, data: CashAccountUpdate) => Promise<void>
  removeAccount: (id: number) => Promise<void>

  fetchCategories: (type?: CashTransactionType) => Promise<void>
  addCategory: (data: TransactionCategoryCreate) => Promise<void>
  removeCategory: (id: number) => Promise<void>

  fetchTransactions: (filters?: TransactionFilters) => Promise<void>
  addTransaction: (data: CashTransactionCreate) => Promise<CashTransaction>
  editTransaction: (id: number, data: CashTransactionUpdate) => Promise<void>
  removeTransaction: (id: number) => Promise<void>

  fetchSummary: (dateFrom?: string, dateTo?: string) => Promise<void>

  clearError: () => void
}

export const useCashflowStore = create<CashflowState>((set, get) => ({
  accounts: [],
  categories: [],
  transactions: [],
  transactionsTotal: 0,
  summary: null,
  loading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchAccounts: async (includeInactive = false) => {
    set({ loading: true, error: null })
    try {
      const accounts = await getAccounts(includeInactive)
      set({ accounts })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка загрузки счетов'
      set({ error: msg })
    } finally {
      set({ loading: false })
    }
  },

  addAccount: async (data) => {
    set({ loading: true, error: null })
    try {
      const account = await createAccount(data)
      set((s) => ({ accounts: [...s.accounts, account] }))
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка создания счёта'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  editAccount: async (id, data) => {
    set({ loading: true, error: null })
    try {
      const updated = await updateAccount(id, data)
      set((s) => ({ accounts: s.accounts.map((a) => (a.id === id ? updated : a)) }))
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка обновления счёта'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  removeAccount: async (id) => {
    set({ loading: true, error: null })
    try {
      await deleteAccount(id)
      set((s) => ({ accounts: s.accounts.filter((a) => a.id !== id) }))
      await get().fetchSummary()
    } catch (e: unknown) {
      throw e
    } finally {
      set({ loading: false })
    }
  },

  fetchCategories: async (type) => {
    set({ loading: true, error: null })
    try {
      const categories = await getCategories(type)
      set({ categories })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка загрузки категорий'
      set({ error: msg })
    } finally {
      set({ loading: false })
    }
  },

  addCategory: async (data) => {
    set({ loading: true, error: null })
    try {
      const category = await createCategory(data)
      set((s) => ({ categories: [...s.categories, category] }))
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка создания категории'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  removeCategory: async (id) => {
    set({ loading: true, error: null })
    try {
      await deleteCategory(id)
      set((s) => ({ categories: s.categories.filter((c) => c.id !== id) }))
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка удаления категории'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  fetchTransactions: async (filters = {}) => {
    set({ loading: true, error: null })
    try {
      const result = await getTransactions(filters)
      set({ transactions: result.items, transactionsTotal: result.total })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка загрузки операций'
      set({ error: msg })
    } finally {
      set({ loading: false })
    }
  },

  addTransaction: async (data) => {
    set({ loading: true, error: null })
    try {
      const tx = await createTransaction(data)
      set((s) => ({ transactions: [tx, ...s.transactions], transactionsTotal: s.transactionsTotal + 1 }))
      await get().fetchAccounts()
      await get().fetchSummary()
      return tx
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка создания операции'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  editTransaction: async (id, data) => {
    set({ loading: true, error: null })
    try {
      const updated = await updateTransaction(id, data)
      set((s) => ({ transactions: s.transactions.map((t) => (t.id === id ? updated : t)) }))
      await get().fetchAccounts()
      await get().fetchSummary()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка обновления операции'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  removeTransaction: async (id) => {
    set({ loading: true, error: null })
    try {
      await deleteTransaction(id)
      set((s) => ({
        transactions: s.transactions.filter((t) => t.id !== id),
        transactionsTotal: s.transactionsTotal - 1,
      }))
      await get().fetchAccounts()
      await get().fetchSummary()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка удаления операции'
      set({ error: msg })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  fetchSummary: async (dateFrom, dateTo) => {
    set({ loading: true, error: null })
    try {
      const summary = await getCashflowSummary(dateFrom, dateTo)
      set({ summary })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Ошибка загрузки сводки'
      set({ error: msg })
    } finally {
      set({ loading: false })
    }
  },
}))
