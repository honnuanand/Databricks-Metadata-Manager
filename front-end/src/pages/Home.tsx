import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  LinearProgress,
} from '@mui/material'
import {
  Storage as StorageIcon,
  Comment as CommentIcon,
  CheckCircle as ApprovedIcon,
  Pending as PendingIcon,
  Person as PersonIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { RootState, AppDispatch } from '../store/store'
import { fetchMyComments, fetchPendingApprovals } from '../store/commentSlice'

export default function Home() {
  const navigate = useNavigate()
  const dispatch = useDispatch<AppDispatch>()
  const { user } = useSelector((state: RootState) => state.auth)
  const { myComments, pendingApprovals } = useSelector((state: RootState) => state.comments)

  useEffect(() => {
    dispatch(fetchMyComments())
    if (user?.role === 'approver' || user?.role === 'admin') {
      dispatch(fetchPendingApprovals())
    }
  }, [dispatch, user])

  const stats = {
    drafts: Array.isArray(myComments) ? myComments.filter(c => c.status === 'draft').length : 0,
    pending: Array.isArray(myComments) ? myComments.filter(c => c.status === 'pending').length : 0,
    approved: Array.isArray(myComments) ? myComments.filter(c => c.status === 'approved' || c.status === 'applied').length : 0,
    rejected: Array.isArray(myComments) ? myComments.filter(c => c.status === 'rejected').length : 0,
  }

  const getRoleDescription = () => {
    switch (user?.role) {
      case 'admin':
        return 'You have full access to all features including user management'
      case 'approver':
        return 'You can suggest comments and approve submissions from other users'
      case 'suggest_only':
        return 'You can browse the catalog and suggest metadata comments'
      default:
        return ''
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Welcome, {user?.full_name || user?.username}!
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        {getRoleDescription()}
      </Typography>

      <Grid container spacing={3}>
        {/* User Info Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <PersonIcon color="primary" />
                <Typography variant="h6">Your Profile</Typography>
              </Box>
              <Box display="flex" flexDirection="column" gap={1}>
                <Typography variant="body2">
                  <strong>Username:</strong> {user?.username}
                </Typography>
                <Typography variant="body2">
                  <strong>Email:</strong> {user?.email}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2">
                    <strong>Role:</strong>
                  </Typography>
                  <Chip
                    label={user?.role.replace('_', ' ').toUpperCase()}
                    size="small"
                    color={
                      user?.role === 'admin'
                        ? 'error'
                        : user?.role === 'approver'
                        ? 'success'
                        : 'primary'
                    }
                  />
                </Box>
              </Box>
            </CardContent>
            <CardActions>
              <Button size="small" onClick={() => navigate('/profile')}>
                View Profile
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Quick Actions Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <TrendingUpIcon color="primary" />
                <Typography variant="h6">Quick Actions</Typography>
              </Box>
              <Box display="flex" flexDirection="column" gap={1}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<StorageIcon />}
                  onClick={() => navigate('/catalog')}
                >
                  Browse Catalog
                </Button>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<CommentIcon />}
                  onClick={() => navigate('/my-comments')}
                >
                  My Comments
                </Button>
                {(user?.role === 'approver' || user?.role === 'admin') && (
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={<ApprovedIcon />}
                    onClick={() => navigate('/approvals')}
                    color="success"
                  >
                    Review Approvals ({pendingApprovals.length})
                  </Button>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Statistics Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <CommentIcon color="primary" />
                <Typography variant="h6">Your Comments</Typography>
              </Box>
              <Box display="flex" flexDirection="column" gap={1}>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Drafts:</Typography>
                  <Chip label={stats.drafts} size="small" />
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Pending Approval:</Typography>
                  <Chip label={stats.pending} size="small" color="warning" />
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Approved:</Typography>
                  <Chip label={stats.approved} size="small" color="success" />
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Rejected:</Typography>
                  <Chip label={stats.rejected} size="small" color="error" />
                </Box>
              </Box>
            </CardContent>
            <CardActions>
              <Button size="small" onClick={() => navigate('/my-comments')}>
                View All Comments
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Pending Approvals Card (for approvers only) */}
        {(user?.role === 'approver' || user?.role === 'admin') && pendingApprovals.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <PendingIcon color="warning" />
                <Typography variant="h6">Pending Approvals</Typography>
                <Chip label={pendingApprovals.length} color="warning" size="small" />
              </Box>
              <Box>
                {pendingApprovals.slice(0, 5).map((comment) => (
                  <Box
                    key={comment.id}
                    sx={{
                      p: 2,
                      mb: 1,
                      bgcolor: 'background.default',
                      borderRadius: 1,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Box>
                      <Typography variant="body2">
                        <strong>{comment.entity_type.toUpperCase()}:</strong> {comment.entity_path}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Submitted by {comment.creator?.username} • {new Date(comment.created_at).toLocaleDateString()}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => navigate('/approvals')}
                    >
                      Review
                    </Button>
                  </Box>
                ))}
                {pendingApprovals.length > 5 && (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 2 }}>
                    And {pendingApprovals.length - 5} more...
                  </Typography>
                )}
              </Box>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  )
}