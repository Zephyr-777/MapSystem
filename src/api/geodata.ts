import { API_BASE_URL, api, downloadApi } from './client'

export interface GeoDataItem {
  id: number
  name: string
  type?: string
  sub_type?: string
  file_path?: string
  image_path?: string
  uploadTime: string
  extent?: [number, number, number, number]
  srid?: number
  center_x?: number
  center_y?: number
  distance?: number
  lithology?: string
  description?: string
  asset_family?: string
  render_mode?: string
  overlay_supported?: boolean
  index_point_enabled?: boolean
  downloadable?: boolean
  overlay_id?: string
  source?: string
  site_key?: string
  site_name?: string
  metadata?: {
    dataset_name?: string
    time_range?: string
    record_count?: number
    device_name?: string
    avg_soil_respiration_rate?: number
    min_soil_respiration_rate?: number
    max_soil_respiration_rate?: number
    source_file_name?: string
    soil_respiration_rate?: number
    linear_flux?: number
    fit_status?: string
    raw_metadata?: any
    dims?: Record<string, number>
    variables?: Array<{
      name: string
      long_name?: string
      units?: string
    }>
    [key: string]: any
  }
  reports?: Array<{ title: string; url: string }>
  dataset_id?: string
  time_range?: string
  record_count?: number
  device_name?: string
  download_url?: string
  avg_soil_respiration_rate?: number
  min_soil_respiration_rate?: number
  max_soil_respiration_rate?: number
  bbox?: [number, number, number, number]
  ring_code?: string
  observed_at?: string
  soil_respiration_rate?: number
  linear_flux?: number
  fit_status?: string
  source_file_name?: string
  location_precision?: string
  metric?: string
  year?: number
  unit?: string
}

export interface GeoDataListResponse {
  data: GeoDataItem[]
  total: number
}

export interface SmartSearchConfig {
  provider?: string
  model?: string
  api_key?: string
  base_url?: string
  enabled?: boolean
}

export interface SmartSearchResponse extends GeoDataListResponse {
  mode: 'ai' | 'fallback'
  reason?: string
}

export interface LocalRasterOverlay {
  id: string
  name: string
  extent: [number, number, number, number]
  srid: number
  min_zoom: number
  opacity: number
  center_x?: number
  center_y?: number
  description?: string
  source_path?: string
  raster_url?: string
  band_count?: number
  dtype?: string
  nodata?: number
  raster_min?: number
  raster_max?: number
}

export interface HeiheFeatureProperties extends GeoDataItem {
  dataset_id: string
  site_key: string
  site_name?: string
}

export interface GeoJSONGeometry {
  type: string
  coordinates: any
}

export interface HeiheGeoJSONFeature {
  type: 'Feature'
  id?: number | string
  geometry: GeoJSONGeometry
  properties: HeiheFeatureProperties
}

export interface HeiheGeoJSONResponse {
  type: 'FeatureCollection'
  dataset_id: string
  mode: 'sites' | 'observations'
  bbox?: [number, number, number, number]
  metadata?: {
    dataset_name?: string
    time_range?: string
    device_name?: string
    record_count?: number
    site_count?: number
  }
  features: HeiheGeoJSONFeature[]
}

export interface HeiheGrasslandGeoJSONResponse {
  type: 'FeatureCollection'
  dataset_id: 'heihe-grassland-1988'
  mode: 'polygons' | 'points'
  bbox?: [number, number, number, number]
  metadata?: {
    dataset_name?: string
    time_range?: string
    scale?: string
    source_format?: string
    record_count?: number
    type_counts?: Record<string, number>
    [key: string]: any
  }
  features: Array<{
    type: 'Feature'
    id?: number | string
    geometry: GeoJSONGeometry
    properties: GeoDataItem & Record<string, any>
  }>
}

export interface ForestCarbonMetricOption {
  id: 'AGBC' | 'BGBC'
  label: string
  unit: string
  description?: string
}

export interface ForestCarbonOverlay {
  id: string
  dataset_id: 'china-forest-carbon-2002-2021'
  name: string
  metric: 'AGBC' | 'BGBC'
  metric_label: string
  year: number
  years: number[]
  metrics: ForestCarbonMetricOption[]
  extent: [number, number, number, number]
  srid: number
  min_zoom: number
  opacity: number
  center_x?: number
  center_y?: number
  description?: string
  source_path?: string
  raster_url: string
  download_url: string
  band_count?: number
  dtype?: string
  nodata?: number | null
  raster_min?: number
  raster_max?: number
  unit?: string
  time_range?: string
  metadata?: Record<string, any>
}

export interface SouthwestTemperatureDataset {
  dataset_id: 'southwest-china-temperature-90ka'
  name: string
  description: string
  center_x: number
  center_y: number
  srid: number
  bbox: [number, number, number, number]
  download_url: string
  file_name: string
  file_size: number
  time_range: string
  metadata?: Record<string, any>
}

export interface CentralAsiaDesertGeoJSONResponse {
  type: 'FeatureCollection'
  dataset_id: 'central-asia-desert-urban-2012-2016'
  mode: 'countries' | 'urban-polygons' | 'urban-points'
  bbox?: [number, number, number, number]
  metadata?: {
    dataset_name?: string
    time_range?: string
    record_count?: number
    returned_count?: number
    country_count?: number
    country_names?: string[]
    density_bucket?: string
    layer_name?: string
    [key: string]: any
  }
  features: Array<{
    type: 'Feature'
    id?: number | string
    geometry: GeoJSONGeometry
    properties: GeoDataItem & Record<string, any>
  }>
}

export interface BadalingImageryTile {
  tile_id: string
  level: number
  name: string
  path: string
  extent: [number, number, number, number]
  center_x: number
  center_y: number
  srid: number
  band_count: number
  dtype?: string
  min_zoom: number
  max_zoom?: number | null
  raster_url: string
}

export interface BadalingImageryLevel {
  level: number
  min_zoom: number
  max_zoom?: number | null
  bbox: [number, number, number, number]
  tiles: BadalingImageryTile[]
}

export interface BadalingImageryDataset {
  dataset_id: 'badaling-town-imagery' | 'hepingjie-street-imagery'
  name: string
  description: string
  time_range: string
  srid: number
  bbox: [number, number, number, number]
  center_x: number
  center_y: number
  min_zoom: number
  max_zoom?: number | null
  levels: BadalingImageryLevel[]
  tile_count: number
  download_url: string
  metadata?: Record<string, any>
}

export interface UploadResponse {
  message: string
  processed: Array<{
    id?: number
    name: string
    type: string
    file_type?: string
    sub_type?: string
    center_x?: number | null
    center_y?: number | null
    srid?: number | null
    extent?: [number, number, number, number] | null
    image_path?: string | null
    rows?: number
    details?: any
  }>
  errors: string[]
  zip_results?: Record<string, any>
}

export interface PreviewBlobOptions {
  fullSize?: boolean
}

export interface BBoxFilter {
  bbox?: [number, number, number, number]
}

const serializeBBox = (bbox?: [number, number, number, number]) =>
  bbox ? bbox.map((value) => Number(value.toFixed(6))).join(',') : undefined

export const geoDataApi = {
  getList: (options: BBoxFilter = {}) => {
    return api.get<GeoDataListResponse>('/api/geodata/list', {
      params: {
        ...(options.bbox ? { bbox: serializeBBox(options.bbox) } : {})
      }
    }) as unknown as Promise<GeoDataListResponse>
  },

  search: (query: string, center?: [number, number], options: BBoxFilter = {}) => {
    const params: any = { q: query }
    if (center) {
      params.lon = center[0]
      params.lat = center[1]
    }
    if (options.bbox) {
      params.bbox = serializeBBox(options.bbox)
    }
    return api.get<GeoDataListResponse>('/api/geodata/search', {
      params
    }) as unknown as Promise<GeoDataListResponse>
  },

  identify: (lon: number, lat: number, buffer: number = 100) => {
    return api.get<GeoDataListResponse>('/api/geodata/identify', {
      params: { lon, lat, buffer }
    }) as unknown as Promise<GeoDataListResponse>
  },

  nearby: (lon: number, lat: number, radius: number = 1000) => {
    return api.get<GeoDataListResponse>('/api/geodata/nearby', {
      params: { lon, lat, radius }
    }) as unknown as Promise<GeoDataListResponse>
  },

  bufferQuery: (center_lon: number, center_lat: number, radius_meters: number) => {
    return api.post<GeoDataListResponse>('/api/geodata/buffer-query', {
      center_lon,
      center_lat,
      radius_meters
    }) as unknown as Promise<GeoDataListResponse>
  },

  upload: (formData: FormData) => {
    return api.post<UploadResponse>('/api/geodata/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }) as unknown as Promise<UploadResponse>
  },

  smartSearch: (query: string, config?: SmartSearchConfig) => {
    return api.post<SmartSearchResponse>('/api/geodata/smart-search', {
      query,
      config
    }) as unknown as Promise<SmartSearchResponse>
  },

  getDetail: (id: number) => {
    return api.get<any>(`/api/geodata/detail/${id}`) as unknown as Promise<any>
  },

  getPreviewUrl: (id: number, fullSize: boolean = false) => {
    const suffix = fullSize ? '?full_size=true' : ''
    return `${API_BASE_URL}/api/geodata/preview/${id}${suffix}`
  },

  getLocalRasterOverlays: () => {
    return api.get<LocalRasterOverlay[]>('/api/geodata/local-raster-overlays') as unknown as Promise<LocalRasterOverlay[]>
  },

  getHeiheGeoJSON: (mode: 'sites' | 'observations' = 'sites', siteKey?: string) => {
    return api.get<HeiheGeoJSONResponse>('/api/geodata/heihe', {
      params: {
        mode,
        ...(siteKey ? { site_key: siteKey } : {})
      }
    }) as unknown as Promise<HeiheGeoJSONResponse>
  },

  getHeiheGrasslandGeoJSON: (mode: 'polygons' | 'points' = 'polygons') => {
    return api.get<HeiheGrasslandGeoJSONResponse>('/api/geodata/heihe-grassland', {
      params: { mode }
    }) as unknown as Promise<HeiheGrasslandGeoJSONResponse>
  },

  getForestCarbonOverlay: (metric: 'AGBC' | 'BGBC' = 'AGBC', year: number = 2021) => {
    return api.get<ForestCarbonOverlay>('/api/geodata/forest-carbon', {
      params: { metric, year }
    }) as unknown as Promise<ForestCarbonOverlay>
  },

  getSouthwestTemperatureDataset: () => {
    return api.get<SouthwestTemperatureDataset>('/api/geodata/southwest-temperature') as unknown as Promise<SouthwestTemperatureDataset>
  },

  getCentralAsiaDesertGeoJSON: (
    mode: 'countries' | 'urban-polygons' | 'urban-points' = 'urban-points',
    bbox?: [number, number, number, number]
  ) => {
    return api.get<CentralAsiaDesertGeoJSONResponse>('/api/geodata/central-asia-desert', {
      params: {
        mode,
        ...(bbox ? { bbox: serializeBBox(bbox) } : {})
      }
    }) as unknown as Promise<CentralAsiaDesertGeoJSONResponse>
  },

  getBadalingImageryDataset: () => {
    return api.get<BadalingImageryDataset>('/api/geodata/badaling-imagery') as unknown as Promise<BadalingImageryDataset>
  },

  getBadalingImageryRasterUrl: (level: number, tileId: string) => {
    return `${API_BASE_URL}/api/geodata/badaling-imagery-raster/${level}/${tileId}`
  },

  getHepingjieImageryDataset: () => {
    return api.get<BadalingImageryDataset>('/api/geodata/hepingjie-imagery') as unknown as Promise<BadalingImageryDataset>
  },

  getHepingjieImageryRasterUrl: (level: number, tileId: string) => {
    return `${API_BASE_URL}/api/geodata/hepingjie-imagery-raster/${level}/${tileId}`
  },

  getForestCarbonRasterUrl: (metric: 'AGBC' | 'BGBC', year: number) => {
    return `${API_BASE_URL}/api/geodata/forest-carbon-raster/${metric}/${year}`
  },

  getLocalRasterPreviewUrl: (id: string) => {
    return `${API_BASE_URL}/api/geodata/local-raster-preview/${id}`
  },

  fetchLocalRasterPreviewBlob: async (id: string) => {
    const response = await downloadApi.get(`/api/geodata/local-raster-preview/${id}`, {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  getLocalRasterFileUrl: (id: string) => {
    return `${API_BASE_URL}/api/geodata/local-raster-download/${id}`
  },

  downloadLocalRasterOverlay: async (id: string) => {
    const response = await downloadApi.get(`/api/geodata/local-raster-download/${id}`, {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadHeiheDataset: async () => {
    const response = await downloadApi.get('/api/download/heihe', {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadHeiheGrasslandDataset: async () => {
    const response = await downloadApi.get('/api/download/heihe-grassland', {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadForestCarbonRaster: async (metric: 'AGBC' | 'BGBC', year: number) => {
    const response = await downloadApi.get(`/api/download/forest-carbon/${metric}/${year}`, {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadSouthwestTemperatureDataset: async () => {
    const response = await downloadApi.get('/api/download/southwest-temperature', {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadCentralAsiaDesertDataset: async () => {
    const response = await downloadApi.get('/api/download/central-asia-desert', {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadBadalingImageryDataset: async () => {
    const response = await downloadApi.get('/api/download/badaling-imagery', {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadHepingjieImageryDataset: async () => {
    const response = await downloadApi.get('/api/download/hepingjie-imagery', {
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  fetchPreviewBlob: async (id: number, options: PreviewBlobOptions = {}) => {
    const response = await downloadApi.get(`/api/geodata/preview/${id}`, {
      params: options.fullSize ? { full_size: 'true' } : undefined,
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  getNetCDFSlice: (id: number, variable: string, time_index: number = 0, depth_index: number = 0) => {
    return api.get<any>(`/api/geodata/netcdf/${id}/slice`, {
      params: { variable, time_index, depth_index }
    }) as unknown as Promise<any>
  },

  download: async (id: number, preview: boolean = false) => {
    const params = preview ? { preview: 'true' } : {}
    const response = await downloadApi.get(`/api/geodata/download/${id}`, {
      params,
      responseType: 'blob'
    })
    return response as unknown as Blob
  },

  downloadBatch: async (ids: number[]) => {
    const response = await downloadApi.post(
      '/api/geodata/download-batch',
      ids,
      { responseType: 'blob' }
    )
    return response as unknown as Blob
  },

  getStats: () => {
    return api.get<any>('/api/geodata/stats') as unknown as Promise<any>
  },

  getSummary: () => {
    return api.get<any>('/api/geodata/summary') as unknown as Promise<any>
  }
}
