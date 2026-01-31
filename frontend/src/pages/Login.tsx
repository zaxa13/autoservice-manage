import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container, Paper, TextField, Button, Typography,
  Box, CircularProgress, InputAdornment, Alert, Fade
} from '@mui/material';
import { PersonOutline, LockOutlined, GarageRounded } from '@mui/icons-material';
import { useAuthStore } from '../store/authStore';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login: loginUser, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await loginUser(username, password);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка входа';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        // Современный градиент на фоне
        background: 'radial-gradient(circle at 2% 10%, rgba(79, 70, 229, 0.05) 0%, transparent 50%), radial-gradient(circle at 98% 90%, rgba(16, 185, 129, 0.05) 0%, transparent 50%), #F8FAFC',
      }}
    >
      <Container maxWidth="xs">
        <Fade in={true} timeout={800}>
          <Box>
            {/* Логотип и заголовок */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Box sx={{
                width: 64, height: 64, bgcolor: 'primary.main',
                borderRadius: '20px', display: 'inline-flex',
                alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 8px 16px rgba(79, 70, 229, 0.24)',
                mb: 2
              }}>
                <GarageRounded sx={{ color: '#fff', fontSize: 32 }} />
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary', mb: 1 }}>
                AUTO.WORKS
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Система управления автосервисом
              </Typography>
            </Box>

            <Paper
              elevation={0}
              sx={{
                p: 4,
                borderRadius: '24px',
                border: '1px solid',
                borderColor: 'divider',
                boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)'
              }}
            >
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 700 }}>
                Вход в аккаунт
              </Typography>

              <form onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  label="Имя пользователя"
                  placeholder="admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  margin="normal"
                  required
                  autoComplete="username"
                  // Иконка внутри поля
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <PersonOutline sx={{ color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ mb: 2 }}
                />

                <TextField
                  fullWidth
                  label="Пароль"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  margin="normal"
                  required
                  autoComplete="current-password"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockOutlined sx={{ color: 'text.secondary' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ mb: 3 }}
                />

                {error && (
                  <Alert severity="error" sx={{ mb: 3, borderRadius: '12px' }}>
                    {error}
                  </Alert>
                )}

                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading}
                  sx={{
                    py: 1.5,
                    fontSize: '1rem',
                    borderRadius: '12px',
                  }}
                >
                  {loading ? <CircularProgress size={26} color="inherit" /> : 'Войти в систему'}
                </Button>
              </form>
            </Paper>

            <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 4 }}>
              © {new Date().getFullYear()} AUTO.WORKS CRM. Все права защищены.
            </Typography>
          </Box>
        </Fade>
      </Container>
    </Box>
  );
}