import { create } from 'zustand'
import api from '../services/api'
import { User } from '../types'

function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

/** Декодирует JWT payload без проверки подписи (только клиентская сторона).
 * В shared-DB архитектуре роль приходит в claim `roles: string[]`. */
export function getRoleFromToken(): string | null {
  try {
    const token = getStoredToken()
    if (!token) return null
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    if (Array.isArray(payload?.roles) && payload.roles.length > 0) {
      return payload.roles[0]
    }
    return payload?.role ?? null
  } catch {
    return null
  }
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  // При открытии новой вкладки или рефреше восстанавливаем сессию из localStorage
  isAuthenticated: !!getStoredToken(),

  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })

    if (!response.data?.access_token) {
      throw new Error('Неверный формат ответа от сервера')
    }

    localStorage.setItem('access_token', response.data.access_token)
    set({ isAuthenticated: true })
  },

  loadUser: async () => {
    try {
      const response = await api.get('/auth/me')
      set({ user: response.data })
    } catch {
      // токен протух или недействителен
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, isAuthenticated: false })
  },

  setUser: (user: User) => set({ user, isAuthenticated: true }),
}))
