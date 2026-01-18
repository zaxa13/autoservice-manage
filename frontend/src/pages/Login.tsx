import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  InputLabel,
} from '@mui/material'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [usernameFilled, setUsernameFilled] = useState(false)
  const [passwordFilled, setPasswordFilled] = useState(false)
  const usernameInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const { login: loginUser, isAuthenticated } = useAuthStore()

  // Если уже авторизован, перенаправляем на главную
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, navigate])

  // Проверка автозаполнения после монтирования компонента
  useEffect(() => {
    // Функция проверки и обновления состояния для автозаполненных полей
    const checkAutofill = () => {
      if (usernameInputRef.current) {
        const inputValue = usernameInputRef.current.value
        // Проверяем, есть ли значение в поле (автозаполнение уже произошло)
        if (inputValue && inputValue.length > 0) {
          setUsernameFilled(true)
          setUsername(inputValue)
        }
      }
      if (passwordInputRef.current) {
        const inputValue = passwordInputRef.current.value
        if (inputValue && inputValue.length > 0) {
          setPasswordFilled(true)
          setPassword(inputValue)
        }
      }
    }

    // Несколько проверок с задержками, так как автозаполнение может произойти с задержкой
    const timeouts = [
      setTimeout(checkAutofill, 100),
      setTimeout(checkAutofill, 300),
      setTimeout(checkAutofill, 500),
      setTimeout(checkAutofill, 1000),
    ]

    // Также проверяем при событии animationstart (браузеры используют анимацию для автозаполнения)
    const handleAnimationStart = (e: AnimationEvent) => {
      if (e.animationName === 'onAutoFillStart' || e.animationName.includes('autofill')) {
        checkAutofill()
      }
    }

    document.addEventListener('animationstart', handleAnimationStart)

    return () => {
      timeouts.forEach(timeout => clearTimeout(timeout))
      document.removeEventListener('animationstart', handleAnimationStart)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      await loginUser(username, password)
      // Навигация произойдет автоматически через useEffect
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка входа'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Автосервис
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Вход в систему
          </Typography>
          
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Имя пользователя"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value)
                setUsernameFilled(e.target.value.length > 0)
              }}
              onFocus={() => setUsernameFilled(true)}
              onBlur={(e) => setUsernameFilled(e.target.value.length > 0)}
              inputRef={usernameInputRef}
              margin="normal"
              required
              autoComplete="username"
              InputLabelProps={{
                shrink: true,
              }}
              sx={{
                '& .MuiInputBase-input:-webkit-autofill': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                  transition: 'background-color 5000s ease-in-out 0s',
                },
                '& .MuiInputBase-input:-webkit-autofill:hover': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                },
                '& .MuiInputBase-input:-webkit-autofill:focus': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                },
                '& .MuiInputBase-input:-webkit-autofill:active': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                },
              }}
            />
            <TextField
              fullWidth
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                setPasswordFilled(e.target.value.length > 0)
              }}
              onFocus={() => setPasswordFilled(true)}
              onBlur={(e) => setPasswordFilled(e.target.value.length > 0)}
              inputRef={passwordInputRef}
              margin="normal"
              required
              autoComplete="current-password"
              InputLabelProps={{
                shrink: true,
              }}
              sx={{
                '& .MuiInputBase-input:-webkit-autofill': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                  transition: 'background-color 5000s ease-in-out 0s',
                },
                '& .MuiInputBase-input:-webkit-autofill:hover': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                },
                '& .MuiInputBase-input:-webkit-autofill:focus': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                },
                '& .MuiInputBase-input:-webkit-autofill:active': {
                  WebkitBoxShadow: '0 0 0 1000px white inset !important',
                  WebkitTextFillColor: 'rgba(0, 0, 0, 0.87) !important',
                },
              }}
            />
            
            {error && (
              <Typography color="error" sx={{ mt: 2 }}>
                {error}
              </Typography>
            )}
            
            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={loading}
              sx={{ mt: 3, mb: 2 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Войти'}
            </Button>
          </form>
        </Paper>
      </Box>
    </Container>
  )
}

