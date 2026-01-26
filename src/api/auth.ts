import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9988'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

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
  }
}

export const authApi = {
  // 登录（使用 JSON 格式）
  login: (data: LoginRequest) => {
    return api.post<AuthResponse>('/api/auth/login/json', data)
  },

  // 注册
  register: (data: RegisterRequest) => {
    return api.post<AuthResponse>('/api/auth/register', data)
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return api.get('/api/auth/me')
  }
}

export default api
