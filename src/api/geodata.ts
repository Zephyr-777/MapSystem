import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9988'

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
  type?: string
  sub_type?: string
  file_path?: string
  uploadTime: string
  extent?: [number, number, number, number]
  srid?: number
  center_x?: number
  center_y?: number
  lithology?: string
  description?: string
  reports?: Array<{ title: string; url: string }>
}

export interface GeoDataListResponse {
  data: GeoDataItem[]
  total: number
}

export interface UploadResponse {
  message: string
  processed: Array<{
    id?: number
    name: string
    type: string
    rows?: number
    details?: any
  }>
  errors: string[]
  zip_results?: Record<string, any>
}

export const geoDataApi = {
  // 获取地质数据列表
  getList: () => {
    return api.get<GeoDataListResponse>('/api/geodata/list') as unknown as Promise<GeoDataListResponse>
  },

  // 搜索地质数据
  search: (query: string, center?: [number, number]) => {
    const params: any = { q: query }
    if (center) {
      params.lon = center[0]
      params.lat = center[1]
    }
    return api.get<GeoDataListResponse>('/api/geodata/search', {
      params
    }) as unknown as Promise<GeoDataListResponse>
  },

  // 空间属性识别
  identify: (lon: number, lat: number, buffer: number = 100) => {
    return api.get<GeoDataListResponse>('/api/geodata/identify', {
      params: { lon, lat, buffer }
    }) as unknown as Promise<GeoDataListResponse>
  },

  // 获取地质数据详情
  getDetail: (id: number) => {
    return api.get<any>(`/api/geodata/detail/${id}`) as unknown as Promise<any>
  },

  // 下载地质数据文件
  download: async (id: number) => {
    const response = await downloadApi.get(`/api/geodata/download/${id}`, {
      responseType: 'blob'
    })
    return response.data // 直接返回 blob 数据
  },

  downloadBatch: async (ids: number[]) => {
    const response = await downloadApi.post(
      '/api/geodata/download-batch',
      { ids },
      { responseType: 'blob' }
    )
    return response.data
  },

  // 获取统计数据
  getStats: () => {
    return api.get<any>('/api/geodata/stats') as unknown as Promise<any>
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
    return response as unknown as UploadResponse
  }
}
