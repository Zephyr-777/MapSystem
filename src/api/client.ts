import axios from 'axios'
import { ElMessage } from 'element-plus'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9988'

function createApiClient(timeout = 15000) {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout,
    headers: { 'Content-Type': 'application/json' }
  })

  instance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  instance.interceptors.response.use(
    (response) => response.data,
    (error) => {
      const config = error.config

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

      const isAuthPath = config?.url?.includes('/api/auth/login') ||
                         config?.url?.includes('/api/auth/register')

      if (error.response.status === 401 && !isAuthPath) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      } else if (error.response.status >= 500) {
        ElMessage.error('服务器内部错误，请稍后重试')
      }

      return Promise.reject(error)
    }
  )

  return instance
}

export const api = createApiClient(15000)
export const downloadApi = createApiClient(60000)
export default api
