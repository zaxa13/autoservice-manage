import { useState, useEffect, useCallback } from 'react'
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Stack,
  Card,
  CardContent,
  alpha,
  Grid,
} from '@mui/material'
import {
  AddRounded,
  DeleteOutlineRounded,
  CalendarMonthRounded,
  AccessTimeRounded,
  PersonOutlineRounded,
  PhoneEnabledRounded,
  DescriptionOutlined,
  AddCircleOutlineRounded,
  EditRounded,
  DeleteRounded,
} from '@mui/icons-material'
import {
  DndContext,
  DragOverlay,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import api from '../services/api'
import {
  Appointment,
  AppointmentCreate,
  AppointmentPost,
  AppointmentPostCreate,
} from '../types'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

const POST_COLORS = [
  '#6366F1', // indigo
  '#22C55E', // green
  '#F59E0B', // amber
  '#EC4899', // pink
  '#14B8A6', // teal
  '#8B5CF6', // violet
]

const DEFAULT_SLOT_HOURS = '9, 11, 13, 15, 17'

/** "9, 11, 13, 15, 17" -> ["09:00", "11:00", "13:00", "15:00", "17:00"] */
function parseSlotTimes(input: string): string[] {
  return input
    .split(/[,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((h) => {
      const n = parseInt(h, 10)
      if (Number.isNaN(n) || n < 0 || n > 23) return null
      return `${String(n).padStart(2, '0')}:00`
    })
    .filter((t): t is string => t !== null)
}

/** ["09:00", "11:00"] -> "9, 11" для поля ввода */
function formatSlotTimesForInput(slotTimes: string[] | undefined): string {
  if (!slotTimes?.length) return ''
  return slotTimes
    .map((t) => {
      const h = t.substring(0, 2)
      const n = parseInt(h, 10)
      return Number.isNaN(n) ? t : String(n)
    })
    .join(', ')
}

function getPostColor(post: AppointmentPost, index: number): string {
  return post.color || POST_COLORS[index % POST_COLORS.length]
}

/** Нормализуем время к HH:MM для сравнения */
function timeToHHMM(t: string | undefined): string {
  if (!t) return ''
  const s = t.toString().trim()
  if (s.length >= 5) return s.substring(0, 5)
  return s
}

// Карточка записи (для списка и для drag overlay)
function AppointmentCard({
  item,
  onDelete,
  color,
  isDragging,
}: {
  item: Appointment
  onDelete: (id: number) => void
  color: string
  isDragging?: boolean
}) {
  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: `4px solid ${color}`,
        opacity: isDragging ? 0.6 : 1,
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 2 },
      }}
    >
      <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color }}>
              {item.time?.toString().substring(0, 5)}
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {item.customer_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {item.customer_phone}
              {item.description ? ` · ${item.description}` : ''}
            </Typography>
          </Box>
          <IconButton
            size="small"
            color="error"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(item.id)
            }}
            sx={{ mt: -0.5, mr: -0.5 }}
          >
            <DeleteOutlineRounded fontSize="small" />
          </IconButton>
        </Stack>
      </CardContent>
    </Card>
  )
}

// Draggable обёртка для карточки
function DraggableCard({
  item,
  postColor,
  onDelete,
}: {
  item: Appointment
  postColor: string
  onDelete: (id: number) => void
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `appointment-${item.id}`,
    data: { appointment: item },
  })
  return (
    <Box ref={setNodeRef} {...listeners} {...attributes} sx={{ mb: 1 }}>
      <AppointmentCard item={item} onDelete={onDelete} color={postColor} isDragging={isDragging} />
    </Box>
  )
}

// Ячейка-слот: при drop запись получает время этого слота и отображается в этой ячейке
function SlotCell({
  postId,
  slotTime,
  postColor,
  children,
}: {
  postId: number
  slotTime: string
  postColor: string
  children: React.ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `slot-${postId}-${slotTime}`,
    data: { postId, slotTime },
  })
  return (
    <Box
      ref={setNodeRef}
      sx={{
        mb: 1.5,
        minHeight: 52,
        borderRadius: 1,
        border: '2px dashed',
        borderColor: isOver ? postColor : 'transparent',
        bgcolor: isOver ? alpha(postColor, 0.08) : 'transparent',
        transition: 'border-color 0.2s, background-color 0.2s',
        p: 0.5,
      }}
    >
      {children}
    </Box>
  )
}

// Колонка поста: при наличии слотов каждый слот — отдельная droppable-ячейка
function PostColumn({
  post,
  appointments,
  postColor,
  onAddRecord,
  onAddRecordForSlot,
  onEditPost,
  onDeletePost,
  onDelete,
}: {
  post: AppointmentPost
  appointments: Appointment[]
  postColor: string
  onAddRecord: () => void
  onAddRecordForSlot?: (slotTime: string) => void
  onEditPost?: (post: AppointmentPost) => void
  onDeletePost?: (post: AppointmentPost) => void
  onDelete: (id: number) => void
}) {
  const slotTimes = post.slot_times && post.slot_times.length > 0 ? post.slot_times : null
  const canAdd = appointments.length < post.max_slots
  const canEditDelete = post.id > 0
  const hasSlotDroppables = Boolean(slotTimes && post.id > 0)
  const { setNodeRef, isOver } = useDroppable({
    id: `post-${post.id}`,
    data: hasSlotDroppables ? undefined : { postId: post.id },
  })

  return (
    <Paper
      ref={hasSlotDroppables ? undefined : setNodeRef}
      variant="outlined"
      sx={{
        minWidth: 280,
        maxWidth: 280,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 2,
        overflow: 'hidden',
        borderWidth: 2,
        borderColor: !hasSlotDroppables && isOver ? postColor : 'divider',
        bgcolor: !hasSlotDroppables && isOver ? alpha(postColor, 0.06) : 'background.paper',
        transition: 'border-color 0.2s, background-color 0.2s',
      }}
    >
      <Box
        sx={{
          py: 1.5,
          px: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: alpha(postColor, 0.12),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 0.5,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            {post.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {appointments.length} / {post.max_slots}
          </Typography>
        </Box>
        {canEditDelete && (
          <Stack direction="row" spacing={0}>
            <IconButton size="small" onClick={() => onEditPost?.(post)} title="Редактировать пост">
              <EditRounded fontSize="small" />
            </IconButton>
            <IconButton size="small" color="error" onClick={() => onDeletePost?.(post)} title="Удалить пост">
              <DeleteRounded fontSize="small" />
            </IconButton>
          </Stack>
        )}
      </Box>
      <Box sx={{ p: 1.5, flex: 1, minHeight: 120 }}>
        {slotTimes ? (
          <>
            {slotTimes.map((slotTime) => {
              const appointmentAtSlot = appointments.find(
                (a) => timeToHHMM(a.time) === slotTime
              )
              return (
                <SlotCell key={slotTime} postId={post.id} slotTime={slotTime} postColor={postColor}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontWeight: 600 }}>
                    {slotTime}
                  </Typography>
                  {appointmentAtSlot ? (
                    <DraggableCard
                      item={appointmentAtSlot}
                      postColor={postColor}
                      onDelete={onDelete}
                    />
                  ) : post.id > 0 && onAddRecordForSlot ? (
                    <Button
                      fullWidth
                      size="small"
                      startIcon={<AddCircleOutlineRounded />}
                      onClick={() => onAddRecordForSlot(slotTime)}
                      sx={{ borderStyle: 'dashed', justifyContent: 'flex-start' }}
                      variant="outlined"
                    >
                      Добавить запись
                    </Button>
                  ) : null}
                </SlotCell>
              )
            })}
            {/* Записи, не попавшие ни в один слот (например после перетаскивания с другого поста) */}
            {(() => {
              const matchedIds = new Set(
                slotTimes
                  .map((slotTime) =>
                    appointments.find((a) => timeToHHMM(a.time) === slotTime)?.id
                  )
                  .filter((id): id is number => id != null)
              )
              const unmatched = appointments.filter((a) => !matchedIds.has(a.id))
              if (unmatched.length === 0) return null
              return (
                <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px dashed', borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                    Другие записи
                  </Typography>
                  {unmatched.map((item) => (
                    <DraggableCard
                      key={item.id}
                      item={item}
                      postColor={postColor}
                      onDelete={onDelete}
                    />
                  ))}
                </Box>
              )
            })()}
          </>
        ) : (
          <>
            {appointments.map((item) => (
              <DraggableCard
                key={item.id}
                item={item}
                postColor={postColor}
                onDelete={onDelete}
              />
            ))}
            {canAdd && post.id > 0 && (
              <Button
                fullWidth
                size="small"
                startIcon={<AddCircleOutlineRounded />}
                onClick={onAddRecord}
                sx={{ mt: 1, borderStyle: 'dashed' }}
                variant="outlined"
              >
                Добавить запись
              </Button>
            )}
          </>
        )}
      </Box>
    </Paper>
  )
}

export default function Appointments() {
  const [selectedDate, setSelectedDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'))
  const [posts, setPosts] = useState<AppointmentPost[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [openRecordDialog, setOpenRecordDialog] = useState(false)
  const [openPostDialog, setOpenPostDialog] = useState(false)
  const [activeAppointment, setActiveAppointment] = useState<Appointment | null>(null)

  const [recordForm, setRecordForm] = useState<AppointmentCreate>({
    date: selectedDate,
    time: '09:00',
    customer_name: '',
    customer_phone: '',
    description: '',
  })
  const [selectedPostIdForNew, setSelectedPostIdForNew] = useState<number | null>(null)

  const [postForm, setPostForm] = useState<AppointmentPostCreate>({
    name: 'Пост 1',
    max_slots: 5,
    sort_order: 0,
  })
  const [postFormSlotTimesInput, setPostFormSlotTimesInput] = useState(DEFAULT_SLOT_HOURS)
  const [editingPostId, setEditingPostId] = useState<number | null>(null)
  const [deletePostConfirm, setDeletePostConfirm] = useState<AppointmentPost | null>(null)
  const [deletingPost, setDeletingPost] = useState(false)
  const [savingPost, setSavingPost] = useState(false)
  const [savingRecord, setSavingRecord] = useState(false)

  const fetchPosts = useCallback(async () => {
    try {
      const res = await api.get<AppointmentPost[]>('/appointment-posts/')
      setPosts(res.data)
    } catch {
      setError('Не удалось загрузить посты')
    }
  }, [])

  const fetchAppointments = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get<Appointment[]>('/appointments/', {
        params: { date: selectedDate },
      })
      setAppointments(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки записей')
    } finally {
      setLoading(false)
    }
  }, [selectedDate])

  useEffect(() => {
    fetchPosts()
  }, [fetchPosts])

  useEffect(() => {
    fetchAppointments()
  }, [fetchAppointments])

  const appointmentsByPost = (postId: number | null) =>
    appointments
      .filter((a) => (a.post_id ?? null) === postId)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

  const handleOpenEditPost = (post: AppointmentPost) => {
    setEditingPostId(post.id)
    setPostForm({
      name: post.name,
      max_slots: post.max_slots,
      sort_order: post.sort_order,
    })
    setPostFormSlotTimesInput(formatSlotTimesForInput(post.slot_times ?? []))
    setOpenPostDialog(true)
  }

  const handleSavePost = async () => {
    if (!postForm.name.trim()) return
    setSavingPost(true)
    try {
      const slot_times = parseSlotTimes(postFormSlotTimesInput)
      const payload = {
        ...postForm,
        slot_times: slot_times.length > 0 ? slot_times : undefined,
      }
      if (editingPostId !== null) {
        await api.put(`/appointment-posts/${editingPostId}`, payload)
      } else {
        await api.post('/appointment-posts/', { ...payload, sort_order: posts.length })
      }
      await fetchPosts()
      setOpenPostDialog(false)
      setEditingPostId(null)
      setPostForm({ name: `Пост ${posts.length + 1}`, max_slots: 5, sort_order: posts.length })
      setPostFormSlotTimesInput(DEFAULT_SLOT_HOURS)
    } catch {
      setError(editingPostId !== null ? 'Ошибка сохранения поста' : 'Ошибка создания поста')
    } finally {
      setSavingPost(false)
    }
  }

  const handleDeletePostConfirm = async () => {
    if (!deletePostConfirm) return
    setDeletingPost(true)
    try {
      await api.delete(`/appointment-posts/${deletePostConfirm.id}`)
      setDeletePostConfirm(null)
      await fetchPosts()
    } catch {
      setError('Ошибка удаления поста')
    } finally {
      setDeletingPost(false)
    }
  }

  const handleOpenAddRecord = (postId: number) => {
    setSelectedPostIdForNew(postId)
    setRecordForm({
      date: selectedDate,
      time: '09:00',
      customer_name: '',
      customer_phone: '',
      description: '',
      post_id: postId,
      sort_order: appointmentsByPost(postId).length,
    })
    setOpenRecordDialog(true)
  }

  const handleOpenAddRecordForSlot = (postId: number, slotTime: string) => {
    setSelectedPostIdForNew(postId)
    const post = posts.find((p) => p.id === postId)
    const slotIndex = post?.slot_times?.indexOf(slotTime) ?? 0
    setRecordForm({
      date: selectedDate,
      time: slotTime.length === 5 ? slotTime : `${slotTime.padStart(2, '0')}:00`,
      customer_name: '',
      customer_phone: '',
      description: '',
      post_id: postId,
      sort_order: slotIndex,
    })
    setOpenRecordDialog(true)
  }

  const handleSaveRecord = async () => {
    if (!recordForm.customer_name?.trim() || !recordForm.customer_phone?.trim()) return
    setSavingRecord(true)
    try {
      await api.post('/appointments/', recordForm)
      setOpenRecordDialog(false)
      setSelectedPostIdForNew(null)
      fetchAppointments()
    } catch {
      setError('Ошибка при сохранении записи')
    } finally {
      setSavingRecord(false)
    }
  }

  const handleDeleteRecord = async (id: number) => {
    if (!window.confirm('Удалить эту запись?')) return
    try {
      await api.delete(`/appointments/${id}`)
      fetchAppointments()
    } catch {
      setError('Ошибка при удалении')
    }
  }

  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current
    if (data?.appointment) setActiveAppointment(data.appointment)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveAppointment(null)
    const { active, over } = event
    if (!over?.data.current || !active.data.current?.appointment) return
    const appointment = active.data.current.appointment as Appointment
    const targetPostId = over.data.current.postId as number | undefined
    const targetSlotTime = over.data.current.slotTime as string | undefined
    if (targetPostId === undefined) return
    if (appointment.post_id === targetPostId && targetSlotTime && timeToHHMM(appointment.time) === targetSlotTime) return
    const targetPost = targetPostId === 0 ? null : posts.find((p) => p.id === targetPostId)
    const targetPosts = appointmentsByPost(targetPostId === 0 ? null : targetPostId)
    if (targetPost && !targetSlotTime && targetPosts.length >= targetPost.max_slots) return
    const slotIndex = targetSlotTime && targetPost ? targetPost.slot_times?.indexOf(targetSlotTime) ?? 0 : targetPosts.length
    const displaced = targetSlotTime && targetPost
      ? appointmentsByPost(targetPostId).find((a) => timeToHHMM(a.time) === targetSlotTime)
      : null
    try {
      if (displaced && displaced.id !== appointment.id) {
        const oldTime = timeToHHMM(appointment.time)
        await api.put(`/appointments/${displaced.id}`, {
          post_id: appointment.post_id ?? null,
          time: oldTime.length === 5 ? oldTime : `${oldTime.padStart(2, '0')}:00`,
          sort_order: appointment.sort_order ?? 0,
        })
      }
      await api.put(`/appointments/${appointment.id}`, {
        post_id: targetPostId === 0 ? null : targetPostId,
        time: targetSlotTime ?? undefined,
        sort_order: slotIndex,
      })
      fetchAppointments()
    } catch {
      setError('Не удалось переместить запись')
    }
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  return (
    <Container maxWidth={false} sx={{ maxWidth: 1600 }}>
      <Box sx={{ mb: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Записи
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddRounded />}
            onClick={() => {
              setEditingPostId(null)
              setPostForm({
                name: `Пост ${posts.length + 1}`,
                max_slots: 5,
                sort_order: posts.length,
              })
              setPostFormSlotTimesInput(DEFAULT_SLOT_HOURS)
              setOpenPostDialog(true)
            }}
          >
            Создать пост
          </Button>
        </Stack>
        <Paper sx={{ p: 2, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
          <CalendarMonthRounded sx={{ color: 'primary.main' }} />
          <TextField
            type="date"
            variant="standard"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            InputProps={{ disableUnderline: true }}
            sx={{ '& input': { fontWeight: 700, fontSize: '1rem' } }}
          />
          <Typography variant="body2" color="text.secondary">
            {format(new Date(selectedDate), 'd MMMM yyyy', { locale: ru })}
          </Typography>
        </Paper>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading && appointments.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : posts.length === 0 ? (
        <Paper variant="outlined" sx={{ py: 8, textAlign: 'center', borderStyle: 'dashed' }}>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Нет ни одного поста. Создайте пост — появится колонка с кнопкой «Добавить запись».
          </Typography>
          <Button variant="outlined" startIcon={<AddRounded />} onClick={() => setOpenPostDialog(true)}>
            Создать пост
          </Button>
        </Paper>
      ) : (
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <Box sx={{ display: 'flex', gap: 2, overflowX: 'auto', pb: 2 }}>
            {posts.map((post, idx) => (
              <PostColumn
                key={post.id}
                post={post}
                appointments={appointmentsByPost(post.id)}
                postColor={getPostColor(post, idx)}
                onAddRecord={() => handleOpenAddRecord(post.id)}
                onAddRecordForSlot={
                  post.slot_times?.length
                    ? (slotTime) => handleOpenAddRecordForSlot(post.id, slotTime)
                    : undefined
                }
                onEditPost={handleOpenEditPost}
                onDeletePost={(p) => setDeletePostConfirm(p)}
                onDelete={handleDeleteRecord}
              />
            ))}
            {appointmentsByPost(null).length > 0 && (
              <PostColumn
                key="no-post"
                post={{ id: 0, name: 'Без поста', max_slots: 999, sort_order: -1, created_at: '' }}
                appointments={appointmentsByPost(null)}
                postColor="#94A3B8"
                onAddRecord={() => {}}
                onDelete={handleDeleteRecord}
              />
            )}
          </Box>

          <DragOverlay>
            {activeAppointment ? (
              <Box sx={{ width: 272 }}>
                <AppointmentCard
                  item={activeAppointment}
                  onDelete={() => {}}
                  color={(() => {
                    const p = posts.find((x) => x.id === activeAppointment.post_id)
                    return p ? getPostColor(p, posts.indexOf(p)) : '#6366F1'
                  })()}
                  isDragging
                />
              </Box>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      {/* Диалог создания/редактирования поста */}
      <Dialog
        open={openPostDialog}
        onClose={() => {
          setOpenPostDialog(false)
          setEditingPostId(null)
        }}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2 } }}
      >
        <DialogTitle>{editingPostId !== null ? 'Редактировать пост' : 'Новый пост'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Название"
              value={postForm.name}
              onChange={(e) => setPostForm((p) => ({ ...p, name: e.target.value }))}
              placeholder="Пост 1"
            />
            <TextField
              fullWidth
              type="number"
              label="Максимум записей на посту"
              value={postForm.max_slots}
              onChange={(e) => setPostForm((p) => ({ ...p, max_slots: Math.max(1, parseInt(e.target.value, 10) || 1) }))}
              inputProps={{ min: 1 }}
            />
            <TextField
              fullWidth
              label="Слоты по времени (часы через запятую)"
              value={postFormSlotTimesInput}
              onChange={(e) => setPostFormSlotTimesInput(e.target.value)}
              placeholder="9, 11, 13, 15, 17"
              helperText="На каждом слоте будет своя ячейка с кнопкой «Добавить запись»"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setOpenPostDialog(false)
              setEditingPostId(null)
            }}
          >
            Отмена
          </Button>
          <Button variant="contained" onClick={handleSavePost} disabled={savingPost || !postForm.name.trim()}>
            {savingPost ? <CircularProgress size={24} /> : editingPostId !== null ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Подтверждение удаления поста */}
      <Dialog open={deletePostConfirm !== null} onClose={() => !deletingPost && setDeletePostConfirm(null)}>
        <DialogTitle>Удалить пост?</DialogTitle>
        <DialogContent>
          {deletePostConfirm && (
            <Typography>
              Пост «{deletePostConfirm.name}» будет удалён. Записи на этот пост останутся в системе, но перестанут
              быть привязаны к посту (появятся в колонке «Без поста»).
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeletePostConfirm(null)} disabled={deletingPost}>
            Отмена
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeletePostConfirm}
            disabled={deletingPost}
          >
            {deletingPost ? <CircularProgress size={24} /> : 'Удалить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог новой записи */}
      <Dialog open={openRecordDialog} onClose={() => setOpenRecordDialog(false)} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: 2 } }}>
        <DialogTitle>Новая запись</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label="Время"
              type="time"
              value={recordForm.time}
              onChange={(e) => setRecordForm((p) => ({ ...p, time: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              fullWidth
              label="Имя клиента"
              value={recordForm.customer_name}
              onChange={(e) => setRecordForm((p) => ({ ...p, customer_name: e.target.value }))}
              InputProps={{ startAdornment: <PersonOutlineRounded sx={{ mr: 1, color: 'text.secondary' }} /> }}
            />
            <TextField
              fullWidth
              label="Телефон"
              value={recordForm.customer_phone}
              onChange={(e) => setRecordForm((p) => ({ ...p, customer_phone: e.target.value }))}
              InputProps={{ startAdornment: <PhoneEnabledRounded sx={{ mr: 1, color: 'text.secondary' }} /> }}
            />
            <TextField
              fullWidth
              label="Комментарий"
              multiline
              rows={2}
              value={recordForm.description || ''}
              onChange={(e) => setRecordForm((p) => ({ ...p, description: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRecordDialog(false)}>Отмена</Button>
          <Button variant="contained" onClick={handleSaveRecord} disabled={savingRecord}>
            {savingRecord ? <CircularProgress size={24} /> : 'Записать'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
