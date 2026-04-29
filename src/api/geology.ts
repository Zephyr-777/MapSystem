import { api, downloadApi } from './client'

export interface FeatureProperties {
  id: number
  name: string
  era?: string
  lithology_class?: string
  rock_type?: string
  structure_type?: string
  mineral?: string
  elevation?: number
  sample_date?: string
  description?: string
  image_path?: string
  highlights?: Record<string, string>
  [key: string]: any
}

export interface FeatureGeoJSON {
  type: "Feature"
  geometry: {
    type: string
    coordinates: number[] | number[][] | number[][][]
  }
  properties: FeatureProperties
}

export interface FeatureCollection {
  type: "FeatureCollection"
  features: FeatureGeoJSON[]
  total?: number
  page?: number
  page_size?: number
}

export interface GeologyStats {
  eras: Record<string, number>
  lithologies: Record<string, number>
  structures: Record<string, number>
  minerals: Record<string, number>
}

export interface GeologyFilterParams {
  era?: string
  lithology?: string
  structure?: string
  mineral?: string
  q?: string
  page?: number
  page_size?: number
  sample_id?: string
  elevation_min?: number
  elevation_max?: number
  date_start?: string
  date_end?: string
}

export const geologyApi = {
  getFeatures: (params?: GeologyFilterParams) => {
    return api.get<FeatureCollection>('/api/geology/list', { params }) as unknown as Promise<FeatureCollection>
  },

  getStats: () => {
    return api.get<GeologyStats>('/api/geology/stats') as unknown as Promise<GeologyStats>
  },

  exportData: (format: 'excel' | 'csv' | 'shapefile' | 'markdown' | 'pdf', params?: GeologyFilterParams, srid: number = 4326) => {
    return api.get('/api/geology/export', {
      params: { ...params, format, srid },
      responseType: 'blob',
    }) as unknown as Promise<Blob>
  },

  exportDataByIds: (format: 'excel' | 'csv' | 'shapefile' | 'markdown' | 'pdf', ids: number[], srid: number = 4326) => {
    return api.get('/api/geology/export', {
      params: { format, ids: ids.join(','), srid },
      responseType: 'blob'
    }) as unknown as Promise<Blob>
  },

  fetchFeatureImageBlob: async (id: number) => {
    const response = await downloadApi.get(`/api/geology/image/${id}`, {
      responseType: 'blob'
    })
    return response as unknown as Blob
  }
}
