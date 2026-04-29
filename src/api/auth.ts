import { api } from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  email?: string
}

export interface AuthResponse {
  token: string
  user: {
    id: number
    username: string
    email?: string
    role?: string
  }
}

export const authApi = {
  login: (data: LoginRequest) => {
    return api.post<AuthResponse>('/api/auth/login/json', data) as unknown as Promise<AuthResponse>
  },

  register: (data: RegisterRequest) => {
    return api.post<AuthResponse>('/api/auth/register', data) as unknown as Promise<AuthResponse>
  },

  getCurrentUser: () => {
    return api.get('/api/auth/me')
  }
}

export default api
