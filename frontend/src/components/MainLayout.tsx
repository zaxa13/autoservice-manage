import React, { useState, useEffect } from 'react';
import {
  Box, Drawer, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, Typography, Divider,
  Avatar, IconButton, Tooltip, Dialog, DialogTitle,
  DialogContent, Stack, Paper, Chip, CircularProgress,
  Button, alpha, TextField, InputAdornment, Alert, Fade
} from '@mui/material';
import {
  DashboardRounded,
  EventNoteRounded,
  AssignmentRounded,
  InventoryRounded,
  PeopleAltRounded,
  AccountBalanceWalletRounded,
  LogoutRounded,
  EmailRounded,
  AdminPanelSettingsRounded,
  CalendarTodayRounded,
  BadgeRounded,
  LockRounded,
  Visibility,
  VisibilityOff,
  VpnKeyRounded
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';
import { User } from '../types';

const drawerWidth = 280;

const ROLE_LABELS: Record<string, string> = {
  admin: 'Администратор',
  manager: 'Менеджер',
  mechanic: 'Механик',
  accountant: 'Бухгалтер'
};

const menuItems = [
  { text: 'Дашборд', icon: <DashboardRounded />, path: '/' },
  { text: 'Записи', icon: <EventNoteRounded />, path: '/appointments' },
  { text: 'Заказ-наряды', icon: <AssignmentRounded />, path: '/orders' },
  { text: 'Склад', icon: <InventoryRounded />, path: '/warehouse' },
  { text: 'Сотрудники', icon: <PeopleAltRounded />, path: '/employees' },
  { text: 'Зарплата', icon: <AccountBalanceWalletRounded />, path: '/salary' },
];

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuthStore();

  // Состояния профиля
  const [profileData, setProfileData] = useState<User | null>(null);
  const [openProfile, setOpenProfile] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Состояния смены пароля
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [showCurrentPass, setShowCurrentPass] = useState(false);
  const [showNewPass, setShowNewPass] = useState(false);
  const [passForm, setPassForm] = useState({ current_password: '', new_password: '' });
  const [passError, setPassError] = useState('');
  const [passSuccess, setPassSuccess] = useState(false);
  const [passLoading, setPassLoading] = useState(false);

  const handleOpenProfile = async () => {
    setOpenProfile(true);
    setLoadingProfile(true);
    setPassError('');
    setPassSuccess(false);
    setIsChangingPassword(false);
    try {
      const res = await api.get('/auth/me');
      setProfileData(res.data);
    } catch (e) {
      console.error("Ошибка загрузки профиля");
    } finally {
      setLoadingProfile(false);
    }
  };

  const handlePasswordChange = async () => {
    setPassError('');
    setPassLoading(true);
    try {
      await api.post('/auth/change-password', passForm);
      setPassSuccess(true);
      setIsChangingPassword(false);
      setPassForm({ current_password: '', new_password: '' });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      // Обработка формата detail: [{ msg: "..." }] или просто строки
      if (Array.isArray(detail)) {
        setPassError(detail[0]?.msg || 'Ошибка валидации');
      } else {
        setPassError(detail || 'Не удалось сменить пароль');
      }
    } finally {
      setPassLoading(false);
    }
  };

  const activeStyle = {
    bgcolor: 'primary.main', color: 'primary.contrastText',
    '&:hover': { bgcolor: 'primary.dark' },
    '& .MuiListItemIcon-root': { color: 'inherit' },
    borderRadius: '12px', mx: 1.5, mb: 0.5,
  };

  const normalStyle = {
    borderRadius: '12px', mx: 1.5, mb: 0.5,
    color: 'text.secondary',
    '&:hover': { bgcolor: alpha('#4F46E5', 0.08), color: 'primary.main' },
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box', borderRight: '1px dashed #E2E8F0', bgcolor: 'background.paper' },
        }}
      >
        {/* Логотип */}
        <Box sx={{ p: 3, mb: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ width: 42, height: 42, bgcolor: 'primary.main', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(79, 70, 229, 0.3)' }}>
            <AssignmentRounded sx={{ color: '#fff' }} />
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 900, color: 'text.primary', letterSpacing: -0.5 }}>AUTO.WORKS</Typography>
        </Box>

        {/* Мини-профиль в сайдбаре */}
        <Box sx={{ px: 2, mb: 3 }}>
          <ListItemButton onClick={handleOpenProfile} sx={{ p: 2, bgcolor: alpha('#F1F5F9', 0.6), borderRadius: '16px', border: '1px solid transparent', '&:hover': { bgcolor: '#F1F5F9', borderColor: 'primary.light' } }}>
            <Avatar sx={{ bgcolor: 'primary.main', width: 42, height: 42, fontWeight: 700 }}>A</Avatar>
            <Box sx={{ ml: 2, overflow: 'hidden' }}>
              <Typography variant="subtitle2" noWrap sx={{ fontWeight: 800 }}>Профиль</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>Настройки аккаунта</Typography>
            </Box>
          </ListItemButton>
        </Box>

        {/* Меню */}
        <List sx={{ flexGrow: 1, px: 0 }}>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton onClick={() => navigate(item.path)} sx={location.pathname === item.path ? activeStyle : normalStyle}>
                <ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: 700 }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider sx={{ mx: 3, my: 2, borderStyle: 'dashed' }} />
        <Box sx={{ p: 2 }}>
          <ListItemButton onClick={logout} sx={{ ...normalStyle, color: 'error.main', '&:hover': { bgcolor: alpha('#EF4444', 0.1) } }}>
            <ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}><LogoutRounded /></ListItemIcon>
            <ListItemText primary="Выйти" primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: 700 }} />
          </ListItemButton>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 } }}>{children}</Box>

      {/* ДИАЛОГ ПРОФИЛЯ + СМЕНА ПАРОЛЯ */}
      <Dialog open={openProfile} onClose={() => setOpenProfile(false)} PaperProps={{ sx: { borderRadius: '24px', width: '100%', maxWidth: 420 } }}>
        <DialogContent sx={{ p: 0 }}>
          {loadingProfile ? (
            <Box sx={{ p: 6, textAlign: 'center' }}><CircularProgress /></Box>
          ) : profileData && (
            <Box>
              <Box sx={{ height: 100, background: 'linear-gradient(135deg, #4F46E5 0%, #3730A3 100%)', position: 'relative' }}>
                <Avatar sx={{ width: 80, height: 80, position: 'absolute', bottom: -40, left: '50%', transform: 'translateX(-50%)', border: '4px solid #fff', bgcolor: 'secondary.main', fontSize: '1.8rem', fontWeight: 800, boxShadow: '0 8px 16px rgba(0,0,0,0.1)' }}>
                  {profileData.username.charAt(0).toUpperCase()}
                </Avatar>
              </Box>

              <Box sx={{ pt: 6, pb: 4, px: 3, textAlign: 'center' }}>
                <Typography variant="h5" sx={{ fontWeight: 900 }}>{profileData.username}</Typography>
                <Chip label={ROLE_LABELS[profileData.role]} size="small" color="primary" icon={<AdminPanelSettingsRounded />} sx={{ fontWeight: 800, borderRadius: '8px', mt: 1, mb: 3 }} />

                {passSuccess && <Alert severity="success" sx={{ mb: 2, borderRadius: '12px', textAlign: 'left' }}>Пароль успешно изменен!</Alert>}

                {!isChangingPassword ? (
                  <Stack spacing={1.5}>
                    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: '12px', display: 'flex', alignItems: 'center', gap: 2, borderStyle: 'dashed' }}>
                      <EmailRounded fontSize="small" color="action" />
                      <Box sx={{ textAlign: 'left' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>Email</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{profileData.email}</Typography>
                      </Box>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: '12px', display: 'flex', alignItems: 'center', gap: 2, borderStyle: 'dashed' }}>
                      <BadgeRounded fontSize="small" color="action" />
                      <Box sx={{ textAlign: 'left' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>ID</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>#{profileData.id}</Typography>
                      </Box>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: '12px', display: 'flex', alignItems: 'center', gap: 2, borderStyle: 'dashed' }}>
                      <CalendarTodayRounded fontSize="small" color="action" />
                      <Box sx={{ textAlign: 'left' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>В системе с</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{new Date(profileData.created_at).toLocaleDateString('ru-RU')}</Typography>
                      </Box>
                    </Paper>

                    <Button
                      fullWidth
                      startIcon={<VpnKeyRounded />}
                      variant="text"
                      onClick={() => { setIsChangingPassword(true); setPassSuccess(false); }}
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
                        {passError && <Alert severity="error" sx={{ borderRadius: '12px' }}>{passError}</Alert>}

                        <TextField
                          fullWidth
                          label="Текущий пароль"
                          type={showCurrentPass ? 'text' : 'password'}
                          value={passForm.current_password}
                          onChange={(e) => setPassForm({ ...passForm, current_password: e.target.value })}
                          InputProps={{
                            endAdornment: (
                              <InputAdornment position="end">
                                <IconButton onClick={() => setShowCurrentPass(!showCurrentPass)} size="small">
                                  {showCurrentPass ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                                </IconButton>
                              </InputAdornment>
                            ),
                          }}
                        />

                        <TextField
                          fullWidth
                          label="Новый пароль"
                          type={showNewPass ? 'text' : 'password'}
                          value={passForm.new_password}
                          onChange={(e) => setPassForm({ ...passForm, new_password: e.target.value })}
                          InputProps={{
                            endAdornment: (
                              <InputAdornment position="end">
                                <IconButton onClick={() => setShowNewPass(!showNewPass)} size="small">
                                  {showNewPass ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                                </IconButton>
                              </InputAdornment>
                            ),
                          }}
                        />

                        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                          <Button fullWidth variant="outlined" color="inherit" onClick={() => setIsChangingPassword(false)}>Отмена</Button>
                          <Button
                            fullWidth
                            variant="contained"
                            onClick={handlePasswordChange}
                            disabled={passLoading || !passForm.new_password}
                          >
                            {passLoading ? <CircularProgress size={24} /> : 'Обновить'}
                          </Button>
                        </Stack>
                      </Stack>
                    </Box>
                  </Fade>
                )}

                {!isChangingPassword && (
                  <Button fullWidth variant="outlined" color="inherit" onClick={() => setOpenProfile(false)} sx={{ mt: 3, borderRadius: '12px', fontWeight: 800 }}>Закрыть</Button>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
}