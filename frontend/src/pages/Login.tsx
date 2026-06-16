import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { TextField, Button, Typography, Box, CircularProgress, InputAdornment, Alert, Link } from '@mui/material'
import { PersonOutline, LockOutlined, GarageRounded } from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { BRAND, FONT, MOTION, PALETTE, SHADOW, SURFACE } from '../design-tokens'

// Abstract SVG — suggests precision instrument / speedometer arc
function BrandDecor() {
  return (
    <svg
      viewBox="0 0 400 400"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.07, pointerEvents: 'none' }}
      aria-hidden
    >
      {/* Outer arc */}
      <circle cx="200" cy="200" r="160" stroke="#2DD4BF" strokeWidth="1" strokeDasharray="6 10" />
      {/* Middle arc */}
      <circle cx="200" cy="200" r="110" stroke="#2DD4BF" strokeWidth="0.75" strokeDasharray="4 14" />
      {/* Inner arc */}
      <circle cx="200" cy="200" r="60"  stroke="#2DD4BF" strokeWidth="0.5" />
      {/* Cross-hairs */}
      <line x1="200" y1="10"  x2="200" y2="390" stroke="#2DD4BF" strokeWidth="0.5" />
      <line x1="10"  y1="200" x2="390" y2="200" stroke="#2DD4BF" strokeWidth="0.5" />
      {/* Diagonal lines */}
      <line x1="40"  y1="40"  x2="360" y2="360" stroke="#2DD4BF" strokeWidth="0.4" strokeDasharray="4 16" />
      <line x1="360" y1="40"  x2="40"  y2="360" stroke="#2DD4BF" strokeWidth="0.4" strokeDasharray="4 16" />
      {/* Center dot */}
      <circle cx="200" cy="200" r="4" fill="#2DD4BF" />
    </svg>
  )
}

export default function Login() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [limitMsg, setLimitMsg] = useState('')
  const [loading, setLoading]   = useState(false)
  const navigate = useNavigate()
  const { login: loginUser, isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLimitMsg('')
    setLoading(true)
    try {
      await loginUser(email, password)
    } catch (err: unknown) {
      const resp = (err as {
        response?: { status?: number; data?: { detail?: unknown } }
      })?.response
      const detail = resp?.data?.detail

      // 409 — превышен лимит одновременных сессий по тарифу: detail — объект.
      if (
        resp?.status === 409 &&
        detail && typeof detail === 'object' &&
        (detail as { code?: string }).code === 'session_limit_reached'
      ) {
        const d = detail as { message?: string; limit?: number }
        setLimitMsg(
          d.message ??
            'Достигнут лимит одновременных сессий по вашему тарифу. ' +
              'Закройте сессию на другом устройстве или перейдите на тариф выше.',
        )
        return
      }

      // Обычные ошибки: detail-строка ("Неверный email или пароль") или fallback.
      const fallback = err instanceof Error ? err.message : 'Ошибка входа'
      setError(typeof detail === 'string' ? detail : fallback)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', bgcolor: '#fff' }}>

      {/* ── Left brand panel ─────────────────────────────────────────────── */}
      <Box sx={{
        display:       { xs: 'none', md: 'flex' },
        flexDirection: 'column',
        justifyContent:'space-between',
        width:         { md: '44%', lg: '42%' },
        bgcolor:       SURFACE.sidebar,
        p:             { md: 5, lg: 7 },
        position:      'relative',
        overflow:      'hidden',
        flexShrink:    0,
      }}>
        {/* Dot grid */}
        <Box sx={{
          position: 'absolute', inset: 0,
          backgroundImage: `radial-gradient(circle, rgba(45,212,191,0.18) 1px, transparent 1px)`,
          backgroundSize: '28px 28px',
          pointerEvents: 'none',
        }} />

        {/* SVG precision graphic */}
        <Box sx={{
          position: 'absolute',
          bottom: '-10%', right: '-10%',
          width: '75%', height: '75%',
          pointerEvents: 'none',
        }}>
          <BrandDecor />
        </Box>

        {/* Bottom vignette */}
        <Box sx={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          height: '50%',
          background: `linear-gradient(to top, ${SURFACE.sidebar} 35%, transparent)`,
          pointerEvents: 'none',
        }} />

        {/* Teal glow top-left */}
        <Box sx={{
          position: 'absolute', top: -100, left: -80,
          width: 340, height: 340, borderRadius: '50%',
          background: `radial-gradient(circle, rgba(13,148,136,0.16) 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />

        {/* Logo + name */}
        <Box sx={{ position: 'relative', zIndex: 1, animation: 'fadeUp 0.5s cubic-bezier(0.16,1,0.3,1) both' }}>
          <Box sx={{
            width: 48, height: 48,
            background: BRAND.gradient,
            borderRadius: '12px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            mb: 3,
            boxShadow: SHADOW.teal,
          }}>
            <GarageRounded sx={{ color: '#fff', fontSize: 26 }} />
          </Box>

          <Typography sx={{
            color: '#F8FAFC',
            fontWeight: 800,
            fontSize: { md: '1.6rem', lg: '1.85rem' },
            letterSpacing: '0.1em',
            fontFamily: FONT.sans,
            lineHeight: 1,
          }}>
            AUTO.WORKS
          </Typography>

          <Typography sx={{ color: 'rgba(248,250,252,0.38)', mt: 1.5, fontSize: '0.85rem', fontWeight: 400, lineHeight: 1.7 }}>
            Система управления<br />автосервисом
          </Typography>
        </Box>

        {/* Bottom tagline */}
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Box sx={{ width: 28, height: 2.5, bgcolor: BRAND.primary, mb: 2.5, borderRadius: '2px' }} />
          <Typography sx={{ color: 'rgba(248,250,252,0.4)', fontSize: '0.78rem', lineHeight: 2, fontWeight: 400 }}>
            Заказы · Склад · Сотрудники<br />
            Касса · Аналитика · Клиенты
          </Typography>
          <Typography sx={{ color: 'rgba(248,250,252,0.18)', fontSize: '0.7rem', mt: 3 }}>
            © {new Date().getFullYear()} AUTO.WORKS CRM
          </Typography>
        </Box>
      </Box>

      {/* ── Right form panel ─────────────────────────────────────────────── */}
      <Box sx={{
        flex: 1,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        bgcolor: '#fff',
        px: { xs: 3, sm: 6, md: 7, lg: 9 },
        py: 6, minHeight: '100vh',
      }}>
        <Box sx={{ width: '100%', maxWidth: 376 }}>

          {/* Mobile logo */}
          <Box sx={{
            display: { xs: 'flex', md: 'none' },
            alignItems: 'center', gap: 1.5, mb: 5,
            animation: 'fadeUp 0.4s cubic-bezier(0.16,1,0.3,1) both',
          }}>
            <Box sx={{
              width: 36, height: 36, background: BRAND.gradient,
              borderRadius: '10px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <GarageRounded sx={{ color: '#fff', fontSize: 20 }} />
            </Box>
            <Typography sx={{ fontWeight: 800, letterSpacing: '0.08em', fontSize: '1rem', color: PALETTE.slate[900] }}>
              AUTO.WORKS
            </Typography>
          </Box>

          {/* Heading */}
          <Box sx={{ animation: 'fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) 0.05s both' }}>
            <Typography variant="h4" sx={{ fontWeight: 800, color: PALETTE.slate[900], mb: 0.75, letterSpacing: '-0.025em' }}>
              С возвращением
            </Typography>
            <Typography variant="body2" sx={{ color: PALETTE.slate[400], mb: 4, fontWeight: 400 }}>
              Войдите в аккаунт, чтобы продолжить
            </Typography>
          </Box>

          <form onSubmit={handleSubmit}>
            {/* Email */}
            <Box sx={{ mb: 2.5, animation: 'fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) 0.1s both' }}>
              <Typography sx={{
                display: 'block', mb: 0.75, fontWeight: 600,
                fontSize: '0.775rem', color: PALETTE.slate[700],
                letterSpacing: '0.02em',
              }}>
                Email
              </Typography>
              <TextField
                fullWidth
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                size="medium"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <PersonOutline sx={{ color: PALETTE.stone[400], fontSize: 20 }} />
                    </InputAdornment>
                  ),
                  sx: { borderRadius: '10px', bgcolor: PALETTE.stone[50] },
                }}
              />
            </Box>

            {/* Password */}
            <Box sx={{ mb: 3.5, animation: 'fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) 0.15s both' }}>
              <Typography sx={{
                display: 'block', mb: 0.75, fontWeight: 600,
                fontSize: '0.775rem', color: PALETTE.slate[700],
                letterSpacing: '0.02em',
              }}>
                Пароль
              </Typography>
              <TextField
                fullWidth
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                size="medium"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockOutlined sx={{ color: PALETTE.stone[400], fontSize: 20 }} />
                    </InputAdornment>
                  ),
                  sx: { borderRadius: '10px', bgcolor: PALETTE.stone[50] },
                }}
              />
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
            )}

            {limitMsg && (
              <Alert severity="warning" sx={{ mb: 3 }}>
                {limitMsg}
                <Box sx={{ mt: 1 }}>
                  <Link
                    href="https://auto-works.pro/cabinet/plan"
                    target="_blank"
                    rel="noopener"
                    underline="hover"
                    sx={{ color: BRAND.primary, fontWeight: 600, fontSize: '0.82rem' }}
                  >
                    Перейти на тариф выше →
                  </Link>
                </Box>
              </Alert>
            )}

            <Box sx={{ animation: 'fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) 0.2s both' }}>
              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  py: 1.5, fontSize: '0.93rem', borderRadius: '10px',
                  fontWeight: 700, letterSpacing: '0.02em',
                  transition: `all ${MOTION.spring}`,
                }}
              >
                {loading
                  ? <CircularProgress size={22} color="inherit" />
                  : 'Войти в систему'
                }
              </Button>
            </Box>
          </form>

          <Typography sx={{
            display: 'block', textAlign: 'center', mt: 3,
            color: PALETTE.slate[500], fontSize: '0.825rem',
            animation: 'fadeUp 0.45s cubic-bezier(0.16,1,0.3,1) 0.25s both',
          }}>
            Забыли пароль?{' '}
            <Link
              href="https://auto-works.pro/login"
              target="_blank"
              rel="noopener"
              underline="hover"
              sx={{
                color: BRAND.primary,
                fontWeight: 600,
                textUnderlineOffset: '3px',
              }}
            >
              Сбросьте в личном кабинете →
            </Link>
          </Typography>

          <Typography sx={{ display: 'block', textAlign: 'center', mt: 5, color: PALETTE.stone[300], fontSize: '0.72rem' }}>
            © {new Date().getFullYear()} AUTO.WORKS CRM. Все права защищены.
          </Typography>
        </Box>
      </Box>
    </Box>
  )
}
