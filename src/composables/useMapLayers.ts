import { ref, shallowRef, watch } from 'vue';
import TileLayer from 'ol/layer/Tile';
import ImageLayer from 'ol/layer/Image';
import WebGLTileLayer from 'ol/layer/WebGLTile';
import type { Style as WebGLTileStyle } from 'ol/layer/WebGLTile';
import VectorLayer from 'ol/layer/Vector';
import HeatmapLayer from 'ol/layer/Heatmap';
import XYZ from 'ol/source/XYZ';
import ImageStatic from 'ol/source/ImageStatic';
import GeoTIFF from 'ol/source/GeoTIFF';
import OSM from 'ol/source/OSM';
import VectorSource from 'ol/source/Vector';
import Cluster from 'ol/source/Cluster';
import { Style, Icon, Text, Fill, Stroke, Circle as CircleStyle } from 'ol/style';
import type BaseLayer from 'ol/layer/Base';
import useMapCore from './useMapCore';
import { ElMessage } from 'element-plus';

// Constants
const TIANDITU_TK = "ba13e30aae52239f8056f1c7421cae7c";
const AMAP_ICON_SVG = `<svg t="1738400000000" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4267" width="32" height="32"><path d="M512 0C305.006 0 137.448 167.558 137.448 374.552c0 197.394 280.914 563.31 374.552 649.448 93.638-86.138 374.552-452.054 374.552-649.448C886.552 167.558 718.994 0 512 0z m0 561.828c-103.448 0-187.276-83.828-187.276-187.276s83.828-187.276 187.276-187.276 187.276 83.828 187.276 187.276-83.828 187.276-187.276 187.276z" p-id="4268" fill="#409EFF"></path></svg>`;
const AMAP_ICON_SRC = 'data:image/svg+xml;base64,' + btoa(AMAP_ICON_SVG);

const RED_ICON_SVG = `<svg t="1738400000000" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4267" width="32" height="32"><path d="M512 0C305.006 0 137.448 167.558 137.448 374.552c0 197.394 280.914 563.31 374.552 649.448 93.638-86.138 374.552-452.054 374.552-649.448C886.552 167.558 718.994 0 512 0z m0 561.828c-103.448 0-187.276-83.828-187.276-187.276s83.828-187.276 187.276-187.276 187.276 83.828 187.276 187.276-83.828 187.276-187.276 187.276z" p-id="4268" fill="#F56C6C"></path></svg>`;
const RED_ICON_SRC = 'data:image/svg+xml;base64,' + btoa(RED_ICON_SVG);

const layers = shallowRef<BaseLayer[]>([]);
const activeLayerKeys = ref<string[]>([]);
const clusterStyleCache = new Map<number, Style>();
const tdtErrorCount = ref(0);
const isFallbackActive = ref(false);

export default function useMapLayers() {
  const { getMap } = useMapCore();

  const getLayerById = (id: string) => layers.value.find((layer) => layer.get('id') === id);

  const clearLayers = () => {
    const map = getMap();
    if (map) {
      layers.value.forEach(layer => map.removeLayer(layer));
    }
    layers.value = [];
    clusterStyleCache.clear();
    tdtErrorCount.value = 0;
    isFallbackActive.value = false;
  };

  const removeLayer = (id: string) => {
    const map = getMap();
    const index = layers.value.findIndex(l => l.get('id') === id);
    if (index > -1) {
      const layer = layers.value[index];
      if (map) {
        map.removeLayer(layer);
      }
      const newLayers = [...layers.value];
      newLayers.splice(index, 1);
      layers.value = newLayers;
    }
  };

  const addTDTLayer = (type: 'vec' | 'img' | 'ter' | 'cva' | 'cia', token: string = TIANDITU_TK): TileLayer<XYZ> => {
    const id = `tdt-${type}`;
    const existingLayer = getLayerById(id);
    if (existingLayer) {
        return existingLayer as TileLayer<XYZ>;
    }

    console.log(`Adding Tianditu layer: ${type}`);
    const source = new XYZ({
      url: `https://t{0-7}.tianditu.gov.cn/${type}_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${type}&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${token}`,
      crossOrigin: "anonymous",
    });

    source.on('tileloaderror', (_event) => {
      // Simple error counting logic
      if (!isFallbackActive.value) {
          tdtErrorCount.value++;
          if (tdtErrorCount.value > 10) {
              console.warn('Too many Tianditu errors, switching to OSM fallback');
              isFallbackActive.value = true;
              ElMessage.warning('天地图加载异常，已自动切换为备用地图源');
              
              // Switch active layers
              const currentKeys = activeLayerKeys.value.filter(k => !k.startsWith('tdt-'));
              if (!currentKeys.includes('osm')) {
                  currentKeys.push('osm');
              }
              activeLayerKeys.value = currentKeys;
          }
      }
    });

    const layer = new TileLayer({
      source: source,
      zIndex: type.includes('c') ? 1 : 0,
      visible: true, // Default to true, visibility controlled by add/remove or activeLayerKeys
      preload: 2,
      className: (type === 'vec' || type === 'ter') ? 'ol-layer-invertible' : undefined,
    });
    
    layer.set('id', id);
    layer.set('managedByActiveKeys', true);
    
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addOSMLayer = (): TileLayer<OSM> => {
    const existingLayer = getLayerById('osm');
    if (existingLayer) {
      return existingLayer as TileLayer<OSM>;
    }

    console.log('Adding OpenStreetMap layer as fallback');
    const layer = new TileLayer({
      source: new OSM({
        crossOrigin: 'anonymous',
      }),
      zIndex: -1,
      visible: activeLayerKeys.value.includes('osm'),
      preload: 2,
      className: 'ol-layer-invertible',
    });
    layer.set('id', 'osm');
    layer.set('managedByActiveKeys', true);
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addEsriSatelliteLayer = (): TileLayer<XYZ> => {
    const existingLayer = getLayerById('esri-sat');
    if (existingLayer) {
      return existingLayer as TileLayer<XYZ>;
    }

    console.log('Adding Esri World Imagery layer');
    const layer = new TileLayer({
      source: new XYZ({
        url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        crossOrigin: 'anonymous'
      }),
      zIndex: -1,
      visible: activeLayerKeys.value.includes('esri-sat'),
    });
    layer.set('id', 'esri-sat');
    layer.set('managedByActiveKeys', true);
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addNavigationLayer = (source: VectorSource): VectorLayer<VectorSource> => {
    const layer = new VectorLayer({
      source: source,
      zIndex: 1003,
      renderBuffer: 200,
      updateWhileAnimating: false,
      style: (feature) => {
        const name = feature.get('name');
        const isRed = feature.get('isRed');
        return new Style({
          image: new Icon({
            src: isRed ? RED_ICON_SRC : AMAP_ICON_SRC,
            scale: 1.1,
            anchor: [0.5, 1],
          }),
          text: name ? new Text({
            text: String(name),
            font: '12px sans-serif',
            offsetY: 15,
            fill: new Fill({ color: '#333' }),
            stroke: new Stroke({ color: '#fff', width: 2 })
          }) : undefined
        });
      },
    });
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addClusterLayer = (source: VectorSource, distance: number = 65, id: string = 'cluster-layer'): VectorLayer<VectorSource> => {
    const clusterSource = new Cluster({
      distance: distance,
      minDistance: 20,
      source: source,
    });

    const layer = new VectorLayer({
      source: clusterSource,
      zIndex: 1002,
      renderBuffer: 200,
      updateWhileAnimating: false,
      visible: true,
      style: (feature) => {
        const features = feature.get("features");
        const size = features ? features.length : 0;
        
        if (size === 1) {
           // Reuse Icon object if possible, but here we create new Style to attach Text
           // Ideally we should cache this too if name repeats, but for now we optimize at least the logic
           return new Style({
            image: new Icon({
              src: AMAP_ICON_SRC,
              scale: 1.0,
              anchor: [0.5, 1],
            }),
            text: new Text({
              text: features[0].get('name'),
              font: '12px sans-serif',
              offsetY: 15,
              fill: new Fill({ color: '#333' }),
              stroke: new Stroke({ color: '#fff', width: 2 })
            })
          });
        }

        const cached = clusterStyleCache.get(size);
        if (cached) return cached;

        // Enhanced Cluster Style
        const radius = Math.min(30, 15 + size * 0.5);
        const style = new Style({
          image: new CircleStyle({
            radius: radius,
            fill: new Fill({ color: "rgba(0, 113, 227, 0.8)" }), // Always light theme color
            stroke: new Stroke({
                color: "rgba(255, 255, 255, 0.8)",
                width: 3
            }),
          }),
          text: new Text({
            text: size.toString(),
            font: 'bold 13px "SF Pro Text", sans-serif',
            fill: new Fill({ color: "#fff" }),
            offsetY: 1, // Visual center correction
          }),
        });
        clusterStyleCache.set(size, style);
        return style;
      },
    });

    layer.set('id', id);
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addHeatmapLayer = (
    source: VectorSource,
    id: string = 'heatmap-layer',
    blur: number = 15,
    radius: number = 8
  ): HeatmapLayer => {
    const layer = new HeatmapLayer({
      source: source,
      blur: blur,
      radius: radius,
      weight: (feature) => {
        const val = feature.get('value');
        return val !== undefined ? Math.min(Math.max(val, 0), 1) : 0; // Normalize 0-1
      },
      zIndex: 1001,
    });
    
    layer.set('id', id);
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addStaticImageOverlayLayer = (options: {
    id: string
    url: string
    extent: [number, number, number, number]
    opacity?: number
    minZoom?: number
    zIndex?: number
    visible?: boolean
  }): ImageLayer<ImageStatic> => {
    const existingLayer = getLayerById(options.id);
    if (existingLayer) {
      const imageLayer = existingLayer as ImageLayer<ImageStatic>;
      imageLayer.setSource(new ImageStatic({
        url: options.url,
        imageExtent: options.extent,
        projection: 'EPSG:3857',
        crossOrigin: 'anonymous',
      }));
      imageLayer.setOpacity(options.opacity ?? 0.75);
      imageLayer.setMinZoom(options.minZoom ?? 8);
      imageLayer.setVisible(options.visible ?? true);
      imageLayer.setZIndex(options.zIndex ?? 900);
      return imageLayer;
    }

    const layer = new ImageLayer({
      source: new ImageStatic({
        url: options.url,
        imageExtent: options.extent,
        projection: 'EPSG:3857',
        crossOrigin: 'anonymous',
      }),
      zIndex: options.zIndex ?? 900,
      opacity: options.opacity ?? 0.75,
      visible: options.visible ?? true,
      minZoom: options.minZoom ?? 8,
    });

    layer.set('id', options.id);
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  const addGeoTiffOverlayLayer = (options: {
    id: string
    url: string
    opacity?: number
    minZoom?: number
    maxZoom?: number
    zIndex?: number
    visible?: boolean
    nodata?: number
    bandCount?: number
    rasterMin?: number
    rasterMax?: number
    colorRamp?: 'terrain' | 'carbon'
    token?: string | null
    extent?: [number, number, number, number]
  }): WebGLTileLayer => {
    const effectiveMinZoom = (options.minZoom ?? 3) - 0.01;
    const isSingleBand = (options.bandCount ?? 1) === 1;
    const colorRamp = options.colorRamp ?? 'terrain';
    const sourceInfo = {
      url: options.url,
      ...(typeof options.nodata === 'number' ? { nodata: options.nodata } : {}),
      ...(typeof options.rasterMin === 'number' ? { min: options.rasterMin } : {}),
      ...(typeof options.rasterMax === 'number' ? { max: options.rasterMax } : {}),
    };
    const singleBandStyle: WebGLTileStyle | undefined = isSingleBand
      ? {
          color: [
            'interpolate',
            ['linear'],
            ['band', 1],
            0,
            colorRamp === 'carbon' ? 'rgba(255,255,255,0)' : '#233b2d',
            0.28,
            colorRamp === 'carbon' ? '#d7e9b1' : '#4f6f38',
            0.52,
            colorRamp === 'carbon' ? '#82b35c' : '#b59b54',
            0.74,
            colorRamp === 'carbon' ? '#2f7a44' : '#e2d7bd',
            1,
            colorRamp === 'carbon' ? '#08351e' : '#ffffff',
          ],
          contrast: colorRamp === 'carbon' ? 0.08 : 0.12,
          saturation: colorRamp === 'carbon' ? 0.25 : 0.15,
        }
      : undefined;
    const source = new GeoTIFF({
      sources: [sourceInfo],
      sourceOptions: {
        headers: options.token ? { Authorization: `Bearer ${options.token}` } : undefined,
        maxRanges: 1,
      },
      convertToRGB: 'auto',
      normalize: true,
      transition: 0,
      wrapX: false,
    });

    const existingLayer = getLayerById(options.id);
    if (existingLayer) {
      const tileLayer = existingLayer as WebGLTileLayer;
      tileLayer.setSource(source as any);
      tileLayer.setOpacity(options.opacity ?? 0.75);
      tileLayer.setMinZoom(effectiveMinZoom);
      tileLayer.setMaxZoom(options.maxZoom ?? Infinity);
      tileLayer.setVisible(options.visible ?? true);
      tileLayer.setZIndex(options.zIndex ?? 910);
      tileLayer.setExtent(options.extent);
      if (singleBandStyle) {
        tileLayer.setStyle(singleBandStyle);
      }
      return tileLayer;
    }

    const layer = new WebGLTileLayer({
      source: source as any,
      zIndex: options.zIndex ?? 910,
      opacity: options.opacity ?? 0.75,
      visible: options.visible ?? true,
      minZoom: effectiveMinZoom,
      maxZoom: options.maxZoom ?? Infinity,
      extent: options.extent,
      style: singleBandStyle,
      preload: 1,
    });

    layer.set('id', options.id);
    layer.set('sourceKind', 'geotiff');
    const map = getMap();
    if (map) {
      map.addLayer(layer);
      layers.value = [...layers.value, layer];
    }
    return layer;
  };

  // Watch activeLayerKeys to toggle visibility
  watch(activeLayerKeys, (keys) => {
    layers.value.forEach(layer => {
      const id = layer.get('id');
      if (id && layer.get('managedByActiveKeys')) {
        layer.setVisible(keys.includes(id));
      }
    });
  }, { deep: true });

  return {
    layers,
    activeLayerKeys,
    addTDTLayer,
    addOSMLayer,
    addEsriSatelliteLayer,
    addNavigationLayer,
    addClusterLayer,
    addHeatmapLayer,
    addStaticImageOverlayLayer,
    addGeoTiffOverlayLayer,
    removeLayer,
    clearLayers,
    isFallbackActive,
  };
}
