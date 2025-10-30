import { useSelector } from 'react-redux'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Avatar,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material'
import {
  Person as PersonIcon,
  Email as EmailIcon,
  Badge as BadgeIcon,
  Security as SecurityIcon,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material'
import { RootState } from '../store/store'

export default function UserProfile() {
  const { user } = useSelector((state: RootState) => state.auth)

  const getRoleColor = () => {
    switch (user?.role) {
      case 'admin':
        return 'error'
      case 'approver':
        return 'success'
      case 'suggest_only':
        return 'primary'
      default:
        return 'default'
    }
  }

  const getRoleDescription = () => {
    switch (user?.role) {
      case 'admin':
        return 'Full system access including user management, comment approval, and system configuration'
      case 'approver':
        return 'Can suggest comments and approve/reject submissions from other users'
      case 'suggest_only':
        return 'Can browse the catalog and suggest metadata comments for approval'
      default:
        return ''
    }
  }

  const getPermissions = () => {
    switch (user?.role) {
      case 'admin':
        return [
          'Browse all catalogs and schemas',
          'Suggest metadata comments',
          'Approve/reject comment suggestions',
          'Manage user accounts',
          'View system analytics',
          'Configure system settings',
        ]
      case 'approver':
        return [
          'Browse all catalogs and schemas',
          'Suggest metadata comments',
          'Approve/reject comment suggestions',
          'View approval queue',
          'Access approval history',
        ]
      case 'suggest_only':
        return [
          'Browse all catalogs and schemas',
          'Suggest metadata comments',
          'View own comment history',
          'Edit draft comments',
          'Submit comments for approval',
        ]
      default:
        return []
    }
  }

  if (!user) {
    return (
      <Box>
        <Typography>Loading user profile...</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        User Profile
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Avatar
              sx={{
                width: 120,
                height: 120,
                margin: '0 auto',
                mb: 2,
                bgcolor: 'primary.main',
                fontSize: '3rem',
              }}
            >
              {user.full_name?.[0] || user.username[0].toUpperCase()}
            </Avatar>
            <Typography variant="h5" gutterBottom>
              {user.full_name || user.username}
            </Typography>
            <Chip
              label={user.role.replace('_', ' ').toUpperCase()}
              color={getRoleColor() as any}
              size="medium"
            />
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Account Information
            </Typography>
            <List>
              <ListItem>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <PersonIcon fontSize="small" />
                      Username
                    </Box>
                  }
                  secondary={user.username}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <EmailIcon fontSize="small" />
                      Email
                    </Box>
                  }
                  secondary={user.email}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <BadgeIcon fontSize="small" />
                      Full Name
                    </Box>
                  }
                  secondary={user.full_name || 'Not provided'}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <SecurityIcon fontSize="small" />
                      Account Status
                    </Box>
                  }
                  secondary={
                    <Chip
                      label={user.is_active ? 'Active' : 'Inactive'}
                      color={user.is_active ? 'success' : 'error'}
                      size="small"
                    />
                  }
                />
              </ListItem>
            </List>
          </Paper>

          <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Role & Permissions
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {getRoleDescription()}
            </Typography>
            <Typography variant="subtitle2" gutterBottom>
              Your Permissions:
            </Typography>
            <List dense>
              {getPermissions().map((permission, index) => (
                <ListItem key={index}>
                  <ListItemText
                    primary={`• ${permission}`}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}