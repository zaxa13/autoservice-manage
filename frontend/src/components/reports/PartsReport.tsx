import {
  Box, Paper, Typography, Divider, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid, Alert, alpha,
} from '@mui/material'
import {
  InventoryRounded,
  WarningAmberRounded,
  TrendingUpRounded,
  ShoppingCartRounded,
  PercentRounded,
} from '@mui/icons-material'
import { PartsReportResponse } from '../../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

interface Props {
  data: PartsReportResponse
}

export default function PartsReport({ data }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Summary */}
      <Grid container spacing={2}>
        {/* Общая сумма продаж */}
        <Grid item xs={12} sm={6} md={3}>
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
                width: 48, height: 48, borderRadius: '12px',
                bgcolor: alpha('#4F46E5', 0.12),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#4F46E5', flexShrink: 0,
              }}
            >
              <InventoryRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Общая сумма продаж
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.total_parts_revenue)}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* Выручка (маржа) */}
        <Grid item xs={12} sm={6} md={3}>
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
                width: 48, height: 48, borderRadius: '12px',
                bgcolor: alpha('#10B981', 0.12),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#10B981', flexShrink: 0,
              }}
            >
              <TrendingUpRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Выручка (маржа)
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.total_parts_margin)}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* Маржинальность % */}
        <Grid item xs={12} sm={6} md={3}>
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
                width: 48, height: 48, borderRadius: '12px',
                bgcolor: alpha('#F59E0B', 0.12),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#F59E0B', flexShrink: 0,
              }}
            >
              <PercentRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Маржинальность
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.total_margin_pct}%
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* Реализовано шт */}
        <Grid item xs={12} sm={6} md={3}>
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
                width: 48, height: 48, borderRadius: '12px',
                bgcolor: alpha('#8B5CF6', 0.12),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#8B5CF6', flexShrink: 0,
              }}
            >
              <ShoppingCartRounded />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                Реализовано (шт.)
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.total_quantity_sold}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Low stock alert */}
      {data.low_stock_parts.length > 0 && (
        <Alert
          severity="warning"
          icon={<WarningAmberRounded />}
          sx={{ borderRadius: '12px', fontWeight: 700 }}
        >
          <strong>{data.low_stock_parts.length} позиций</strong> с остатком ниже минимального — требуется пополнение склада
        </Alert>
      )}

      {/* Top parts table */}
      <Paper
        elevation={0}
        sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: '16px', overflow: 'hidden' }}
      >
        <Box sx={{ p: 3, pb: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Топ запчастей по выручке
          </Typography>
        </Box>
        <Divider sx={{ borderStyle: 'dashed' }} />
        {data.top_parts.length === 0 ? (
          <Box sx={{ p: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет данных за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer sx={{ maxHeight: 400 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>#</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Запчасть</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Артикул</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Категория</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 800 }}>Заказов</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>Продано</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>Сумма продаж</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>Маржа</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>Марж. %</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>На складе</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.top_parts.map((part, idx) => (
                  <TableRow key={part.part_id} hover>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                        {idx + 1}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {part.part_name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="caption"
                        sx={{ fontFamily: 'monospace', color: 'text.secondary', fontWeight: 600 }}
                      >
                        {part.part_number}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={part.category_label}
                        size="small"
                        sx={{ fontWeight: 700, bgcolor: alpha('#8B5CF6', 0.1), color: '#8B5CF6' }}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {part.orders_count}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {part.total_quantity}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>
                        {fmt(part.total_revenue)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 800, color: part.total_margin >= 0 ? '#10B981' : '#EF4444' }}
                      >
                        {fmt(part.total_margin)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Chip
                        label={`${part.margin_pct}%`}
                        size="small"
                        sx={{
                          fontWeight: 800,
                          bgcolor: part.margin_pct >= 20
                            ? alpha('#10B981', 0.12)
                            : part.margin_pct >= 10
                              ? alpha('#F59E0B', 0.12)
                              : alpha('#EF4444', 0.12),
                          color: part.margin_pct >= 20
                            ? '#10B981'
                            : part.margin_pct >= 10
                              ? '#F59E0B'
                              : '#EF4444',
                        }}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 700, color: part.current_stock <= 0 ? '#EF4444' : 'text.primary' }}
                      >
                        {part.current_stock}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Low stock table */}
      {data.low_stock_parts.length > 0 && (
        <Paper
          elevation={0}
          sx={{
            border: '1px solid',
            borderColor: alpha('#F59E0B', 0.4),
            borderRadius: '16px',
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              p: 3, pb: 1,
              display: 'flex', alignItems: 'center', gap: 1,
              bgcolor: alpha('#F59E0B', 0.06),
            }}
          >
            <WarningAmberRounded sx={{ color: '#F59E0B' }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
              Требуют пополнения ({data.low_stock_parts.length})
            </Typography>
          </Box>
          <Divider sx={{ borderColor: alpha('#F59E0B', 0.3) }} />
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>Запчасть</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Артикул</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Категория</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 800 }}>Остаток</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.low_stock_parts.map((part) => (
                  <TableRow key={part.part_id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {part.part_name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="caption"
                        sx={{ fontFamily: 'monospace', color: 'text.secondary', fontWeight: 600 }}
                      >
                        {part.part_number}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={part.category_label} size="small" sx={{ fontWeight: 700 }} />
                    </TableCell>
                    <TableCell align="right">
                      <Chip
                        label={part.current_stock}
                        size="small"
                        color="warning"
                        sx={{ fontWeight: 700 }}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  )
}
