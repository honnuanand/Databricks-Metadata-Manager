import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Divider,
} from '@mui/material'
import {
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  VerifiedUser as ApproverIcon,
  Login as LoginIcon,
  BugReport as BugReportIcon,
} from '@mui/icons-material'
import { AppDispatch } from '../store/store'
import { login } from '../store/authSlice'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await dispatch(login({ username, password })).unwrap()
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleQuickLogin = async (testUsername: string, testPassword: string) => {
    setUsername(testUsername)
    setPassword(testPassword)
    setError('')
    setLoading(true)

    try {
      await dispatch(login({ username: testUsername, password: testPassword })).unwrap()
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const testUsers = [
    {
      username: 'user@example.com',
      password: 'user123',
      name: 'Test User',
      role: 'Suggest Only',
      description: 'Can browse catalogs and suggest comments',
      color: 'primary',
      icon: <PersonIcon />
    },
    {
      username: 'approver@example.com',
      password: 'approver123',
      name: 'Approver User',
      role: 'Approver',
      description: 'Can suggest and approve/reject comments',
      color: 'success',
      icon: <ApproverIcon />
    },
    {
      username: 'admin@example.com',
      password: 'admin123',
      name: 'Admin User',
      role: 'Admin',
      description: 'Full system access including user management',
      color: 'error',
      icon: <AdminIcon />
    },
  ]

  return (
    <Container component="main" maxWidth="md">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%', maxWidth: 800 }}>
          <Typography component="h1" variant="h4" align="center" gutterBottom>
            Databricks Metadata Manager
          </Typography>
          <Typography variant="body2" color="textSecondary" align="center" paragraph>
            Sign in to manage your Databricks catalog metadata
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="Username"
              name="username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              data-testid="username-input"
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="password-input"
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
              data-testid="login-button"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </Box>

          {import.meta.env.DEV && (
            <Box mt={4}>
              <Divider sx={{ mb: 3 }}>
                <Chip label="Quick Login (Development Only)" size="small" />
              </Divider>
              <Grid container spacing={2}>
                {testUsers.map((user) => (
                  <Grid item xs={12} sm={4} key={user.username}>
                    <Card 
                      elevation={2}
                      sx={{
                        cursor: 'pointer',
                        transition: 'transform 0.2s, box-shadow 0.2s',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: 4,
                        },
                        border: username === user.username ? '2px solid' : '1px solid transparent',
                        borderColor: username === user.username ? `${user.color}.main` : 'transparent',
                      }}
                      onClick={() => handleQuickLogin(user.username, user.password)}
                    >
                      <CardContent sx={{ pb: 1 }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <Box sx={{ color: `${user.color}.main` }}>
                            {user.icon}
                          </Box>
                          <Typography variant="h6" component="div">
                            {user.name}
                          </Typography>
                        </Box>
                        <Chip
                          label={user.role}
                          size="small"
                          color={user.color as any}
                          sx={{ mb: 1 }}
                        />
                        <Typography variant="caption" color="text.secondary" display="block">
                          {user.description}
                        </Typography>
                      </CardContent>
                      <CardActions sx={{ pt: 0 }}>
                        <Button
                          size="small"
                          startIcon={<LoginIcon />}
                          disabled={loading}
                          fullWidth
                          variant="outlined"
                          color={user.color as any}
                        >
                          Login as {user.name}
                        </Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
              
              <Box mt={2} p={1.5} bgcolor="warning.light" borderRadius={1} sx={{ opacity: 0.8 }}>
                <Typography variant="caption" color="warning.contrastText" display="block" textAlign="center">
                  ⚠️ Development Mode: Click any card above for instant login
                </Typography>
              </Box>
            </Box>
          )}

          {/* Test Runner Link - Always Available */}
          <Box mt={3} textAlign="center">
            <Button
              variant="outlined"
              color="secondary"
              onClick={() => navigate('/test-runner')}
              startIcon={<BugReportIcon />}
              fullWidth
            >
              🧪 Run Authentication Tests
            </Button>
            <Typography variant="caption" display="block" color="text.secondary" mt={1}>
              Test authentication inside SSO boundary
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  )
}