import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9988'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 增加超时时间到 15s
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
    const config = error.config
    
    // 处理网络错误 (Network Error)
    if (!error.response) {
      if (error.code === 'ERR_NETWORK') {
        ElMessage.error('网络连接失败，请检查后端服务是否启动')
      } else if (error.code === 'ECONNABORTED') {
        ElMessage.error('请求超时，请检查网络连接')
      } else {
        ElMessage.error(error.message || '未知网络错误')
      }
      return Promise.reject(error)
    }

    // 排除登录和注册接口，避免由于密码错误导致的 401 触发页面重载
    const isAuthPath = config.url?.includes('/api/auth/login') || config.url?.includes('/api/auth/register')
    
    if (error.response.status === 401 && !isAuthPath) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 避免重复跳转
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    } else if (error.response.status >= 500) {
      ElMessage.error('服务器内部错误，请稍后重试')
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
    return api.post<AuthResponse>('/api/auth/login/json', data) as unknown as Promise<AuthResponse>
  },

  // 注册
  register: (data: RegisterRequest) => {
    return api.post<AuthResponse>('/api/auth/register', data) as unknown as Promise<AuthResponse>
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return api.get('/api/auth/me')
  }
}

export default api
