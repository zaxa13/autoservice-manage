import { create } from 'zustand'
import api from '../services/api'
import { User } from '../types'

function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  // При открытии новой вкладки или рефреше восстанавливаем сессию из localStorage
  isAuthenticated: !!getStoredToken(),
  
  login: async (username: string, password: string) => {
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('password', password)
    
    const response = await api.post('/auth/login', params.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    
    if (!response.data?.access_token) {
      throw new Error('Неверный формат ответа от сервера')
    }
    
    localStorage.setItem('access_token', response.data.access_token)
    set({ isAuthenticated: true })
  },
  
  loadUser: async () => {
    // Функция загрузки пользователя - НЕ используется, пользователь не загружается
    // Токены достаточно для аутентификации
    // Если нужно будет загрузить пользователя, можно добавить позже
    throw new Error('loadUser is disabled - user info not needed')
  },
  
  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, isAuthenticated: false })
  },
  
  setUser: (user: User) => set({ user, isAuthenticated: true }),
}))

