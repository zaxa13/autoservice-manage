import React from 'react';
import {
  Box, Drawer, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, Typography, Divider,
  Avatar, IconButton, Tooltip
} from '@mui/material';
import {
  DashboardRounded,
  EventNoteRounded,
  AssignmentRounded,
  InventoryRounded,
  PeopleAltRounded,
  AccountBalanceWalletRounded,
  LogoutRounded,
  SettingsRounded
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const drawerWidth = 280;

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
  const { logout, user } = useAuthStore();

  const activeStyle = {
    bgcolor: 'primary.main',
    color: 'primary.contrastText',
    '&:hover': { bgcolor: 'primary.dark' },
    '& .MuiListItemIcon-root': { color: 'inherit' },
    borderRadius: '10px',
    mx: 1,
  };

  const normalStyle = {
    borderRadius: '10px',
    mx: 1,
    mb: 0.5,
    color: 'text.secondary',
    '&:hover': { bgcolor: 'rgba(79, 70, 229, 0.08)', color: 'primary.main' },
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: '1px dashed',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        {/* Логотип */}
        <Box sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{
            width: 40, height: 40, bgcolor: 'primary.main',
            borderRadius: '10px', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 10px rgba(79, 70, 229, 0.3)'
          }}>
            <AssignmentRounded sx={{ color: '#fff' }} />
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 800, color: 'text.primary', letterSpacing: -0.5 }}>
            AUTO.WORKS
          </Typography>
        </Box>

        {/* Профиль (мини) */}
        <Box sx={{ px: 2, mb: 3 }}>
          <Box sx={{
            p: 2, bgcolor: 'rgba(241, 245, 249, 0.6)',
            borderRadius: '16px', display: 'flex', alignItems: 'center', gap: 1.5
          }}>
            <Avatar sx={{ bgcolor: 'secondary.main', width: 40, height: 40 }}>
              {user?.username?.charAt(0).toUpperCase() || 'A'}
            </Avatar>
            <Box sx={{ overflow: 'hidden' }}>
              <Typography variant="subtitle2" noWrap sx={{ fontWeight: 700 }}>
                {user?.username || 'Администратор'}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>
                {user?.role === 'admin' ? 'Владелец' : 'Менеджер'}
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* Меню */}
        <List sx={{ flexGrow: 1, px: 1 }}>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => navigate(item.path)}
                sx={location.pathname === item.path ? activeStyle : normalStyle}
              >
                <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{ fontSize: '0.95rem', fontWeight: 600 }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider sx={{ mx: 2, borderStyle: 'dashed' }} />

        {/* Футер меню */}
        <Box sx={{ p: 2 }}>
          <ListItemButton onClick={logout} sx={{ ...normalStyle, color: 'error.main', '&:hover': { bgcolor: 'error.light', color: '#fff' } }}>
            <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
              <LogoutRounded />
            </ListItemIcon>
            <ListItemText primary="Выйти" primaryTypographyProps={{ fontSize: '0.95rem', fontWeight: 600 }} />
          </ListItemButton>
        </Box>
      </Drawer>

      {/* Контент */}
      <Box component="main" sx={{ flexGrow: 1, p: 4, width: { sm: `calc(100% - ${drawerWidth}px)` } }}>
        {children}
      </Box>
    </Box>
  );
}