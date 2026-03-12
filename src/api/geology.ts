import api from './auth'

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
  // Get features as GeoJSON
  getFeatures: (params?: GeologyFilterParams) => {
    return api.get<FeatureCollection>('/api/geology/list', { params }) as unknown as Promise<FeatureCollection>
  },

  // Get stats for classification
  getStats: () => {
    return api.get<GeologyStats>('/api/geology/stats') as unknown as Promise<GeologyStats>
  },

  // Export data
  exportData: (format: 'excel' | 'csv' | 'shapefile', params?: GeologyFilterParams) => {
    // We need to build the URL manually or use axios download
    const queryParams = new URLSearchParams();
    queryParams.append('format', format);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            queryParams.append(key, String(value));
        }
      });
    }
    
    // Construct absolute URL or relative
    // Assuming api.defaults.baseURL is set or we use relative
    const url = `/api/geology/export?${queryParams.toString()}`;
    window.open(url, '_blank');
  }
}
