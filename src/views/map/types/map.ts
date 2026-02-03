export interface GeoDataItem {
  id: number;
  name: string;
  type: string;
  uploadTime: string;
  extent?: [number, number, number, number]; // [minX, minY, maxX, maxY]
  srid?: number; // EPSG code (e.g., 3857 or 4326)
  center_x?: number;
  center_y?: number;
  lithology?: string;
  description?: string;
  reports?: Array<{ title: string; url: string }>;
}

export interface LayerConfigItem {
  visible: boolean;
  opacity: number;
  name: string;
}

export interface LayerConfig {
  [key: string]: LayerConfigItem;
}

export interface MapOptions {
  target: HTMLElement;
  center?: [number, number];
  zoom?: number;
  maxZoom?: number;
}

export interface SearchResult extends GeoDataItem {}

export type BaseMapType = 'vector' | 'satellite';
