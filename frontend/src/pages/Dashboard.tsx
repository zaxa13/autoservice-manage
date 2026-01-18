import { Container, Typography, Box, Grid, Paper } from '@mui/material'
import { useNavigate } from 'react-router-dom'

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Панель управления
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Добро пожаловать!
        </Typography>
        
        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={4}>
            <Paper
              sx={{
                p: 3,
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
              onClick={() => navigate('/orders')}
            >
              <Typography variant="h6">Заказ-наряды</Typography>
              <Typography variant="body2" color="text.secondary">
                Управление заказ-нарядами
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={4}>
            <Paper
              sx={{
                p: 3,
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
              onClick={() => navigate('/warehouse')}
            >
              <Typography variant="h6">Склад</Typography>
              <Typography variant="body2" color="text.secondary">
                Управление складом
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={4}>
            <Paper
              sx={{
                p: 3,
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
              onClick={() => navigate('/employees')}
            >
              <Typography variant="h6">Сотрудники</Typography>
              <Typography variant="body2" color="text.secondary">
                Управление сотрудниками
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Container>
  )
}

