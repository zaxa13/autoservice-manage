import {
  Container, Typography, Box, Grid,
  Paper, Button, Stack, alpha
} from '@mui/material';
import {
  AssignmentRounded,
  EventAvailableRounded,
  Inventory2Rounded,
  PeopleAltRounded,
  TrendingUpRounded,
  AddRounded,
  ArrowForwardRounded
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

// Компонент для маленьких карточек статистики (KPI)
function StatCard({ title, value, icon, color }: { title: string, value: string, icon: React.ReactNode, color: string }) {
  return (
    <Paper sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box sx={{
        display: 'flex', p: 1.5, borderRadius: '12px',
        bgcolor: alpha(color, 0.1), color: color
      }}>
        {icon}
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase' }}>
          {title}
        </Typography>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          {value}
        </Typography>
      </Box>
    </Paper>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();

  const mainActions = [
    {
      title: 'Календарь записей',
      desc: 'Планирование визитов клиентов',
      icon: <EventAvailableRounded sx={{ fontSize: 32 }} />,
      path: '/appointments',
      color: '#4F46E5'
    },
    {
      title: 'Заказ-наряды',
      desc: 'Управление активными работами',
      icon: <AssignmentRounded sx={{ fontSize: 32 }} />,
      path: '/orders',
      color: '#10B981'
    },
    {
      title: 'Склад',
      desc: 'Запчасти и расходные материалы',
      icon: <Inventory2Rounded sx={{ fontSize: 32 }} />,
      path: '/warehouse',
      color: '#F59E0B'
    },
    {
      title: 'Сотрудники',
      desc: 'Штат и эффективность мастеров',
      icon: <PeopleAltRounded sx={{ fontSize: 32 }} />,
      path: '/employees',
      color: '#6366F1'
    },
  ];

  return (
    <Container maxWidth="xl">
      {/* Приветствие */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>
            Панель управления
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Сегодня {new Date().toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddRounded />}
          onClick={() => navigate('/orders')} // Быстрое действие
          sx={{ borderRadius: '10px', px: 3 }}
        >
          Новый заказ
        </Button>
      </Box>

      {/* Блок статистики (KPI) */}
      <Grid container spacing={3} sx={{ mb: 5 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Записей на сегодня" value="12" icon={<EventAvailableRounded />} color="#4F46E5" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Машин в боксах" value="8" icon={<TrendingUpRounded />} color="#10B981" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Ожидают оплаты" value="3" icon={<AssignmentRounded />} color="#F59E0B" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Низкий запас (склад)" value="5" icon={<Inventory2Rounded />} color="#EF4444" />
        </Grid>
      </Grid>

      {/* Основная навигация (Карточки разделов) */}
      <Typography variant="h6" sx={{ mb: 3, fontWeight: 700 }}>
        Быстрый доступ
      </Typography>

      <Grid container spacing={3}>
        {mainActions.map((action) => (
          <Grid item xs={12} sm={6} md={3} key={action.title}>
            <Paper
              sx={{
                p: 3,
                height: '100%',
                cursor: 'pointer',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                display: 'flex',
                flexDirection: 'column',
                border: '1px solid',
                borderColor: 'divider',
                '&:hover': {
                  transform: 'translateY(-5px)',
                  boxShadow: '0 12px 20px -5px rgba(0,0,0,0.1)',
                  borderColor: action.color,
                  '& .action-icon': {
                    bgcolor: alpha(action.color, 0.1),
                    color: action.color,
                  },
                  '& .arrow-icon': {
                    transform: 'translateX(5px)',
                    color: action.color,
                  }
                },
              }}
              onClick={() => navigate(action.path)}
            >
              <Box
                className="action-icon"
                sx={{
                  p: 2, borderRadius: '16px', bgcolor: '#F8FAFC',
                  color: 'text.secondary', width: 'fit-content', mb: 2,
                  transition: 'all 0.3s ease'
                }}
              >
                {action.icon}
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                {action.title}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3, flexGrow: 1 }}>
                {action.desc}
              </Typography>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ color: 'text.secondary' }}>
                <Typography variant="button" sx={{ fontSize: '0.75rem' }}>Перейти</Typography>
                <ArrowForwardRounded className="arrow-icon" sx={{ fontSize: 18, transition: 'all 0.3s ease' }} />
              </Stack>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}