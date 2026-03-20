import React, { useEffect } from 'react'
import {
  Box, Typography, Paper, Tabs, Tab, TextField, Button,
  CircularProgress, Alert, Divider, alpha,
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

const TABS: { value: ReportTab; label: string; icon: React.ReactElement }[] = [
  { value: 'revenue', label: 'Выручка', icon: <TrendingUpRounded /> },
  { value: 'mechanics', label: 'Механики', icon: <BuildRounded /> },
  { value: 'orders', label: 'Заказ-наряды', icon: <AssignmentRounded /> },
  { value: 'parts', label: 'Запчасти', icon: <InventoryRounded /> },
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

  // Load report on mount and whenever tab/dates change
  useEffect(() => {
    fetchReport()
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleTabChange = (_: React.SyntheticEvent, value: ReportTab) => {
    setActiveTab(value)
  }

  const handleApply = () => {
    fetchReport()
  }

  const renderReport = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      )
    }

    if (error) {
      return (
        <Alert severity="error" sx={{ borderRadius: '12px' }}>
          {error}
        </Alert>
      )
    }

    switch (activeTab) {
      case 'revenue':
        return revenueReport ? (
          <RevenueReport data={revenueReport} />
        ) : null
      case 'mechanics':
        return mechanicsReport ? (
          <MechanicsReport data={mechanicsReport} />
        ) : null
      case 'orders':
        return ordersReport ? (
          <OrdersReport data={ordersReport} />
        ) : null
      case 'parts':
        return partsReport ? (
          <PartsReport data={partsReport} />
        ) : null
      default:
        return null
    }
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '14px',
              bgcolor: alpha('#4F46E5', 0.12),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'primary.main',
            }}
          >
            <AssessmentRounded />
          </Box>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 900 }}>
              Отчёты
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
              Аналитика по периодам — выручка, механики, заказы, склад
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Date range controls */}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          mb: 3,
          border: '1px dashed',
          borderColor: 'divider',
          borderRadius: '16px',
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
          onClick={handleApply}
          disabled={loading}
          sx={{ fontWeight: 700, borderRadius: '10px' }}
        >
          Применить
        </Button>
      </Paper>

      {/* Tabs */}
      <Paper
        elevation={0}
        sx={{ border: '1px dashed', borderColor: 'divider', borderRadius: '16px', overflow: 'hidden' }}
      >
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{
            px: 2,
            pt: 1,
            borderBottom: '1px dashed',
            borderColor: 'divider',
            '& .MuiTab-root': { fontWeight: 700, textTransform: 'none', minHeight: 48 },
            '& .Mui-selected': { color: 'primary.main' },
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

        <Divider sx={{ borderStyle: 'dashed' }} />

        <Box sx={{ p: 3 }}>{renderReport()}</Box>
      </Paper>
    </Box>
  )
}
