import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'

// Импорт нашей новой темы и лейаута
import { theme } from './theme'
import MainLayout from './components/MainLayout'

// Импорт страниц
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Appointments from './pages/Appointments'
import Orders from './pages/Orders'
import Warehouse from './pages/Warehouse'
import Employees from './pages/Employees'
import Salary from './pages/Salary'

// Импорт стора
import { useAuthStore } from './store/authStore'

/**
 * Компонент защиты роутов.
 * Если пользователь авторизован, оборачивает контент в MainLayout (с боковым меню).
 * Если нет — редиректит на логин.
 */
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const token = localStorage.getItem('access_token')

  if (!token || !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Здесь происходит магия: любая приватная страница оказывается внутри стильного меню
  return <MainLayout>{children}</MainLayout>
}

function AppRoutes() {
  return (
    <Routes>
      {/* Публичный роут */}
      <Route path="/login" element={<Login />} />

      {/* Защищенные роуты */}
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
      <Route
        path="/appointments"
        element={
          <PrivateRoute>
            <Appointments />
          </PrivateRoute>
        }
      />
      <Route
        path="/orders"
        element={
          <PrivateRoute>
            <Orders />
          </PrivateRoute>
        }
      />
      <Route
        path="/warehouse"
        element={
          <PrivateRoute>
            <Warehouse />
          </PrivateRoute>
        }
      />
      <Route
        path="/employees"
        element={
          <PrivateRoute>
            <Employees />
          </PrivateRoute>
        }
      />
      <Route
        path="/salary"
        element={
          <PrivateRoute>
            <Salary />
          </PrivateRoute>
        }
      />

      {/* Редирект со всех несуществующих страниц на главную */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      {/* CssBaseline сбрасывает стандартные стили браузера под настройки темы */}
      <CssBaseline />
      <Router>
        <AppRoutes />
      </Router>
    </ThemeProvider>
  )
}

export default App