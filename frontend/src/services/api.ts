import axios from 'axios'

// Используем относительный путь для работы с Vite прокси
// Vite проксирует /api на http://localhost:8000
// В dev режиме используем относительный путь, в production можно указать полный URL через VITE_API_BASE_URL
// @ts-ignore - Vite добавляет import.meta.env автоматически
const API_BASE_URL = (import.meta.env as any)?.VITE_API_BASE_URL || '/api/v1'

// Публичные эндпоинты, которые не требуют токена
const PUBLIC_ENDPOINTS = ['/auth/login', '/auth/register']

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor для добавления токена
api.interceptors.request.use(
  (config) => {
    // Проверяем, является ли эндпоинт публичным
    const isPublicEndpoint = PUBLIC_ENDPOINTS.some(endpoint => 
      config.url?.includes(endpoint)
    )
    
    // Добавляем токен только для защищенных эндпоинтов
    if (!isPublicEndpoint) {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Возвращаем ошибку для обработки в компонентах
    return Promise.reject(error)
  }
)

export default api
