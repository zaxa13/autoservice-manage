import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  CircularProgress,
  Alert,
  Grid,
  Chip,
  Switch,
  FormControlLabel,
  Divider,
} from '@mui/material'
import {
  Add as AddIcon,
  Edit as EditIcon,
  Home as HomeIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { Employee, User } from '../types'

interface EmployeePosition {
  value: string
  label: string
}

interface UserRole {
  value: string
  label: string
}

interface EmployeeCreate {
  full_name: string
  position: string
  phone?: string
  email?: string
  hire_date: string
  salary_base: number
  username?: string
  password?: string
  user_role?: string
}

interface EmployeeUpdate {
  full_name?: string
  position?: string
  phone?: string
  email?: string
  salary_base?: number
  is_active?: boolean
}

export default function Employees() {
  const navigate = useNavigate()
  const [employees, setEmployees] = useState<Employee[]>([])
  const [positions, setPositions] = useState<EmployeePosition[]>([])
  const [userRoles, setUserRoles] = useState<UserRole[]>([])
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [openDialog, setOpenDialog] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null)
  const [creatingUser, setCreatingUser] = useState(false)
  
  const isAdmin = currentUser?.role === 'admin'
  
  const [formData, setFormData] = useState<EmployeeCreate>({
    full_name: '',
    position: '',
    phone: '',
    email: '',
    hire_date: new Date().toISOString().split('T')[0],
    salary_base: 0,
    username: '',
    password: '',
    user_role: '',
  })

  useEffect(() => {
    loadCurrentUser()
    loadEmployees()
    loadPositions()
    loadUserRoles()
  }, [])

  const loadCurrentUser = async () => {
    try {
      const response = await api.get('/auth/me')
      setCurrentUser(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки текущего пользователя:', err)
    }
  }

  const loadEmployees = async () => {
    try {
      setLoading(true)
      const response = await api.get('/employees/')
      setEmployees(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки сотрудников')
    } finally {
      setLoading(false)
    }
  }

  const loadPositions = async () => {
    try {
      const response = await api.get('/employees/positions')
      setPositions(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки должностей:', err)
    }
  }

  const loadUserRoles = async () => {
    try {
      const response = await api.get('/employees/user-roles')
      setUserRoles(response.data)
    } catch (err: any) {
      console.error('Ошибка загрузки ролей пользователей:', err)
    }
  }

  const handleOpenDialog = (employee?: Employee) => {
    if (employee) {
      setEditingEmployee(employee)
      setFormData({
        full_name: employee.full_name,
        position: employee.position,
        phone: employee.phone || '',
        email: employee.email || '',
        hire_date: employee.hire_date,
        salary_base: Number(employee.salary_base),
        username: '',
        password: '',
        user_role: '',
      })
      setCreatingUser(false)
    } else {
      setEditingEmployee(null)
      setFormData({
        full_name: '',
        position: '',
        phone: '',
        email: '',
        hire_date: new Date().toISOString().split('T')[0],
        salary_base: 0,
        username: '',
        password: '',
        user_role: '',
      })
      setCreatingUser(false)
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingEmployee(null)
    setError('')
  }

  const handleSave = async () => {
    if (!formData.full_name || !formData.position || !formData.hire_date) {
      setError('Заполните все обязательные поля')
      return
    }

    // Если создается пользователь, проверяем обязательные поля
    if (creatingUser && (!formData.username || !formData.password || !formData.user_role)) {
      setError('Для создания пользователя заполните логин, пароль и роль')
      return
    }

    try {
      setError('')
      setLoading(true)

      if (editingEmployee) {
        const updateData: EmployeeUpdate = {
          full_name: formData.full_name,
          position: formData.position,
          phone: formData.phone || undefined,
          email: formData.email || undefined,
          salary_base: formData.salary_base,
        }
        await api.put(`/employees/${editingEmployee.id}`, updateData)
      } else {
        const createData: EmployeeCreate = {
          ...formData,
          phone: formData.phone || undefined,
          email: formData.email || undefined,
          username: creatingUser ? formData.username : undefined,
          password: creatingUser ? formData.password : undefined,
          user_role: creatingUser ? formData.user_role : undefined,
        }
        await api.post('/employees/', createData)
      }

      handleCloseDialog()
      loadEmployees()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка сохранения сотрудника')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU')
  }

  const getPositionLabel = (value: string) => {
    return positions.find(p => p.value === value)?.label || value
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <IconButton onClick={() => navigate('/')} color="primary">
              <HomeIcon />
            </IconButton>
            <Typography variant="h4" component="h1">
              Сотрудники
            </Typography>
          </Box>
          {isAdmin && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenDialog()}
            >
              Добавить сотрудника
            </Button>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {loading && !employees.length ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ФИО</TableCell>
                  <TableCell>Должность</TableCell>
                  <TableCell>Телефон</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Дата приема</TableCell>
                  <TableCell align="right">Зарплата</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employees.map((employee) => (
                  <TableRow key={employee.id}>
                    <TableCell>{employee.full_name}</TableCell>
                    <TableCell>{getPositionLabel(employee.position)}</TableCell>
                    <TableCell>{employee.phone || '-'}</TableCell>
                    <TableCell>{employee.email || '-'}</TableCell>
                    <TableCell>{formatDate(employee.hire_date)}</TableCell>
                    <TableCell align="right">{formatCurrency(Number(employee.salary_base))}</TableCell>
                    <TableCell>
                      <Chip
                        label={employee.is_active ? 'Активен' : 'Неактивен'}
                        color={employee.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {isAdmin && (
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(employee)}
                        >
                          <EditIcon />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Диалог создания/редактирования */}
        <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
          <DialogTitle>
            {editingEmployee ? 'Редактировать сотрудника' : 'Добавить сотрудника'}
          </DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="ФИО *"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required>
                    <InputLabel>Должность *</InputLabel>
                    <Select
                      value={formData.position}
                      label="Должность *"
                      onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    >
                      {positions.map((position) => (
                        <MenuItem key={position.value} value={position.value}>
                          {position.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Телефон"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Дата приема *"
                    type="date"
                    value={formData.hire_date}
                    onChange={(e) => setFormData({ ...formData, hire_date: e.target.value })}
                    InputLabelProps={{
                      shrink: true,
                    }}
                    required
                    disabled={!!editingEmployee}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Базовая зарплата *"
                    type="number"
                    value={formData.salary_base}
                    onChange={(e) => setFormData({ ...formData, salary_base: Number(e.target.value) || 0 })}
                    required
                    inputProps={{ min: 0, step: 0.01 }}
                  />
                </Grid>

                {!editingEmployee && (
                  <>
                    <Grid item xs={12}>
                      <Divider sx={{ my: 2 }} />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={creatingUser}
                            onChange={(e) => {
                              setCreatingUser(e.target.checked)
                              if (!e.target.checked) {
                                setFormData({
                                  ...formData,
                                  username: '',
                                  password: '',
                                  user_role: '',
                                })
                              }
                            }}
                          />
                        }
                        label="Создать учетную запись пользователя"
                      />
                    </Grid>

                    {creatingUser && (
                      <>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Логин *"
                            value={formData.username}
                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                            required
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <TextField
                            fullWidth
                            label="Пароль *"
                            type="password"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                          />
                        </Grid>
                        <Grid item xs={12}>
                          <FormControl fullWidth required>
                            <InputLabel>Роль пользователя *</InputLabel>
                            <Select
                              value={formData.user_role}
                              label="Роль пользователя *"
                              onChange={(e) => setFormData({ ...formData, user_role: e.target.value })}
                            >
                              {userRoles.map((role) => (
                                <MenuItem key={role.value} value={role.value}>
                                  {role.label}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                      </>
                    )}
                  </>
                )}
              </Grid>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Отмена</Button>
            <Button
              onClick={handleSave}
              variant="contained"
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Сохранить'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  )
}
