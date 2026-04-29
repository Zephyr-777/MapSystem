export interface GeoDataItem {
  id: number;
  name: string;
  type?: string;
  sub_type?: string;
  file_path?: string;
  image_path?: string;
  uploadTime: string;
  extent?: [number, number, number, number]; // [minX, minY, maxX, maxY]
  srid?: number; // EPSG code (e.g., 3857 or 4326)
  center_x?: number;
  center_y?: number;
  distance?: number;
  lithology?: string;
  description?: string;
  asset_family?: string;
  render_mode?: string;
  overlay_supported?: boolean;
  index_point_enabled?: boolean;
  downloadable?: boolean;
  overlay_id?: string;
  source?: string;
  site_key?: string;
  site_name?: string;
  reports?: Array<{ title: string; url: string }>;
  metadata?: any; // NetCDF or other metadata
  dataset_id?: string;
  time_range?: string;
  record_count?: number;
  device_name?: string;
  download_url?: string;
  avg_soil_respiration_rate?: number;
  min_soil_respiration_rate?: number;
  max_soil_respiration_rate?: number;
  bbox?: [number, number, number, number];
  ring_code?: string;
  observed_at?: string;
  soil_respiration_rate?: number;
  linear_flux?: number;
  fit_status?: string;
  source_file_name?: string;
  location_precision?: string;
  metric?: string;
  year?: number;
  unit?: string;
}

export interface LayerConfig {
  [key: string]: {
    visible: boolean;
    opacity: number;
    name: string;
  };
}

export interface MapOptions {
  target: HTMLElement;
  center?: [number, number];
  zoom?: number;
  maxZoom?: number;
}

export interface SearchResult extends GeoDataItem {}

export type BaseMapType = 'vector' | 'satellite';
