import { useState, useEffect } from 'react';
import {
  Container, Typography, Box, Paper, TextField, Button,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  Alert, CircularProgress, Stack, Card, CardContent, alpha
} from '@mui/material';
import {
  AddRounded,
  DeleteOutlineRounded,
  CalendarMonthRounded,
  AccessTimeRounded,
  PersonOutlineRounded,
  PhoneEnabledRounded,
  DescriptionOutlined
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Appointment, AppointmentCreate } from '../types';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

export default function Appointments() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'));
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [openDialog, setOpenDialog] = useState(false);

  const [formData, setFormData] = useState<AppointmentCreate>({
    date: selectedDate,
    time: '09:00',
    customer_name: '',
    customer_phone: '',
    description: '',
  });

  useEffect(() => {
    fetchAppointments();
  }, [selectedDate]);

  const fetchAppointments = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/appointments/', { params: { date: selectedDate } });
      // Сортируем по времени
      const sorted = response.data.sort((a: any, b: any) => a.time.localeCompare(b.time));
      setAppointments(sorted);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки записей');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = () => {
    setFormData({ ...formData, date: selectedDate });
    setOpenDialog(true);
  };

  const handleSave = async () => {
    if (!formData.customer_name || !formData.customer_phone) return;
    setLoading(true);
    try {
      await api.post('/appointments/', formData);
      setOpenDialog(false);
      fetchAppointments();
    } catch (err: any) {
      setError('Ошибка при сохранении');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Удалить эту запись?')) return;
    try {
      await api.delete(`/appointments/${id}`);
      fetchAppointments();
    } catch (err) {
      setError('Ошибка при удалении');
    }
  };

  return (
    <Container maxWidth="md">
      {/* Заголовок и выбор даты */}
      <Box sx={{ mb: 4 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Typography variant="h4">Записи</Typography>
          <Button
            variant="contained"
            startIcon={<AddRounded />}
            onClick={handleOpenDialog}
          >
            Новая запись
          </Button>
        </Stack>

        <Paper sx={{ p: 2, borderRadius: '16px', display: 'flex', alignItems: 'center', gap: 2 }}>
          <CalendarMonthRounded sx={{ color: 'primary.main', ml: 1 }} />
          <TextField
            type="date"
            variant="standard"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            InputProps={{ disableUnderline: true }}
            sx={{
              width: '100%',
              '& input': { fontWeight: 700, fontSize: '1.1rem', cursor: 'pointer' }
            }}
          />
        </Paper>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading && appointments.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 5 }}><CircularProgress /></Box>
      ) : (
        <Stack spacing={2}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 700, letterSpacing: 1 }}>
            {format(new Date(selectedDate), 'd MMMM yyyy', { locale: ru })}
          </Typography>

          {appointments.length === 0 ? (
            <Paper variant="outlined" sx={{ py: 8, textAlign: 'center', bgcolor: 'transparent', borderStyle: 'dashed' }}>
              <Typography color="text.secondary">На этот день записей пока нет</Typography>
            </Paper>
          ) : (
            appointments.map((item) => (
              <Card
                key={item.id}
                elevation={0}
                sx={{
                  borderRadius: '16px',
                  border: '1px solid',
                  borderColor: 'divider',
                  transition: '0.2s',
                  '&:hover': { boxShadow: '0 8px 24px rgba(0,0,0,0.05)', borderColor: 'primary.light' }
                }}
              >
                <CardContent sx={{ p: '16px !important' }}>
                  <Grid container alignItems="center" spacing={2}>
                    {/* Время */}
                    <Grid item xs={12} sm={2}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ color: 'primary.main' }}>
                        <AccessTimeRounded sx={{ fontSize: 20 }} />
                        <Typography variant="h6" sx={{ fontWeight: 800 }}>
                          {item.time.substring(0, 5)}
                        </Typography>
                      </Stack>
                    </Grid>

                    {/* Клиент */}
                    <Grid item xs={12} sm={8}>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                          {item.customer_name}
                        </Typography>
                        <Stack direction="row" spacing={2}>
                          <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <PhoneEnabledRounded sx={{ fontSize: 16 }} /> {item.customer_phone}
                          </Typography>
                          {item.description && (
                            <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <DescriptionOutlined sx={{ fontSize: 16 }} /> {item.description}
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    </Grid>

                    {/* Действия */}
                    <Grid item xs={12} sm={2} sx={{ textAlign: 'right' }}>
                      <IconButton color="error" onClick={() => handleDelete(item.id)} sx={{ bgcolor: alpha('#EF4444', 0.05) }}>
                        <DeleteOutlineRounded />
                      </IconButton>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))
          )}
        </Stack>
      )}

      {/* Модальное окно */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: '24px' } }}>
        <DialogTitle sx={{ fontWeight: 800 }}>Новая запись</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Время"
              type="time"
              value={formData.time}
              onChange={(e) => setFormData({ ...formData, time: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              fullWidth
              label="Имя клиента"
              placeholder="Иван Иванович"
              value={formData.customer_name}
              onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
              InputProps={{ startAdornment: <PersonOutlineRounded sx={{ mr: 1, color: 'text.secondary' }} /> }}
            />
            <TextField
              fullWidth
              label="Телефон"
              placeholder="+7 (999) 000-00-00"
              value={formData.customer_phone}
              onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
              InputProps={{ startAdornment: <PhoneEnabledRounded sx={{ mr: 1, color: 'text.secondary' }} /> }}
            />
            <TextField
              fullWidth
              label="Комментарий"
              multiline
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={() => setOpenDialog(false)} color="secondary">Отмена</Button>
          <Button variant="contained" onClick={handleSave} disabled={loading}>Записать</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

// Вспомогательный Grid (если не импортирован из MUI)
import { Grid } from '@mui/material';