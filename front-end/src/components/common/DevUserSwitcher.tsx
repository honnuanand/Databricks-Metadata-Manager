import { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Chip,
  Button,
  Box,
  Typography,
  IconButton,
} from '@mui/material'
import {
  SwapHoriz as SwapIcon,
  Close as CloseIcon,
  Person as PersonIcon,
  Add as AddIcon,
} from '@mui/icons-material'
import { RootState, AppDispatch } from '../../store/store'
import { switchDevUser, createTestUsers, login } from '../../store/authSlice'

const testUsers = [
  {
    userId: 'u001',
    username: 'john_suggest',
    password: 'suggest123',
    name: 'John Doe',
    role: 'suggest_only',
    roleLabel: 'Suggest Only',
    color: '#2196f3',
  },
  {
    userId: 'u003',
    username: 'jane_approver',
    password: 'approve123',
    name: 'Jane Smith',
    role: 'approver',
    roleLabel: 'Approver',
    color: '#4caf50',
  },
  {
    userId: 'u005',
    username: 'admin_user',
    password: 'admin123',
    name: 'Admin User',
    role: 'admin',
    roleLabel: 'Admin',
    color: '#f44336',
  },
  {
    userId: 'u002',
    username: 'alice_suggest',
    password: 'suggest123',
    name: 'Alice Johnson',
    role: 'suggest_only',
    roleLabel: 'Suggest Only',
    color: '#2196f3',
  },
  {
    userId: 'u004',
    username: 'bob_approver',
    password: 'approve123',
    name: 'Bob Williams',
    role: 'approver',
    roleLabel: 'Approver',
    color: '#4caf50',
  },
]

export default function DevUserSwitcher() {
  const [open, setOpen] = useState(false)
  const [usersCreated, setUsersCreated] = useState(false)
  const dispatch = useDispatch<AppDispatch>()
  const { user } = useSelector((state: RootState) => state.auth)

  const handleCreateTestUsers = async () => {
    try {
      await dispatch(createTestUsers()).unwrap()
      setUsersCreated(true)
    } catch (error) {
      console.error('Failed to create test users:', error)
    }
  }

  const handleSwitchUser = async (userId: string) => {
    try {
      await dispatch(switchDevUser(userId)).unwrap()
      setOpen(false)
    } catch (error) {
      console.error('Failed to switch user:', error)
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
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

  return (
    <>
      <Fab
        color="secondary"
        size="small"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 9999,
        }}
        onClick={() => setOpen(true)}
      >
        <SwapIcon />
      </Fab>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">Development User Switcher</Typography>
            <IconButton onClick={() => setOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {user && (
            <Box mb={2} p={2} bgcolor="grey.100" borderRadius={1}>
              <Typography variant="subtitle2" color="textSecondary">
                Current User
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mt={1}>
                <Avatar sx={{ width: 32, height: 32 }}>
                  <PersonIcon />
                </Avatar>
                <Box flex={1}>
                  <Typography variant="body1">{user.full_name || user.username}</Typography>
                  <Typography variant="caption" color="textSecondary">
                    {user.email}
                  </Typography>
                </Box>
                <Chip
                  label={user.role.replace('_', ' ').toUpperCase()}
                  size="small"
                  color={getRoleColor(user.role) as any}
                />
              </Box>
            </Box>
          )}

          {!usersCreated && (
            <Box mb={2}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={handleCreateTestUsers}
              >
                Create Test Users
              </Button>
            </Box>
          )}

          <Typography variant="subtitle2" color="textSecondary" gutterBottom>
            Switch to Test User
          </Typography>
          <List>
            {testUsers.map((testUser) => (
              <ListItem key={testUser.username} disablePadding>
                <ListItemButton
                  onClick={() => handleSwitchUser(testUser.userId)}
                  disabled={user?.username === testUser.username}
                >
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: testUser.color }}>
                      {testUser.name[0]}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={testUser.name}
                    secondary={`@${testUser.username}`}
                  />
                  <Chip
                    label={testUser.roleLabel}
                    size="small"
                    color={getRoleColor(testUser.role) as any}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>

          <Box mt={2} p={2} bgcolor="warning.light" borderRadius={1}>
            <Typography variant="caption" color="warning.contrastText">
              <strong>Note:</strong> This switcher is only available in development mode.
              Test users have pre-configured passwords for easy switching.
            </Typography>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}