import {
  Box, Paper, Typography, Table, TableBody, TableCell,
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
import { BRAND, PALETTE, iconBoxSx, monoSx, overlineSx } from '../../design-tokens'

const fmt = (n: number) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(n)

interface Props {
  data: PartsReportResponse
}

export default function PartsReport({ data }: Props) {
  const marginColor = (pct: number): string =>
    pct >= 20 ? PALETTE.green.main : pct >= 10 ? PALETTE.amber.main : PALETTE.red.main

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

      {/* ── Summary ── */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(BRAND.primary)}><InventoryRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Сумма продаж</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.total_parts_revenue)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.green.main)}><TrendingUpRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Маржа</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {fmt(data.total_parts_margin)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.amber.main)}><PercentRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Маржинальность</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.total_margin_pct}%
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper elevation={0} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={iconBoxSx(PALETTE.blue.main)}><ShoppingCartRounded /></Box>
            <Box>
              <Typography sx={{ ...overlineSx, mb: 0.3 }}>Реализовано (шт.)</Typography>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1.2 }}>
                {data.total_quantity_sold}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* ── Low stock alert ── */}
      {data.low_stock_parts.length > 0 && (
        <Alert severity="warning" icon={<WarningAmberRounded />} sx={{ fontWeight: 600 }}>
          <strong>{data.low_stock_parts.length} позиций</strong> с остатком ниже минимального — требуется пополнение склада
        </Alert>
      )}

      {/* ── Top parts table ── */}
      <Paper elevation={0} sx={{ overflow: 'hidden' }}>
        <Box sx={{ p: 3, pb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
            Топ запчастей по выручке
          </Typography>
        </Box>
        {data.top_parts.length === 0 ? (
          <Box sx={{ px: 3, pb: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Нет данных за выбранный период
            </Typography>
          </Box>
        ) : (
          <TableContainer sx={{ maxHeight: 400 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>Запчасть</TableCell>
                  <TableCell>Артикул</TableCell>
                  <TableCell>Категория</TableCell>
                  <TableCell align="center">Заказов</TableCell>
                  <TableCell align="right">Продано</TableCell>
                  <TableCell align="right">Сумма продаж</TableCell>
                  <TableCell align="right">Маржа</TableCell>
                  <TableCell align="right">Марж. %</TableCell>
                  <TableCell align="right">На складе</TableCell>
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
                      <Typography variant="caption" sx={{ ...monoSx, color: 'text.secondary' }}>
                        {part.part_number}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={part.category_label}
                        size="small"
                        sx={{ fontWeight: 700, bgcolor: alpha(BRAND.primary, 0.08), color: BRAND.primary }}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{part.orders_count}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{part.total_quantity}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 800 }}>{fmt(part.total_revenue)}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 800, color: part.total_margin >= 0 ? PALETTE.green.main : PALETTE.red.main }}
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
                          bgcolor: alpha(marginColor(part.margin_pct), 0.1),
                          color: marginColor(part.margin_pct),
                        }}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 700, color: part.current_stock <= 0 ? PALETTE.red.main : 'text.primary' }}
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

      {/* ── Low stock table ── */}
      {data.low_stock_parts.length > 0 && (
        <Paper
          elevation={0}
          sx={{ border: `1px solid ${alpha(PALETTE.amber.main, 0.35)}`, overflow: 'hidden' }}
        >
          <Box
            sx={{
              p: 3, pb: 1.5,
              display: 'flex', alignItems: 'center', gap: 1,
              bgcolor: alpha(PALETTE.amber.main, 0.05),
            }}
          >
            <WarningAmberRounded sx={{ color: PALETTE.amber.main }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
              Требуют пополнения ({data.low_stock_parts.length})
            </Typography>
          </Box>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Запчасть</TableCell>
                  <TableCell>Артикул</TableCell>
                  <TableCell>Категория</TableCell>
                  <TableCell align="right">Остаток</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.low_stock_parts.map((part) => (
                  <TableRow key={part.part_id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{part.part_name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" sx={{ ...monoSx, color: 'text.secondary' }}>
                        {part.part_number}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={part.category_label} size="small" sx={{ fontWeight: 700 }} />
                    </TableCell>
                    <TableCell align="right">
                      <Chip label={part.current_stock} size="small" color="warning" sx={{ fontWeight: 700 }} />
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
