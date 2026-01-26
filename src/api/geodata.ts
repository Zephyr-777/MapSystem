import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:9988'

// 创建独立的 axios 实例用于文件下载
const downloadApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 下载可能需要更长时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 token
downloadApi.interceptors.request.use(
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

// 使用 api 实例进行普通请求
import api from './auth'

export interface GeoDataItem {
  id: number
  name: string
  type: string
  uploadTime: string
  extent?: [number, number, number, number]
}

export interface GeoDataListResponse {
  data: GeoDataItem[]
  total: number
}

export interface UploadResponse {
  message: string
  uploaded_files: string[]
  asset_id?: number
  asset_name?: string
  warning?: string
}

export const geoDataApi = {
  // 获取地质数据列表
  getList: () => {
    return api.get<GeoDataListResponse>('/api/geodata/list')
  },

  // 下载地质数据文件
  download: async (id: number) => {
    const response = await downloadApi.get(`/api/geodata/download/${id}`, {
      responseType: 'blob'
    })
    return response.data // 直接返回 blob 数据
  },

  // 上传地质数据文件
  upload: async (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    
    const response = await api.post<UploadResponse>('/api/geodata/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response
  }
}
