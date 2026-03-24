import React, { useEffect } from 'react'
import {
  Box, Typography, Paper, Tabs, Tab, TextField, Button,
  CircularProgress, Alert,
} from '@mui/material'
import {
  TrendingUpRounded,
  BuildRounded,
  AssignmentRounded,
  InventoryRounded,
  RefreshRounded,
  AssessmentRounded,
} from '@mui/icons-material'
import { useReportsStore, ReportTab } from '../store/reportsStore'
import RevenueReport from '../components/reports/RevenueReport'
import MechanicsReport from '../components/reports/MechanicsReport'
import OrdersReport from '../components/reports/OrdersReport'
import PartsReport from '../components/reports/PartsReport'
import { BRAND, PALETTE, SURFACE, iconBoxSx } from '../design-tokens'

const TABS: { value: ReportTab; label: string; icon: React.ReactElement }[] = [
  { value: 'revenue',   label: 'Выручка',       icon: <TrendingUpRounded /> },
  { value: 'mechanics', label: 'Механики',       icon: <BuildRounded /> },
  { value: 'orders',    label: 'Заказ-наряды',   icon: <AssignmentRounded /> },
  { value: 'parts',     label: 'Запчасти',       icon: <InventoryRounded /> },
]

export default function Reports() {
  const {
    dateFrom, dateTo,
    activeTab,
    revenueReport, mechanicsReport, ordersReport, partsReport,
    loading, error,
    setDateFrom, setDateTo, setActiveTab,
    fetchReport,
  } = useReportsStore()

  useEffect(() => {
    fetchReport()
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleTabChange = (_: React.SyntheticEvent, value: ReportTab) => {
    setActiveTab(value)
  }

  const renderReport = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress color="primary" />
        </Box>
      )
    }

    if (error) {
      return <Alert severity="error">{error}</Alert>
    }

    switch (activeTab) {
      case 'revenue':   return revenueReport   ? <RevenueReport   data={revenueReport} />   : null
      case 'mechanics': return mechanicsReport ? <MechanicsReport data={mechanicsReport} /> : null
      case 'orders':    return ordersReport    ? <OrdersReport    data={ordersReport} />    : null
      case 'parts':     return partsReport     ? <PartsReport     data={partsReport} />     : null
      default:          return null
    }
  }

  return (
    <Box>
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 0.5 }}>
          <Box sx={iconBoxSx(BRAND.primary)}>
            <AssessmentRounded />
          </Box>
          <Box>
            <Typography
              variant="overline"
              sx={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.1em', color: PALETTE.stone[500] }}
            >
              Аналитика
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, lineHeight: 1.1 }}>
              Отчёты
            </Typography>
          </Box>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ ml: 7, fontWeight: 500 }}>
          Выручка, механики, заказы и склад за выбранный период
        </Typography>
      </Box>

      {/* ── Date range controls ───────────────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          mb: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          flexWrap: 'wrap',
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.secondary', mr: 1 }}>
          Период:
        </Typography>
        <TextField
          type="date"
          label="С"
          size="small"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          InputLabelProps={{ shrink: true }}
          sx={{ width: 170 }}
        />
        <TextField
          type="date"
          label="По"
          size="small"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }}
          sx={{ width: 170 }}
        />
        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <RefreshRounded />}
          onClick={() => fetchReport()}
          disabled={loading}
        >
          Применить
        </Button>
      </Paper>

      {/* ── Tabs + content ────────────────────────────────────────────────── */}
      <Paper elevation={0} sx={{ overflow: 'hidden' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{
            px: 2,
            pt: 1,
            borderBottom: `1px solid ${PALETTE.stone[200]}`,
          }}
        >
          {TABS.map((tab) => (
            <Tab
              key={tab.value}
              value={tab.value}
              label={tab.label}
              icon={tab.icon}
              iconPosition="start"
            />
          ))}
        </Tabs>

        <Box sx={{ p: 3, bgcolor: SURFACE.muted, minHeight: 300 }}>
          {renderReport()}
        </Box>
      </Paper>
    </Box>
  )
}
