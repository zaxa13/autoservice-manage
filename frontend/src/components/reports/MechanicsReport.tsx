import {
  Box, Paper, Typography, Divider, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid, alpha,
} from '@mui/material'
import {
  BuildRounded,
  EmojiEventsRounded,
  TrendingUpRounded,
} from '@mui/icons-material'
import { MechanicsReportResponse } from '../../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

interface Props {
  data: MechanicsReportResponse
}

export default function MechanicsReport({ data }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Team summary */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              border: '1px dashed',
              borderColor: 'divider',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '12px',
                bgcolor: alpha('#4F46E5', 0.12),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#4F46E5',
                flexShrink: 0,
              }}
            >
              <TrendingUpRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Суммарная выручка
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.team_total_revenue)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              border: '1px dashed',
              borderColor: 'divider',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '12px',
                bgcolor: alpha('#10B981', 0.12),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#10B981',
                flexShrink: 0,
              }}
            >
              <BuildRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Заказов (команда)
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.team_total_orders}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              border: '1px dashed',
              borderColor: 'divider',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '12px',
                bgcolor: alpha('#F59E0B', 0.12),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#F59E0B',
                flexShrink: 0,
              }}
            >
              <EmojiEventsRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Средний чек команды
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.team_avg_check)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Mechanics table */}
      <Paper
        elevation={0}
        sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: '16px', overflow: 'hidden' }}
      >
        <Box sx={{ p: 3, pb: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Показатели по механикам
          </Typography>
        </Box>
        <Divider sx={{ borderStyle: 'dashed' }} />
        {data.mechanics.length === 0 ? (
          <Box sx={{ p: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет данных за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>Механик</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 800 }}>
                    Завершено
                  </TableCell>
                  <TableCell align="center" sx={{ fontWeight: 800 }}>
                    В работе
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Выручка
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Ср. чек
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Доля выработки
                  </TableCell>
                  <TableCell align="center" sx={{ fontWeight: 800 }}>
                    Работ
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    Зарплата
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.mechanics.map((m, idx) => {
                  const sharePct =
                    data.team_total_revenue > 0
                      ? (m.revenue / data.team_total_revenue) * 100
                      : 0
                  return (
                    <TableRow key={m.employee_id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {idx === 0 && (
                            <EmojiEventsRounded fontSize="small" sx={{ color: '#F59E0B' }} />
                          )}
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {m.full_name}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={m.orders_completed}
                          size="small"
                          sx={{ fontWeight: 700, bgcolor: alpha('#10B981', 0.1), color: '#10B981' }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={m.orders_in_progress}
                          size="small"
                          sx={{ fontWeight: 700, bgcolor: alpha('#F59E0B', 0.1), color: '#F59E0B' }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 800 }}>
                          {fmt(m.revenue)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {fmt(m.avg_check)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'flex-end' }}>
                          <Box
                            sx={{
                              width: 60, height: 6, borderRadius: 3,
                              bgcolor: alpha('#4F46E5', 0.12), overflow: 'hidden',
                            }}
                          >
                            <Box
                              sx={{
                                width: `${Math.min(sharePct, 100)}%`,
                                height: '100%',
                                bgcolor: '#4F46E5',
                                borderRadius: 3,
                              }}
                            />
                          </Box>
                          <Typography variant="body2" sx={{ fontWeight: 800, minWidth: 40, textAlign: 'right' }}>
                            {sharePct.toFixed(1)}%
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {m.works_count}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {m.salary_total !== null ? (
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {fmt(m.salary_total)}
                          </Typography>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            Нет данных
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  )
}
