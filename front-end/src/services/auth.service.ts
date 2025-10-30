import api from './api'
import { User } from '../store/authSlice'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

class AuthService {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await api.post('/api/v1/auth/login', {
      username,
      password,
    })
    
    const { access_token, refresh_token } = response.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    
    // Get user details
    const userResponse = await api.get('/api/v1/auth/me')
    
    return {
      ...response.data,
      user: userResponse.data.user,
    }
  }
  
  async logout(): Promise<void> {
    try {
      await api.post('/api/v1/auth/logout')
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }
  
  async register(userData: {
    email: string
    username: string
    password: string
    full_name?: string
    role?: string
  }): Promise<User> {
    const response = await api.post('/api/v1/auth/register', userData)
    return response.data
  }
  
  async getCurrentUser(): Promise<User> {
    const response = await api.get('/api/v1/auth/me')
    return response.data.user
  }
  
  async createTestUsers(): Promise<any> {
    const response = await api.post('/api/v1/auth/dev/create-test-users')
    return response.data
  }
  
  async switchDevUser(userId: string): Promise<LoginResponse> {
    const response = await api.post('/api/v1/auth/dev/switch-user', null, {
      params: { user_id: userId },
    })
    
    const { access_token, refresh_token } = response.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    
    return response.data
  }
  
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token')
  }
}

// Updated to use /api/v1/auth/me endpoint
export const authService = new AuthService()