import React, { useState } from 'react'
import {
  Box, Drawer, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, Typography,
  Avatar, IconButton, DialogContent, Stack, Paper,
  Chip, CircularProgress, Button, alpha, TextField,
  InputAdornment, Alert, Fade, Dialog,
} from '@mui/material'
import {
  DashboardRounded, EventNoteRounded, AssignmentRounded,
  InventoryRounded, PeopleAltRounded, AccountBalanceWalletRounded,
  CurrencyRubleRounded, LogoutRounded, EmailRounded,
  AdminPanelSettingsRounded, BadgeRounded, LockRounded,
  Visibility, VisibilityOff, VpnKeyRounded, BalanceRounded,
  LocalShippingRounded, DirectionsCarRounded, AssessmentRounded,
  GarageRounded,
} from '@mui/icons-material'
import { useLocation, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../services/api'
import type { User } from '../types'
import { BRAND, FONT, MOTION, PALETTE, SHADOW, SIDEBAR, SURFACE } from '../design-tokens'

const ROLE_LABELS: Record<string, string> = {
  admin:      'Администратор',
  manager:    'Менеджер',
  mechanic:   'Механик',
  accountant: 'Бухгалтер',
}

const menuItems = [
  { text: 'Дашборд',              icon: <DashboardRounded />,           path: '/' },
  { text: 'Записи',               icon: <EventNoteRounded />,            path: '/appointments' },
  { text: 'Заказ-наряды',         icon: <AssignmentRounded />,           path: '/orders' },
  { text: 'Автомобили',           icon: <DirectionsCarRounded />,        path: '/vehicles' },
  { text: 'Склад',                icon: <InventoryRounded />,            path: '/warehouse' },
  { text: 'Сверка по поставщику', icon: <BalanceRounded />,              path: '/supplier-reconciliation' },
  { text: 'Поставщики',           icon: <LocalShippingRounded />,        path: '/suppliers' },
  { text: 'Сотрудники',           icon: <PeopleAltRounded />,            path: '/employees' },
  { text: 'Зарплата',             icon: <AccountBalanceWalletRounded />, path: '/salary' },
  { text: 'Касса',                icon: <CurrencyRubleRounded />,        path: '/cashflow' },
  { text: 'Отчёты',               icon: <AssessmentRounded />,           path: '/reports' },
] as const

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const { logout } = useAuthStore()

  const [profileData,    setProfileData]    = useState<User | null>(null)
  const [openProfile,    setOpenProfile]    = useState(false)
  const [loadingProfile, setLoadingProfile] = useState(false)

  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [showCurrentPass,    setShowCurrentPass]    = useState(false)
  const [showNewPass,        setShowNewPass]        = useState(false)
  const [passForm,  setPassForm]  = useState({ current_password: '', new_password: '' })
  const [passError, setPassError] = useState('')
  const [passSuccess, setPassSuccess] = useState(false)
  const [passLoading, setPassLoading] = useState(false)

  const handleOpenProfile = async () => {
    setOpenProfile(true)
    setLoadingProfile(true)
    setPassError('')
    setPassSuccess(false)
    setIsChangingPassword(false)
    try {
      const res = await api.get('/auth/me')
      setProfileData(res.data as User)
    } catch {
      // ignore
    } finally {
      setLoadingProfile(false)
    }
  }

  const handlePasswordChange = async () => {
    setPassError('')
    setPassLoading(true)
    try {
      await api.post('/auth/change-password', passForm)
      setPassSuccess(true)
      setIsChangingPassword(false)
      setPassForm({ current_password: '', new_password: '' })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      if (Array.isArray(detail)) {
        setPassError((detail[0] as { msg?: string })?.msg ?? 'Ошибка валидации')
      } else {
        setPassError(typeof detail === 'string' ? detail : 'Не удалось сменить пароль')
      }
    } finally {
      setPassLoading(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: SURFACE.page }}>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <Drawer
        variant="permanent"
        sx={{
          width: SIDEBAR.width,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: SIDEBAR.width,
            boxSizing: 'border-box',
            bgcolor: SIDEBAR.bg,
            borderRight: 'none',
            // subtle right border
            boxShadow: `inset -1px 0 0 ${SIDEBAR.divider}`,
            display: 'flex',
            flexDirection: 'column',
            overflowX: 'hidden',
          },
        }}
      >
        {/* Logo */}
        <Box sx={{ px: 2.5, pt: 3.5, pb: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{
            width: 36, height: 36,
            background: BRAND.gradient,
            borderRadius: '10px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            boxShadow: SHADOW.teal,
          }}>
            <GarageRounded sx={{ color: '#fff', fontSize: 20 }} />
          </Box>
          <Typography sx={{
            fontWeight: 800, color: '#F8FAFC',
            letterSpacing: '0.08em', fontSize: '0.92rem',
            fontFamily: FONT.sans,
          }}>
            AUTO.WORKS
          </Typography>
        </Box>

        {/* Profile button */}
        <Box sx={{ px: 1.5, mb: 1 }}>
          <ListItemButton onClick={handleOpenProfile} sx={{
            p: 1.5, borderRadius: '10px',
            bgcolor: 'rgba(255,255,255,0.05)',
            border: `1px solid ${SIDEBAR.divider}`,
            transition: `all ${MOTION.fast}`,
            '&:hover': { bgcolor: 'rgba(255,255,255,0.09)', borderColor: 'rgba(255,255,255,0.12)' },
          }}>
            <Avatar sx={{
              bgcolor: alpha(BRAND.primary, 0.22),
              color: BRAND.primaryLight,
              width: 32, height: 32,
              fontSize: '0.82rem', fontWeight: 700,
              border: `1px solid ${alpha(BRAND.primaryLight, 0.2)}`,
            }}>
              A
            </Avatar>
            <Box sx={{ ml: 1.5, overflow: 'hidden' }}>
              <Typography sx={{ fontWeight: 700, color: '#F8FAFC', fontSize: '0.8rem', lineHeight: 1.2 }} noWrap>
                Профиль
              </Typography>
              <Typography sx={{ color: SIDEBAR.text, fontSize: '0.7rem' }}>
                Настройки аккаунта
              </Typography>
            </Box>
          </ListItemButton>
        </Box>

        {/* Divider */}
        <Box sx={{ mx: 2, mb: 2, height: '1px', bgcolor: SIDEBAR.divider }} />

        {/* Nav */}
        <List sx={{ flexGrow: 1, px: 1.5, py: 0 }}>
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  component={Link}
                  to={item.path}
                  sx={isActive ? {
                    borderRadius: '8px',
                    bgcolor: SIDEBAR.activeBg,
                    color: '#fff',
                    '& .MuiListItemIcon-root': { color: '#fff' },
                    '&:hover': { bgcolor: SIDEBAR.activeHover },
                    boxShadow: `0 2px 8px ${alpha(BRAND.primary, 0.4)}`,
                  } : {
                    borderRadius: '8px',
                    color: SIDEBAR.text,
                    '& .MuiListItemIcon-root': { color: SIDEBAR.text },
                    transition: `all ${MOTION.fast}`,
                    '&:hover': {
                      bgcolor: SIDEBAR.hoverBg,
                      color: SIDEBAR.textHover,
                      '& .MuiListItemIcon-root': { color: SIDEBAR.textHover },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      fontSize: '0.84rem',
                      fontWeight: isActive ? 700 : 500,
                      letterSpacing: '0.005em',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            )
          })}
        </List>

        {/* Divider + logout */}
        <Box sx={{ mx: 1.5, mb: 1.5, height: '1px', bgcolor: SIDEBAR.divider }} />
        <Box sx={{ px: 1.5, pb: 3 }}>
          <ListItemButton onClick={logout} sx={{
            borderRadius: '8px',
            color: 'rgba(248,113,113,0.65)',
            '& .MuiListItemIcon-root': { color: 'inherit' },
            transition: `all ${MOTION.fast}`,
            '&:hover': {
              bgcolor: 'rgba(239,68,68,0.1)',
              color: '#F87171',
              '& .MuiListItemIcon-root': { color: '#F87171' },
            },
          }}>
            <ListItemIcon sx={{ minWidth: 36 }}><LogoutRounded /></ListItemIcon>
            <ListItemText
              primary="Выйти"
              primaryTypographyProps={{ fontSize: '0.84rem', fontWeight: 500 }}
            />
          </ListItemButton>
        </Box>
      </Drawer>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <Box
        component="main"
        sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, minWidth: 0, animation: 'fadeIn 0.25s ease both' }}
      >
        {children}
      </Box>

      {/* ── Profile dialog ───────────────────────────────────────────────── */}
      <Dialog
        open={openProfile}
        onClose={() => setOpenProfile(false)}
        PaperProps={{ sx: { maxWidth: 400, width: '100%' } }}
      >
        <DialogContent sx={{ p: 0 }}>
          {loadingProfile ? (
            <Box sx={{ p: 6, textAlign: 'center' }}><CircularProgress /></Box>
          ) : profileData && (
            <Box>
              {/* Banner */}
              <Box sx={{
                height: 88,
                background: BRAND.gradientDeep,
                position: 'relative',
              }} />
              <Avatar sx={{
                width: 76, height: 76,
                position: 'absolute',
                top: 50, left: '50%',
                transform: 'translateX(-50%)',
                border: '3px solid #fff',
                bgcolor: PALETTE.teal[900],
                color: BRAND.primaryLight,
                fontSize: '1.7rem', fontWeight: 800,
                boxShadow: SHADOW.md,
              }}>
                {profileData.username.charAt(0).toUpperCase()}
              </Avatar>

              <Box sx={{ pt: 6, pb: 4, px: 3, textAlign: 'center' }}>
                <Typography variant="h5" sx={{ fontWeight: 800 }}>{profileData.username}</Typography>
                <Chip
                  label={ROLE_LABELS[profileData.role]}
                  size="small"
                  color="primary"
                  icon={<AdminPanelSettingsRounded />}
                  sx={{ fontWeight: 700, mt: 1, mb: 3 }}
                />

                {passSuccess && (
                  <Alert severity="success" sx={{ mb: 2, textAlign: 'left' }}>Пароль успешно изменён!</Alert>
                )}

                {!isChangingPassword ? (
                  <Stack spacing={1.5}>
                    {[
                      { icon: <EmailRounded />, label: 'Email',    value: profileData.email },
                      { icon: <BadgeRounded />, label: 'ID',       value: `#${profileData.id}` },
                    ].map((row) => (
                      <Paper key={row.label} variant="outlined" sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 2, bgcolor: SURFACE.muted }}>
                        <Box sx={{ color: 'text.secondary', display: 'flex' }}>{row.icon}</Box>
                        <Box sx={{ textAlign: 'left' }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, display: 'block', lineHeight: 1.2 }}>
                            {row.label}
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>{row.value}</Typography>
                        </Box>
                      </Paper>
                    ))}

                    <Button
                      fullWidth startIcon={<VpnKeyRounded />} variant="text"
                      onClick={() => { setIsChangingPassword(true); setPassSuccess(false) }}
                      sx={{ mt: 1, fontWeight: 700 }}
                    >
                      Сменить пароль
                    </Button>
                  </Stack>
                ) : (
                  <Fade in={isChangingPassword}>
                    <Box sx={{ textAlign: 'left' }}>
                      <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LockRounded color="primary" fontSize="small" /> Обновление пароля
                      </Typography>
                      <Stack spacing={2}>
                        {passError && <Alert severity="error">{passError}</Alert>}

                        {[
                          { label: 'Текущий пароль', show: showCurrentPass, toggle: () => setShowCurrentPass(v => !v), field: 'current_password' as const },
                          { label: 'Новый пароль',   show: showNewPass,     toggle: () => setShowNewPass(v => !v),     field: 'new_password' as const },
                        ].map((f) => (
                          <TextField key={f.field} fullWidth label={f.label}
                            type={f.show ? 'text' : 'password'}
                            value={passForm[f.field]}
                            onChange={(e) => setPassForm(prev => ({ ...prev, [f.field]: e.target.value }))}
                            InputProps={{
                              endAdornment: (
                                <InputAdornment position="end">
                                  <IconButton onClick={f.toggle} size="small">
                                    {f.show ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                                  </IconButton>
                                </InputAdornment>
                              ),
                            }}
                          />
                        ))}

                        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                          <Button fullWidth variant="outlined" onClick={() => setIsChangingPassword(false)}>Отмена</Button>
                          <Button fullWidth variant="contained" onClick={handlePasswordChange}
                            disabled={passLoading || !passForm.new_password}
                          >
                            {passLoading ? <CircularProgress size={20} color="inherit" /> : 'Обновить'}
                          </Button>
                        </Stack>
                      </Stack>
                    </Box>
                  </Fade>
                )}

                {!isChangingPassword && (
                  <Button fullWidth variant="outlined" onClick={() => setOpenProfile(false)} sx={{ mt: 3, fontWeight: 700 }}>
                    Закрыть
                  </Button>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  )
}
