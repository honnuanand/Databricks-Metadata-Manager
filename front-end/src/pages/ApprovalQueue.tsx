import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Chip,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Divider,
} from '@mui/material'
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Visibility as ViewIcon,
  Comment as CommentIcon,
} from '@mui/icons-material'
import { RootState, AppDispatch } from '../store/store'
import { fetchPendingApprovals, approveComment, rejectComment } from '../store/commentSlice'

export default function ApprovalQueue() {
  const dispatch = useDispatch<AppDispatch>()
  const { pendingApprovals } = useSelector((state: RootState) => state.comments)
  const { user } = useSelector((state: RootState) => state.auth)
  const [selectedComment, setSelectedComment] = useState<any>(null)
  const [actionDialog, setActionDialog] = useState(false)
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [feedback, setFeedback] = useState('')

  useEffect(() => {
    if (user?.role === 'approver' || user?.role === 'admin') {
      dispatch(fetchPendingApprovals())
    }
  }, [dispatch, user])

  const handleAction = (comment: any, actionType: 'approve' | 'reject') => {
    setSelectedComment(comment)
    setAction(actionType)
    setFeedback('')
    setActionDialog(true)
  }

  const handleSubmitAction = async () => {
    if (!selectedComment || !action) return

    if (action === 'approve') {
      await dispatch(approveComment({ id: selectedComment.id, feedback }))
    } else {
      await dispatch(rejectComment({ id: selectedComment.id, feedback: feedback || 'No feedback provided' }))
    }

    setActionDialog(false)
    dispatch(fetchPendingApprovals())
  }

  if (user?.role !== 'approver' && user?.role !== 'admin') {
    return (
      <Box>
        <Alert severity="warning">
          You don't have permission to access this page. Only approvers and admins can review approvals.
        </Alert>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Approval Queue
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Review and approve or reject comment suggestions from users
      </Typography>

      {pendingApprovals.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <CommentIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No pending approvals
          </Typography>
          <Typography variant="body2" color="text.secondary">
            All comment suggestions have been reviewed
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {pendingApprovals.map((comment) => (
            <Grid item xs={12} md={6} key={comment.id}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Chip
                      label={comment.entity_type.toUpperCase()}
                      size="small"
                      color="primary"
                    />
                    <Typography variant="caption" color="text.secondary">
                      {new Date(comment.created_at).toLocaleDateString()}
                    </Typography>
                  </Box>

                  <Typography variant="subtitle2" gutterBottom>
                    Entity Path:
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {comment.entity_path}
                  </Typography>

                  <Divider sx={{ my: 2 }} />

                  {comment.current_comment && (
                    <>
                      <Typography variant="subtitle2" gutterBottom>
                        Current Comment:
                      </Typography>
                      <Paper sx={{ p: 1, bgcolor: 'grey.100', mb: 2 }}>
                        <Typography variant="body2">
                          {comment.current_comment}
                        </Typography>
                      </Paper>
                    </>
                  )}

                  <Typography variant="subtitle2" gutterBottom>
                    Suggested Comment:
                  </Typography>
                  <Paper sx={{ p: 1, bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                    <Typography variant="body2">
                      {comment.suggested_comment}
                    </Typography>
                  </Paper>

                  <Box mt={2}>
                    <Typography variant="caption" color="text.secondary">
                      Submitted by: {comment.creator?.username || 'Unknown'}
                    </Typography>
                  </Box>
                </CardContent>
                <CardActions>
                  <Button
                    size="small"
                    color="success"
                    startIcon={<ApproveIcon />}
                    onClick={() => handleAction(comment, 'approve')}
                  >
                    Approve
                  </Button>
                  <Button
                    size="small"
                    color="error"
                    startIcon={<RejectIcon />}
                    onClick={() => handleAction(comment, 'reject')}
                  >
                    Reject
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={actionDialog} onClose={() => setActionDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {action === 'approve' ? 'Approve Comment' : 'Reject Comment'}
        </DialogTitle>
        <DialogContent>
          {selectedComment && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Entity:</Typography>
                <Typography variant="body2">{selectedComment.entity_path}</Typography>
              </Alert>
              <Alert severity={action === 'approve' ? 'success' : 'error'} sx={{ mb: 2 }}>
                <Typography variant="subtitle2">
                  {action === 'approve' ? 'Approving:' : 'Rejecting:'}
                </Typography>
                <Typography variant="body2">{selectedComment.suggested_comment}</Typography>
              </Alert>
              <TextField
                fullWidth
                multiline
                rows={3}
                label={action === 'approve' ? 'Feedback (optional)' : 'Feedback (required)'}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder={
                  action === 'approve'
                    ? 'Add any feedback for the submitter...'
                    : 'Please provide feedback on why this was rejected...'
                }
                required={action === 'reject'}
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionDialog(false)}>Cancel</Button>
          <Button
            onClick={handleSubmitAction}
            variant="contained"
            color={action === 'approve' ? 'success' : 'error'}
            disabled={action === 'reject' && !feedback.trim()}
          >
            {action === 'approve' ? 'Approve' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}