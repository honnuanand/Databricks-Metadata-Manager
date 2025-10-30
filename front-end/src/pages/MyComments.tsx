import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
} from '@mui/material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Send as SendIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material'
import { RootState, AppDispatch } from '../store/store'
import { fetchMyComments, updateComment, submitComments } from '../store/commentSlice'
import { commentService } from '../services/comment.service'

export default function MyComments() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { myComments } = useSelector((state: RootState) => state.comments)
  const [tab, setTab] = useState(0)
  const [selectedComments, setSelectedComments] = useState<string[]>([])
  const [editDialog, setEditDialog] = useState(false)
  const [editingComment, setEditingComment] = useState<any>(null)
  const [suggestedComment, setSuggestedComment] = useState('')

  useEffect(() => {
    dispatch(fetchMyComments())
  }, [dispatch])

  const getFilteredComments = () => {
    switch (tab) {
      case 0:
        return myComments.filter(c => c.status === 'draft')
      case 1:
        return myComments.filter(c => c.status === 'pending')
      case 2:
        return myComments.filter(c => c.status === 'approved' || c.status === 'applied')
      case 3:
        return myComments.filter(c => c.status === 'rejected')
      default:
        return myComments
    }
  }

  const handleEdit = (comment: any) => {
    setEditingComment(comment)
    setSuggestedComment(comment.suggested_comment)
    setEditDialog(true)
  }

  const handleUpdateComment = async () => {
    if (!editingComment || !suggestedComment.trim()) return

    await dispatch(
      updateComment({
        id: editingComment.id,
        suggested_comment: suggestedComment,
      })
    )
    setEditDialog(false)
    dispatch(fetchMyComments())
  }

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this comment?')) {
      await commentService.deleteComment(id)
      dispatch(fetchMyComments())
    }
  }

  const handleSubmitSelected = async () => {
    if (selectedComments.length === 0) return

    await dispatch(submitComments(selectedComments))
    setSelectedComments([])
    dispatch(fetchMyComments())
  }

  const handleViewInCatalog = (comment: any) => {
    // Parse entity path to navigate to the correct location
    const parts = comment.entity_path.split('.')
    
    if (parts.length >= 3) {
      // Has at least catalog.schema.table
      const [catalog, schema, table] = parts
      
      // Navigate to catalog explorer with the specific table selected
      navigate(`/catalog?catalog=${catalog}&schema=${schema}&table=${table}`)
    } else if (parts.length === 2) {
      // Has catalog.schema
      const [catalog, schema] = parts
      navigate(`/catalog?catalog=${catalog}&schema=${schema}`)
    } else if (parts.length === 1) {
      // Has only catalog
      const [catalog] = parts
      navigate(`/catalog?catalog=${catalog}`)
    } else {
      // Fallback to main catalog page
      navigate('/catalog')
    }
  }

  const columns: GridColDef[] = [
    {
      field: 'entity_type',
      headerName: 'Type',
      width: 100,
      renderCell: (params) => (
        <Chip label={params.value.toUpperCase()} size="small" />
      ),
    },
    {
      field: 'entity_path',
      headerName: 'Entity',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <Button
          variant="text"
          size="small"
          onClick={() => handleViewInCatalog(params.row)}
          sx={{ 
            textTransform: 'none',
            justifyContent: 'flex-start',
            color: 'primary.main',
            fontWeight: 'normal',
            fontSize: '0.875rem'
          }}
        >
          {params.value}
        </Button>
      ),
    },
    {
      field: 'suggested_comment',
      headerName: 'Suggested Comment',
      flex: 2,
      minWidth: 300,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => {
        const getColor = () => {
          switch (params.value) {
            case 'draft': return 'default'
            case 'pending': return 'warning'
            case 'approved': return 'success'
            case 'applied': return 'success'
            case 'rejected': return 'error'
            default: return 'default'
          }
        }
        return (
          <Chip
            label={params.value.toUpperCase()}
            size="small"
            color={getColor() as any}
          />
        )
      },
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 150,
      valueFormatter: (params) => new Date(params.value).toLocaleDateString(),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      sortable: false,
      renderCell: (params) => {
        if (params.row.status === 'draft') {
          return (
            <Box>
              <IconButton size="small" onClick={() => handleEdit(params.row)}>
                <EditIcon fontSize="small" />
              </IconButton>
              <IconButton size="small" onClick={() => handleDelete(params.row.id)}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          )
        }
        return (
          <IconButton 
            size="small" 
            onClick={() => handleViewInCatalog(params.row)}
            title="View in Catalog"
          >
            <ViewIcon fontSize="small" />
          </IconButton>
        )
      },
    },
  ]

  const draftComments = getFilteredComments()

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        My Comments
      </Typography>

      <Paper sx={{ width: '100%', mb: 2 }}>
        <Tabs value={tab} onChange={(_, newValue) => setTab(newValue)}>
          <Tab
            label={
              <Box display="flex" alignItems="center" gap={1}>
                Drafts
                <Chip label={myComments.filter(c => c.status === 'draft').length} size="small" />
              </Box>
            }
          />
          <Tab
            label={
              <Box display="flex" alignItems="center" gap={1}>
                Pending
                <Chip label={myComments.filter(c => c.status === 'pending').length} size="small" color="warning" />
              </Box>
            }
          />
          <Tab
            label={
              <Box display="flex" alignItems="center" gap={1}>
                Approved
                <Chip label={myComments.filter(c => c.status === 'approved' || c.status === 'applied').length} size="small" color="success" />
              </Box>
            }
          />
          <Tab
            label={
              <Box display="flex" alignItems="center" gap={1}>
                Rejected
                <Chip label={myComments.filter(c => c.status === 'rejected').length} size="small" color="error" />
              </Box>
            }
          />
        </Tabs>
      </Paper>

      {tab === 0 && draftComments.length > 0 && (
        <Box mb={2}>
          <Button
            variant="contained"
            startIcon={<SendIcon />}
            onClick={handleSubmitSelected}
            disabled={selectedComments.length === 0}
          >
            Submit Selected ({selectedComments.length})
          </Button>
        </Box>
      )}

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={draftComments}
          columns={columns}
          checkboxSelection={tab === 0}
          onRowSelectionModelChange={(newSelection) => {
            setSelectedComments(newSelection as string[])
          }}
          rowSelectionModel={selectedComments}
          disableRowSelectionOnClick
        />
      </Paper>

      <Dialog open={editDialog} onClose={() => setEditDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Comment Suggestion</DialogTitle>
        <DialogContent>
          {editingComment && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Entity:</Typography>
                <Typography variant="body2">{editingComment.entity_path}</Typography>
              </Alert>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Suggested Comment"
                value={suggestedComment}
                onChange={(e) => setSuggestedComment(e.target.value)}
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog(false)}>Cancel</Button>
          <Button
            onClick={handleUpdateComment}
            variant="contained"
            disabled={!suggestedComment.trim()}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}