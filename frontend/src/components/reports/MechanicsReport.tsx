import {
  Box, Paper, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid, alpha,
} from '@mui/material'
import {
  BuildRounded,
  EmojiEventsRounded,
  TrendingUpRounded,
} from '@mui/icons-material'
import { MechanicsReportResponse } from '../../types'
import { BRAND, PALETTE, iconBoxSx, overlineSx } from '../../design-tokens'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

interface Props {
  data: MechanicsReportResponse
}

export default function MechanicsReport({ data }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

      {/* ── Team summary ── */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(BRAND.primary)}><TrendingUpRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Суммарная выручка</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.team_total_revenue)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.green.main)}><BuildRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Заказов (команда)</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.team_total_orders}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.amber.main)}><EmojiEventsRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Средний чек команды</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.team_avg_check)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* ── Mechanics table ── */}
      <Paper elevation={0} sx={{ overflow: 'hidden' }}>
        <Box sx={{ p: 3, pb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
            Показатели по механикам
          </Typography>
        </Box>
        {data.mechanics.length === 0 ? (
          <Box sx={{ px: 3, pb: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет данных за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Механик</TableCell>
                  <TableCell align="center">Завершено</TableCell>
                  <TableCell align="center">В работе</TableCell>
                  <TableCell align="right">Выручка</TableCell>
                  <TableCell align="right">Ср. чек</TableCell>
                  <TableCell align="right">Доля выработки</TableCell>
                  <TableCell align="center">Работ</TableCell>
                  <TableCell align="right">Зарплата</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.mechanics.map((m, idx) => {
                  const sharePct = data.team_total_revenue > 0
                    ? (m.revenue / data.team_total_revenue) * 100
                    : 0
                  return (
                    <TableRow key={m.employee_id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {idx === 0 && (
                            <EmojiEventsRounded fontSize="small" sx={{ color: PALETTE.amber.main }} />
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
                          sx={{ fontWeight: 700, bgcolor: alpha(PALETTE.green.main, 0.1), color: PALETTE.green.main }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={m.orders_in_progress}
                          size="small"
                          sx={{ fontWeight: 700, bgcolor: alpha(PALETTE.amber.main, 0.1), color: PALETTE.amber.main }}
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
                          <Box sx={{ width: 60, height: 5, borderRadius: 3, bgcolor: alpha(BRAND.primary, 0.1), overflow: 'hidden' }}>
                            <Box
                              sx={{
                                width: `${Math.min(sharePct, 100)}%`,
                                height: '100%',
                                background: BRAND.gradient,
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
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{m.works_count}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        {m.salary_total !== null ? (
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>
                            {fmt(m.salary_total)}
                          </Typography>
                        ) : (
                          <Typography variant="caption" color="text.secondary">—</Typography>
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
