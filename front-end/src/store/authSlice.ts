import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { authService } from '../services/auth.service'

export interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: 'suggest_only' | 'approver' | 'admin'
  is_active: boolean
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
  // Development mode user switcher
  devUsers: User[]
  currentDevUser: User | null
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,
  devUsers: [],
  currentDevUser: null,
}

export const login = createAsyncThunk(
  'auth/login',
  async ({ username, password }: { username: string; password: string }) => {
    const response = await authService.login(username, password)
    return response
  }
)

export const logout = createAsyncThunk('auth/logout', async () => {
  await authService.logout()
})

export const getCurrentUser = createAsyncThunk('auth/getCurrentUser', async () => {
  const response = await authService.getCurrentUser()
  return response
})

export const createTestUsers = createAsyncThunk('auth/createTestUsers', async () => {
  const response = await authService.createTestUsers()
  return response
})

export const switchDevUser = createAsyncThunk(
  'auth/switchDevUser',
  async (userId: string) => {
    const response = await authService.switchDevUser(userId)
    return response
  }
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setDevUsers: (state, action: PayloadAction<User[]>) => {
      state.devUsers = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.user = action.payload.user
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Login failed'
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.user = null
        state.isAuthenticated = false
      })
      // Get current user
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload
        state.isAuthenticated = true
      })
      // Switch dev user
      .addCase(switchDevUser.fulfilled, (state, action) => {
        state.loading = false
        state.isAuthenticated = true
        state.currentDevUser = action.payload.user
        state.user = action.payload.user
      })
      .addCase(switchDevUser.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(switchDevUser.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'User switch failed'
      })
  },
})

export const { clearError, setDevUsers } = authSlice.actions
export default authSlice.reducer