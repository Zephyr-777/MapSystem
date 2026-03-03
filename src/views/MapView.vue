<template>
  <div class="map-view-container">
    <ErrorBoundary>
      <MapContainer ref="mapContainerRef" :map-instance="map">
        <!-- Cesium 3D Container (Overlay) -->
        <CesiumContainer 
          v-if="mapReady"
          :visible="is3DActive"
          :view-state="viewState"
          :features="rawFeatures"
        />

        <!-- Swipe Control -->
        <div v-if="isSwipeActive" class="swipe-control-container">
            <input 
              type="range" 
              min="0" 
              max="100" 
              v-model="swipeValue" 
              class="swipe-slider"
              @input="map?.render()"
            />
        </div>

        <!-- Mouse Tooltip Overlay Content -->
        <div ref="mouseTooltipRef" class="mouse-tooltip" v-show="tooltipContent">
          {{ tooltipContent }}
        </div>
        
        <!-- Result Popover Overlay (Only for non-feature clicks if needed, or simple POIs) -->
        <div ref="popupRef" class="map-popup-overlay">
          <div v-if="popupInfo" class="popup-content glass-panel">
            <div class="popup-header">
              <span class="popup-title">{{ popupInfo.name }}</span>
              <el-button link class="close-btn" @click="closePopup">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <div class="popup-body">
              <div v-if="popupInfo.address" class="popup-address">
                <el-icon><LocationInformation /></el-icon>
                {{ popupInfo.address }}
              </div>
              <div class="popup-actions">
                <el-button type="primary" size="small" round @click="handleSetCenter(popupInfo)">
                  设为中心
                </el-button>
                <el-button size="small" round @click="handleDetail(popupInfo)">
                  查看详情
                </el-button>
              </div>
            </div>
            <!-- Ripple Effect -->
            <div class="ripple-container">
               <div class="ripple"></div>
            </div>
          </div>
        </div>

        <!-- Bottom Right Controls: Zoom & Location -->
        <div class="bottom-right-controls">
          <el-tooltip content="定位" placement="left">
            <button 
              class="nav-btn"
              :class="{ 'loading': locating }"
              @click="handleLocation" 
            >
              <el-icon :class="{ 'is-loading': locating }"><Location /></el-icon>
            </button>
          </el-tooltip>

          <div class="map-zoom-control-vertical">
            <el-icon class="zoom-btn" @click="zoomIn"><Plus /></el-icon>
            <el-slider 
              v-model="zoomLevel" 
              vertical 
              :min="3" 
              :max="18" 
              height="100px"
              :show-tooltip="false"
              @input="handleZoomChange"
            />
            <el-icon class="zoom-btn" @click="zoomOut"><Minus /></el-icon>
          </div>

          <!-- 退出登录按钮 -->
          <el-tooltip content="退出登录" placement="left">
            <button 
              class="nav-btn logout-btn"
              @click="handleLogout" 
            >
              <el-icon><SwitchButton /></el-icon>
            </button>
          </el-tooltip>
        </div>

        <!-- Bottom Dock -->
        <BottomDock 
          :active-tool="activeTool"
          @home="handleHome"
          @toggle-layers="toggleLayers"
          @toggle-measure="toggleMeasureTool"
          @toggle-selection="toggleSelectionTool"
          @toggle-buffer="toggleBufferTool"
          @toggle-identify="toggleIdentifyTool"
          @open-gallery="$router.push('/gallery')"
          @share-view="handleShareView"
          @upload="showUploadDialog = true"
        />

      </MapContainer>

      <div v-if="!mapReady && !initError" class="loading-overlay">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span style="margin-left: 10px">正在初始化地图...</span>
      </div>

      <div v-if="initError" class="loading-overlay error-state">
        <el-empty description="地图加载失败" :image-size="100">
          <template #description>
            <p class="error-text">{{ errorMessage }}</p>
            <el-button type="primary" :icon="RefreshRight" @click="handleRetry">重试</el-button>
          </template>
        </el-empty>
      </div>

      <div v-if="mapReady">
        <div class="top-search-container">
          <SearchBox 
            :fetch-suggestions="handleSearchSuggestions"
            @select-result="handleSelectResult"
            @upload="showUploadDialog = true"
          />
        </div>

        <div class="top-right-controls">
          <el-tooltip content="3D 预览" placement="left">
            <button 
              class="control-btn" 
              :class="{ active: is3DActive }"
              @click="toggle3D"
            >
              <el-icon><Monitor /></el-icon>
            </button>
          </el-tooltip>
        </div>

        <Transition name="fade-slide">
          <LayerControl 
            v-if="showLayerPanel"
            :visible="showLayerPanel"
            :layer-config="layerConfig"
            @close="showLayerPanel = false"
            @update:visibility="handleLayerVisibilityChange"
            @update:opacity="handleLayerOpacityChange"
          />
        </Transition>

        <Transition name="slide-right">
          <InfoPanel 
            v-if="sidePanelVisible"
            :visible="sidePanelVisible"
            :title="sidePanelTitle"
            :feature="currentFeature"
            :is-multi-selection="selectedItems.length > 1"
            :selected-items="selectedItems"
            @close="closeSidePanel"
            @download="handleDownload"
            @locate="locateItem"
            @visualize-nc="handleVisualizeNetCDF"
          />
        </Transition>

        <Transition name="fade-slide">
          <StatsPanel />
        </Transition>
        
      </div>
      
      <!-- Upload Dialog -->
      <UploadDialog 
         v-model="showUploadDialog" 
         @upload-success="handleUploadSuccess"
      />
    </ErrorBoundary>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, shallowRef, nextTick, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { geoDataApi, type GeoDataItem } from '@/api/geodata';
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus';
import { Location, Loading, Plus, Minus, RefreshRight, Close, LocationInformation, SwitchButton, Monitor } from '@element-plus/icons-vue';
import type Map from 'ol/Map';
import type { LayerConfig } from '@/views/map/types/map';
import useMapCore from '@/composables/useMapCore';
import useMapLayers from '@/composables/useMapLayers';
import useMapInteractions from '@/composables/useMapInteractions';
import VectorSource from 'ol/source/Vector';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj';
import { Style, Fill, Stroke, Circle as CircleStyle, RegularShape } from 'ol/style';
import VectorLayer from 'ol/layer/Vector';
import Overlay from 'ol/Overlay';
import { Circle as CircleGeom } from 'ol/geom';
import { getRenderPixel } from 'ol/render';
import TileLayer from 'ol/layer/Tile';
import HeatmapLayer from 'ol/layer/Heatmap';

// Components
import ErrorBoundary from '@/components/ErrorBoundary.vue';
import MapContainer from '@/views/map/components/MapContainer.vue';
import SearchBox from '@/views/map/components/SearchBox.vue';
import BottomDock from '@/components/layout/BottomDock.vue';
import LayerControl from '@/views/map/components/LayerControl.vue';
import InfoPanel from '@/views/map/components/InfoPanel.vue';
import StatsPanel from '@/views/map/components/StatsPanel.vue';
import UploadDialog from '@/views/map/components/UploadDialog.vue';
import CesiumContainer from '@/views/map/components/CesiumContainer.vue';

import { getDistance } from 'ol/sphere';

// Composables
const { initMap, mapReady } = useMapCore();
const { addOSMLayer, addEsriSatelliteLayer, addTDTLayer, addNavigationLayer, addClusterLayer, addHeatmapLayer, removeLayer, activeLayerKeys, clearLayers, layers } = useMapLayers();
const { initInteractions, toggleDragBox, isDragBoxActive, selectedExtent, clearSelection: clearInteractions, initTooltip, flyTo, removeInteractions, selectedItems, startDrawing, stopDrawing } = useMapInteractions();

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const map = shallowRef<Map | null>(null);
const mapContainerRef = ref<any>(null);

// State
const activeTool = ref<string>('');
const initError = ref(false);
const errorMessage = ref('');
const showLayerPanel = ref(false);
const sidePanelVisible = ref(false);
const showAttributeDashboard = ref(true); // Now controlled by StatsPanel trigger
const currentFeature = ref<GeoDataItem | null>(null);
const showUploadDialog = ref(false);
const locating = ref(false);
const isNearbyActive = ref(false);
const isSwipeActive = ref(false);
const swipeValue = ref(50);
const mouseTooltipRef = ref<HTMLElement | null>(null);

// 3D Mode State
const is3DActive = ref(false);
const rawFeatures = ref<any[]>([]);
const viewState = ref({
    center: [116.3974, 39.9093] as [number, number],
    zoom: 10,
    extent: undefined as [number, number, number, number] | undefined
});

// Tool toggle handlers
const toggleLayers = () => {
  activeTool.value = activeTool.value === 'layers' ? '' : 'layers';
  showLayerPanel.value = !showLayerPanel.value;
};

const toggleMeasureTool = () => {
  activeTool.value = activeTool.value === 'measure' ? '' : 'measure';
  ElMessage.info('测量工具开发中');
};

const toggleSelectionTool = () => {
  if (activeTool.value === 'selection') {
    activeTool.value = '';
    if (isDragBoxActive.value) toggleDragBox();
  } else {
    activeTool.value = 'selection';
    if (!isDragBoxActive.value) toggleDragBox();
    isNearbyActive.value = false;
  }
};

const toggleBufferTool = () => {
  if (activeTool.value === 'buffer') {
    activeTool.value = '';
    isNearbyActive.value = false;
    stopDrawing();
    bufferSource.clear();
    selectedItems.value = [];
    sidePanelVisible.value = false;
  } else {
    activeTool.value = 'buffer';
    isNearbyActive.value = true;
    if (isDragBoxActive.value) toggleDragBox();
    
    ElMessage.info('请在地图上拖拽绘制圆形区域进行分析');
    startDrawing('Circle', handleBufferDraw);
  }
};

const handleBufferDraw = async (geometry: any) => {
    // geometry is Circle (in Web Mercator)
    const center = geometry.getCenter();
    const radius = geometry.getRadius(); // This is in projection units (meters-ish)
    
    // Convert center to LonLat
    const centerLonLat = toLonLat(center);
    
    // Calculate accurate radius in meters (Geodesic)
    // Get a point on the circumference
    // For Circle geometry in OL, it's defined by center and radius.
    // We can assume flat radius for small areas, but for accuracy:
    // Create a point at [center[0] + radius, center[1]] and measure distance?
    // Or just use the projection radius if the projection is meters (Web Mercator is meters but distorted).
    // Distortion factor at latitude phi is 1 / cos(phi).
    // So real distance = map distance * cos(phi).
    const lat = centerLonLat[1];
    const realRadius = radius * Math.cos(lat * Math.PI / 180);
    
    console.log(`Buffer Analysis: Center=[${centerLonLat}], Radius=${realRadius}m`);
    
    ElMessage.info(`正在分析周边 ${realRadius.toFixed(0)} 米范围数据...`);
    
    // Clear previous visual buffer (drawn by interaction)
    // The interaction draws on a temp layer. We might want to keep it or add to our bufferLayer.
    // Let's add it to our bufferLayer so we can control it.
    bufferSource.clear();
    const feature = new Feature(geometry);
    bufferSource.addFeature(feature);
    
    try {
        const res = await geoDataApi.bufferQuery(centerLonLat[0], centerLonLat[1], realRadius);
        const data = Array.isArray(res) ? res : (res as any).data || [];
        
        if (data.length > 0) {
            if (data.length === 1) {
                currentFeature.value = data[0];
                selectedItems.value = data;
            } else {
                currentFeature.value = null;
                selectedItems.value = data;
            }
            sidePanelVisible.value = true;
            // Highlight results
            highlightSource.clear();
            data.forEach((item: GeoDataItem) => {
                if (item.center_x && item.center_y) {
                    const c = toMapCoords([item.center_x, item.center_y], item.srid);
                    const f = new Feature(new Point(c));
                    highlightSource.addFeature(f);
                }
            });
            ElMessage.success(`发现 ${data.length} 个地质点位`);
        } else {
            ElMessage.info('缓冲区内无数据');
            selectedItems.value = [];
        }
    } catch (e) {
        console.error(e);
        ElMessage.error('缓冲区查询失败');
    }
};

const toggleIdentifyTool = () => {
  if (activeTool.value === 'identify') {
    activeTool.value = '';
    // Optional: Hide panel if closing tool? 
    // Usually, we want it to stay if a feature is selected, 
    // but the task says "only appear when clicking a geologic point".
  } else {
    activeTool.value = 'identify';
    isNearbyActive.value = false;
    if (isDragBoxActive.value) toggleDragBox();
    ElMessage.success('已开启属性识别，点击地图查看详情');
  }
};

const handleHome = () => {
  if (map.value) {
    map.value.getView().animate({
      center: fromLonLat([116.4074, 39.9042]),
      zoom: 10,
      duration: 1000
    });
  }
};

const handleShareView = async () => {
  if (!map.value) return;
  
  const view = map.value.getView();
  const center = view.getCenter();
  const zoom = view.getZoom();
  
  if (center && zoom) {
    const lonLat = toLonLat(center);
    // 保留更多小数位以确保精度
    const lon = lonLat[0].toFixed(6);
    const lat = lonLat[1].toFixed(6);
    const z = zoom.toFixed(2);
    
    // 构建包含当前视角的 URL
    const url = `${window.location.origin}${window.location.pathname}?x=${lon}&y=${lat}&z=${z}`;
    
    try {
      await navigator.clipboard.writeText(url);
      ElNotification({
        title: '分享成功',
        message: '视角链接已复制到剪贴板',
        type: 'success',
        duration: 3000,
        offset: 80,
      });
    } catch (err) {
      console.error('Failed to copy: ', err);
      ElNotification({
        title: '复制失败',
        message: '请手动复制浏览器地址栏链接',
        type: 'error',
        duration: 3000,
        offset: 80,
      });
    }
  }
};

const popupRef = ref<HTMLElement | null>(null);
const tooltipContent = ref('');
const currentBaseMap = ref<'vector' | 'satellite'>('vector');
const navigationSource = new VectorSource();
const geoPointSource = new VectorSource();
const zoomLevel = ref(10);
const popupInfo = ref<any>(null);
let popupOverlay: Overlay | null = null;

const closePopup = () => {
  popupInfo.value = null;
  if (popupOverlay) {
    popupOverlay.setPosition(undefined);
  }
};

const handleSetCenter = (info: any) => {
  if (info.location) {
    const coords = fromLonLat([info.location.lon, info.location.lat]) as [number, number];
    if (map.value) {
      map.value.getView().animate({
        center: coords,
        zoom: 14,
        duration: 1000
      });
    }
  }
  closePopup();
};

const handleDetail = (info: any) => {
  // Mock detail or simple info
  ElMessage.info(`查看详情: ${info.name}`);
};

const sidePanelTitle = computed(() => {
  if (isNearbyActive.value) return '周边分析结果';
  if (selectedItems.value.length > 1) return '批量操作';
  return currentFeature.value?.name || '详细信息';
});

// Highlight Layer
const highlightSource = new VectorSource();
const highlightLayer = new VectorLayer({
  source: highlightSource,
  zIndex: 9999, // Ensure it's on top
  style: new Style({
    image: new CircleStyle({
      radius: 6,
      fill: new Fill({ color: '#FFFF00' }), // Yellow highlight
      stroke: new Stroke({ color: '#FF0000', width: 2 })
    }),
    zIndex: Infinity
  })
});

// Buffer Layer for Nearby Analysis
const bufferSource = new VectorSource();
const bufferLayer = new VectorLayer({
  source: bufferSource,
  zIndex: 999,
  style: new Style({
    fill: new Fill({
      color: 'rgba(64, 158, 255, 0.2)'
    }),
    stroke: new Stroke({
      color: '#409EFF',
      width: 2,
      lineDash: [10, 10]
    })
  })
});

const layerConfig = ref<LayerConfig>({
  faults: { visible: true, opacity: 80, name: '矢量断裂带' },
  boreholes: { visible: true, opacity: 90, name: '钻孔分布点' },
  raster: { visible: true, opacity: 80, name: '栅格影像' }
});

const toMapCoords = (coord: [number, number], srid?: number) => {
  if (srid === 3857) {
    return coord;
  }
  return fromLonLat(coord) as [number, number];
};

const setNavigationMarker = (coord: [number, number], name?: string, isRed: boolean = false) => {
  navigationSource.clear();
  const feature = new Feature({
    geometry: new Point(coord),
    name: name || '导航点',
    isRed: isRed
  });
  navigationSource.addFeature(feature);
};

const handleRetry = () => {
  initError.value = false;
  errorMessage.value = '';
  window.location.reload();
};

const handleLogout = () => {
  ElMessageBox.confirm(
    '确定要退出登录吗？退出后将清除所有本地缓存并跳转至登录页。',
    '退出确认',
    {
      confirmButtonText: '确认退出',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'logout-confirm-box', // 可自定义样式
    }
  )
    .then(() => {
      try {
        authStore.logout();
        ElMessage.success('已安全退出登录');
      } catch (error) {
        console.error('Logout error:', error);
        ElMessage.error('退出过程发生异常，正在强制跳转');
        // 强制清理
        localStorage.clear();
        router.push('/login');
      }
    })
    .catch(() => {
      // User cancelled
    });
};

const toggle3D = () => {
    if (!map.value) return;
    
    is3DActive.value = !is3DActive.value;
    
    if (is3DActive.value) {
        // Sync OL to Cesium
        const view = map.value.getView();
        const center = toLonLat(view.getCenter()!);
        const zoom = view.getZoom() || 10;
        const extent = view.calculateExtent(map.value.getSize()!);
        const lonLatExtent = transformExtent(extent, 'EPSG:3857', 'EPSG:4326') as [number, number, number, number];
        
        viewState.value = {
            center: center as [number, number],
            zoom: zoom,
            extent: lonLatExtent
        };
        
        ElMessage.success('已切换至 3D 预览模式');
    } else {
        ElMessage.info('已回到 2D 地图模式');
    }
};

const toggleNearby = () => {
  if (isSwipeActive.value) {
      ElMessage.warning('请先关闭卷帘对比模式');
      return;
  }
  isNearbyActive.value = !isNearbyActive.value;
  if (!isNearbyActive.value) {
    bufferSource.clear();
    selectedItems.value = [];
    sidePanelVisible.value = false;
  } else {
    ElMessage.info('开启周边分析模式：请点击地图查看周边数据');
  }
};

const toggleSwipe = () => {
    if (isNearbyActive.value) {
        ElMessage.warning('请先关闭周边分析模式');
        return;
    }
    
    isSwipeActive.value = !isSwipeActive.value;
    
    if (isSwipeActive.value) {
        ElMessage.info('开启卷帘模式：左侧卫星影像，右侧矢量地图');
        enableSwipe();
    } else {
        disableSwipe();
    }
};

const enableSwipe = () => {
    // 1. Ensure both layers are present
    // Left: Satellite (Bottom), Right: Vector (Top)
    
    // Reset layers first to be clean
    // Actually we can just add them if missing
    addTDTLayer('img'); // Satellite
    addTDTLayer('cia'); // Labels
    addTDTLayer('vec'); // Vector
    addTDTLayer('cva'); // Labels
    
    // 2. Set Visibility and Z-Index
    // We want Vector on TOP to clip it
    const vecLayer = layers.value.find(l => l.get('id') === 'tdt-vec');
    const cvaLayer = layers.value.find(l => l.get('id') === 'tdt-cva');
    const imgLayer = layers.value.find(l => l.get('id') === 'tdt-img');
    const ciaLayer = layers.value.find(l => l.get('id') === 'tdt-cia');
    
    if (imgLayer) { imgLayer.setVisible(true); imgLayer.setZIndex(0); }
    if (ciaLayer) { ciaLayer.setVisible(true); ciaLayer.setZIndex(1); }
    
    // Vector layers on top, to be clipped
    if (vecLayer) { 
        vecLayer.setVisible(true); 
        vecLayer.setZIndex(10); 
        vecLayer.on('prerender' as any, swipePrerender);
        vecLayer.on('postrender' as any, swipePostrender);
    }
    if (cvaLayer) { 
        cvaLayer.setVisible(true); 
        cvaLayer.setZIndex(11); 
        cvaLayer.on('prerender' as any, swipePrerender);
        cvaLayer.on('postrender' as any, swipePostrender);
    }
    
    map.value?.render();
};

const disableSwipe = () => {
    // Remove listeners
    const vecLayer = layers.value.find(l => l.get('id') === 'tdt-vec');
    const cvaLayer = layers.value.find(l => l.get('id') === 'tdt-cva');
    
    if (vecLayer) {
        vecLayer.un('prerender' as any, swipePrerender);
        vecLayer.un('postrender' as any, swipePostrender);
    }
    if (cvaLayer) {
        cvaLayer.un('prerender' as any, swipePrerender);
        cvaLayer.un('postrender' as any, swipePostrender);
    }
    
    // Restore base map state
    updateBaseMapLayers();
    map.value?.render();
};

const swipePrerender = (event: any) => {
    const ctx = event.context;
    const mapSize = map.value?.getSize();
    if (!mapSize) return;
    
    const width = mapSize[0] * (swipeValue.value / 100);
    // Calculate pixel ratio for retina displays
    const pixelRatio = event.frameState.pixelRatio;
    
    ctx.save();
    ctx.beginPath();
    // Clip the right side (Vector)
    // Rect: x, y, w, h
    // We want to show Vector only on the RIGHT of the slider
    // So clip rectangle starts at width and goes to end
    ctx.rect(width * pixelRatio, 0, (mapSize[0] - width) * pixelRatio, mapSize[1] * pixelRatio);
    ctx.clip();
};

const swipePostrender = (event: any) => {
    const ctx = event.context;
    ctx.restore();
};

const handleUploadSuccess = async (asset: any) => {
    // Reload data
    await loadGeoData(geoPointSource);
    
    // Fit to extent if available
    if (asset.extent && Array.isArray(asset.extent) && asset.extent.length === 4) {
        // Assume extent is [minX, minY, maxX, maxY] in 4326 (LonLat)
        const extent = asset.extent;
        // Transform extent corners to Map Projection (Web Mercator)
        // Note: fromLonLat takes [lon, lat]
        const min = fromLonLat([extent[0], extent[1]]);
        const max = fromLonLat([extent[2], extent[3]]);
        const mapExtent = [min[0], min[1], max[0], max[1]];
        
        map.value?.getView().fit(mapExtent, { padding: [100, 100, 100, 100], duration: 1000 });
        ElMessage.success(`已缩放到新数据范围: ${asset.name}`);
    } else if (asset.center_x && asset.center_y) {
        const coords = toMapCoords([asset.center_x, asset.center_y], asset.srid || 4326);
        flyTo(coords);
        setNavigationMarker(coords, asset.name);
        ElMessage.success(`已跳转到新数据: ${asset.name}`);
    }
};


const handleVisualizeNetCDF = (data: any) => {
    // 1. Remove existing heatmap layer
    const existing = layers.value.find(l => l.get('id') === 'nc-heatmap');
    if (existing) {
        map.value?.removeLayer(existing);
        layers.value = layers.value.filter(l => l !== existing);
    }
    
    if (!data || !data.lons || !data.lats || !data.values) {
        ElMessage.warning('数据格式无效');
        return;
    }
    
    // 2. Create Vector Source with Points
    const source = new VectorSource();
    const features: Feature[] = [];
    
    const lons = data.lons;
    const lats = data.lats;
    const values = data.values;
    const minVal = data.min;
    const maxVal = data.max;
    const range = maxVal - minVal;
    
    for (let i = 0; i < lats.length; i++) {
        for (let j = 0; j < lons.length; j++) {
            const val = values[i][j];
            if (val !== null && val !== undefined) {
                const lon = lons[j];
                const lat = lats[i];
                
                const coords = toMapCoords([lon, lat], 4326);
                const feature = new Feature(new Point(coords));
                
                // Normalize value 0-1 for heatmap weight
                const weight = range === 0 ? 0.5 : (val - minVal) / range;
                feature.set('value', weight);
                feature.set('rawValue', val);
                
                features.push(feature);
            }
        }
    }
    
    source.addFeatures(features);
    
    // 3. Add Heatmap Layer
    addHeatmapLayer(source, 'nc-heatmap', 20, 10);
    
    // 4. Adjust View
    const extent = source.getExtent();
    map.value?.getView().fit(extent, { padding: [50, 50, 50, 50], duration: 1000 });
    
    ElMessage.success(`已渲染 ${data.variable} 热力图`);
};

// Init Map
onMounted(async () => {
  await nextTick();
  console.log('MapView mounted, starting initialization...');
  const container = mapContainerRef.value?.getMapElement();
  if (container) {
      try {
          console.log('Found map container, initializing OpenLayers...');
          const mapInstance = await initMap(container, {
              target: container,
              center: [116.3974, 39.9093],
              zoom: 10,
              maxZoom: 18
          });
          
          if (!mapInstance) {
              throw new Error('Map instance creation failed');
          }
          
          map.value = mapInstance;
          console.log('Map instance created and assigned');

          // Performance optimization: Disable animations during interaction
          mapInstance.on('movestart', () => {
            const target = mapInstance.getTargetElement();
            if (target) target.classList.add('map-moving');
          });
          mapInstance.on('moveend', () => {
            const target = mapInstance.getTargetElement();
            if (target) target.classList.remove('map-moving');
            // Sync Zoom Slider
            const zoom = mapInstance.getView().getZoom();
            if (zoom) zoomLevel.value = zoom;
            
            // Sync 3D View State
            if (is3DActive.value) {
                const center = mapInstance.getView().getCenter();
                if (center && zoom) {
                    const lonLat = toLonLat(center);
                    const extent = mapInstance.getView().calculateExtent(mapInstance.getSize());
                    const lonLatExtent = transformExtent(extent, 'EPSG:3857', 'EPSG:4326') as [number, number, number, number];
                    
                    viewState.value = {
                        center: lonLat as [number, number],
                        zoom: zoom,
                        extent: lonLatExtent
                    };
                }
            }
          });
          
          clearLayers();

          console.log('Initializing layers...');
          addOSMLayer();
          addEsriSatelliteLayer();
          // Initialize Tianditu layers
          addTDTLayer('vec');
          addTDTLayer('cva');
          addTDTLayer('img');
          addTDTLayer('cia');
          
          addNavigationLayer(navigationSource);
          updateBaseMapLayers();

          // Mock Data Layer (Cluster)
          addClusterLayer(geoPointSource, 60, 'boreholes');

          // Load Data
          console.log('Loading geo data...');
          await loadGeoData(geoPointSource);

          // Check Route Query for FlyTo or Initial View
          // Priority: 1. ID/Name (Gallery) 2. Lon/Lat/Z (Share)
          if (route.query.lat && route.query.lon) {
              const lat = parseFloat(route.query.lat as string);
              const lon = parseFloat(route.query.lon as string);
              // Support both 'zoom' (gallery) and 'z' (share)
              const zoomParam = route.query.zoom || route.query.z;
              const zoom = zoomParam ? parseFloat(zoomParam as string) : 14;
              
              if (!isNaN(lat) && !isNaN(lon)) {
                  console.log(`Auto positioning to query location: ${lon}, ${lat}, z=${zoom}`);
                  const coords = toMapCoords([lon, lat], 4326); // Assume query is WGS84
                  
                  // Delay slightly to ensure map is fully rendered
                  setTimeout(() => {
                      if (route.query.id) {
                          flyTo(coords, zoom);
                          const name = (route.query.name as string) || '目标位置';
                          setNavigationMarker(coords, name, true);
                          
                          const id = parseInt(route.query.id as string);
                          const feature = geoPointSource.getFeatures().find(f => f.get('id') === id);
                          if (feature) {
                              const props = feature.getProperties();
                              currentFeature.value = props as GeoDataItem;
                              sidePanelVisible.value = true;
                              
                              highlightSource.clear();
                              const clone = feature.clone();
                              highlightSource.addFeature(clone);
                          }
                          ElMessage.success(`已定位到: ${name}`);
                      } else {
                          // Share view logic: Direct setCenter for instant restore
                          mapInstance.getView().setCenter(coords);
                          mapInstance.getView().setZoom(zoom);
                          ElMessage.success('已恢复分享视图');
                      }
                  }, 500);
              }
          }

          // Init Interactions
          console.log('Initializing interactions...');
          if (map.value) {
            map.value.addLayer(highlightLayer);
            map.value.addLayer(bufferLayer);
          }

          initInteractions(
            (featureProps) => {
                // Feature Click Handler
                console.log('Feature clicked:', featureProps);
                currentFeature.value = featureProps as GeoDataItem;
                sidePanelVisible.value = true;
            },
            (extent) => {
                // Handle DragBox Selection
                if (isNearbyActive.value) return;

                console.log('Box Selection Extent:', extent);
                
                highlightSource.clear();
                const selected: GeoDataItem[] = [];
                
                // Get features from cluster source
                const features = geoPointSource.getFeaturesInExtent(extent);
                
                features.forEach(feature => {
                    const originalFeatures = feature.get('features');
                    if (originalFeatures) {
                        // It's a cluster, unwrap items
                        originalFeatures.forEach((f: any) => {
                             const props = f.getProperties();
                             // We'll add a clone to highlight layer
                             const clone = f.clone();
                             // clone.setStyle(null); // Use layer style
                             highlightSource.addFeature(clone);
                             
                             if (props.id && props.name) {
                                 selected.push(props as GeoDataItem);
                             }
                        });
                    } else {
                        // Normal feature
                        const props = feature.getProperties();
                        const clone = feature.clone();
                        // clone.setStyle(null);
                        highlightSource.addFeature(clone);
                        
                        if (props.id && props.name) {
                            selected.push(props as GeoDataItem);
                        }
                    }
                });

                if (selected.length > 0) {
                    // Update state correctly for InfoPanel logic
                    if (selected.length === 1) {
                        // Single feature selected
                        currentFeature.value = selected[0];
                        selectedItems.value = selected; // InfoPanel might ignore this due to v-if, but good to keep
                    } else {
                        // Multi selection
                        currentFeature.value = null;
                        selectedItems.value = selected;
                    }
                    sidePanelVisible.value = true;
                } else {
                    ElMessage.info('该区域内未找到点位');
                }
            },
            () => {
                // Blank Click Handler
                if (!isNearbyActive.value) {
                    currentFeature.value = null;
                    sidePanelVisible.value = false;
                    highlightSource.clear(); // Clear highlights
                    bufferSource.clear();
                    closePopup();
                }
            },
            async (_lon, _lat, coords) => {
                const lonLat = toLonLat(coords);

                if (isNearbyActive.value) {
                    // Buffer analysis is now handled by Draw interaction
                    return;
                }

                // Identify Handler
                // Show loading
                // We can reuse popup for loading or result
                popupInfo.value = { name: '查询中...', address: '正在识别周边数据...', loading: true };
                if (popupOverlay) {
                    popupOverlay.setPosition(coords);
                }
                
                try {
                    const res = await geoDataApi.identify(lonLat[0], lonLat[1]);
                    const data = res.data || []; // Access the data array from response
                    
                    if (data && data.length > 0) {
                        // Found something
                        // For now just show the first one or a list summary
                        const first = data[0];
                        popupInfo.value = {
                            ...first,
                            address: `发现 ${data.length} 个目标`,
                            loading: false
                        };
                    } else {
                        // No result
                        popupInfo.value = {
                            name: '无数据',
                            address: '该位置周边 100m 无地质数据',
                            loading: false
                        };
                    }
                } catch (e) {
                    console.error(e);
                    popupInfo.value = {
                        name: '查询失败',
                        address: '服务请求异常',
                        loading: false
                    };
                }
            }
          );

          if (mouseTooltipRef.value) {
              initTooltip(mouseTooltipRef.value);
          }
          
          if (popupRef.value && map.value) {
            popupOverlay = new Overlay({
              element: popupRef.value,
              positioning: 'bottom-center',
              stopEvent: true,
              offset: [0, -10]
            });
            map.value.addOverlay(popupOverlay);
          }
          
          console.log('MapView initialization complete');
          
      } catch (error: any) {
          console.error('Failed to initialize map:', error);
          initError.value = true;
          errorMessage.value = error.message || '初始化过程发生未知错误';
          ElMessage.error(`地图初始化失败: ${error.message || '请检查网络或配置'}`);
      }
  } else {
      console.error('Map container element not found - check if MapContainer.vue is rendering');
      initError.value = true;
      errorMessage.value = '无法定位地图容器元素';
      ElMessage.error('无法定位地图容器，请尝试刷新页面');
  }
});

// Methods
const handleSearchSuggestions = async (queryString: string, cb: (results: any[]) => void) => {
    if (!queryString) {
        cb([]);
        return;
    }

    try {
        let center: [number, number] | undefined;
        if (map.value) {
            const view = map.value.getView();
            const centerCoords = view.getCenter();
            if (centerCoords) {
                const lonLat = toLonLat(centerCoords);
                center = lonLat as [number, number];
            }
        }

        const [geoRes, poiRes] = await Promise.allSettled([
            geoDataApi.search(queryString, center),
            searchTiandituPOI(queryString)
        ]);

        let results: any[] = [];

        // 1. Geo Data
        if (geoRes.status === 'fulfilled') {
             const res = geoRes.value;
             const data = Array.isArray(res) ? res : (res as any).data || [];
             if (data.length > 0) {
                 results.push({ type: 'header', name: '地质数据', id: 'header-asset' });
                 results = results.concat(data.map((item: any) => ({
                     ...item,
                     type: 'asset',
                     value: item.name 
                 })));
             }
        }

        // 2. POI Data
        if (poiRes.status === 'fulfilled') {
            const pois = poiRes.value;
            if (pois.length > 0) {
                results.push({ type: 'header', name: '地点信息', id: 'header-location' });
                results = results.concat(pois);
            }
        }

        // 3. Empty State
        if (results.length === 0) {
            results.push({ type: 'empty', name: '未发现相关地质数据或地点', id: 'empty' });
        }

        cb(results);
    } catch (e) {
        console.error(e);
        cb([{ type: 'empty', name: '搜索发生错误', id: 'error' }]);
    }
};

const searchTiandituPOI = async (keyword: string) => {
    try {
        const postObj = {
            keyWord: keyword,
            level: "11",
            mapBound: "-180,-90,180,90",
            queryType: "1",
            start: "0",
            count: "5"
        };
        const postStr = JSON.stringify(postObj);
        // 使用 encodeURIComponent 编码 postStr
        const url = `https://api.tianditu.gov.cn/search?postStr=${encodeURIComponent(postStr)}&type=query&tk=ba13e30aae52239f8056f1c7421cae7c`;
        
        const res = await fetch(url);
        if (!res.ok) {
            console.warn(`TDT Search failed with status: ${res.status}`);
            return [];
        }
        const data = await res.json();
        
        if (data.pois && Array.isArray(data.pois)) {
            return data.pois.map((poi: any) => ({
                name: poi.name,
                address: poi.address,
                type: 'location',
                value: poi.name,
                location: {
                    lon: parseFloat(poi.lonlat.split(' ')[0]),
                    lat: parseFloat(poi.lonlat.split(' ')[1])
                },
                id: poi.hotPointID || `poi-${Math.random()}`
            }));
        }
        return [];
    } catch (e) {
        console.warn('TDT Search failed', e);
        return [];
    }
};

const handleSelectResult = (item: any) => {
    if (item.type === 'header' || item.type === 'empty') return;

    if (item.type === 'asset') {
        currentFeature.value = item;
        sidePanelVisible.value = true;
        if (item.center_x && item.center_y) {
            const coords = toMapCoords([item.center_x, item.center_y], item.srid);
            flyTo(coords);
            setNavigationMarker(coords, item.name);
        }
    } else if (item.type === 'location') {
        // Handle POI selection
        sidePanelVisible.value = false; // Close info panel for POI
        const coords = fromLonLat([item.location.lon, item.location.lat]) as [number, number];
        
        if (map.value) {
            map.value.getView().animate({
                center: coords,
                zoom: 14,
                duration: 1000
            });
        }
        
        // Show Popup
        popupInfo.value = item;
        if (popupOverlay) {
          popupOverlay.setPosition(coords);
        }
        
        // setNavigationMarker(coords, item.name, true);
        // ElMessage.success(`已定位到: ${item.name}`);
    }
};


const toggleBaseMap = () => {
    if (currentBaseMap.value === 'vector') {
        currentBaseMap.value = 'satellite';
    } else {
        currentBaseMap.value = 'vector';
    }
    updateBaseMapLayers();
};

const updateBaseMapLayers = () => {
    // Explicitly manage layers: destroy old ones, add new ones
    if (currentBaseMap.value === 'vector') {
        removeLayer('tdt-img');
        removeLayer('tdt-cia');
        addTDTLayer('vec');
        addTDTLayer('cva');
        activeLayerKeys.value = activeLayerKeys.value.filter(k => k !== 'tdt-img' && k !== 'tdt-cia').concat(['tdt-vec', 'tdt-cva']);
    } else if (currentBaseMap.value === 'satellite') {
        removeLayer('tdt-vec');
        removeLayer('tdt-cva');
        addTDTLayer('img');
        addTDTLayer('cia');
        activeLayerKeys.value = activeLayerKeys.value.filter(k => k !== 'tdt-vec' && k !== 'tdt-cva').concat(['tdt-img', 'tdt-cia']);
    }
};

const handleLayerVisibilityChange = ({ key, visible }: { key: string, visible: boolean }) => {
    if (layerConfig.value[key]) {
        layerConfig.value[key].visible = visible;
        
        if (key === 'raster') {
            // Toggle Base Map Layers
            const baseMapLayers = ['tdt-vec', 'tdt-cva', 'tdt-img', 'tdt-cia', 'osm', 'esri-sat'];
            layers.value.forEach(layer => {
                const id = layer.get('id');
                if (id && baseMapLayers.includes(id)) {
                    // Only toggle if it matches current base map logic?
                    // Simplified: just toggle visibility if it's active
                    // But activeLayerKeys controls this.
                    // Better: Update activeLayerKeys if we want to persist state properly?
                    // Or just setVisible directly for temporary toggle.
                    // Using activeLayerKeys is safer for reactivity.
                    
                    // Actually, activeLayerKeys is for "which source is selected".
                    // If we want to hide "Raster" entirely, we should just hide them.
                    // But `activeLayerKeys` watcher will override it if we just use setVisible.
                    // So we might need a separate mechanism or just hack it.
                    
                    // Let's use setVisible, but watcher watches activeLayerKeys.
                    // If activeLayerKeys changes, it resets visibility.
                    // So we should probably modify activeLayerKeys?
                    // But activeLayerKeys determines *content*.
                    // If we remove 'tdt-vec' from activeLayerKeys, it's gone.
                    
                    // Let's try direct setVisible. The watcher only runs when keys change.
                    if (activeLayerKeys.value.includes(id)) {
                        layer.setVisible(visible);
                    }
                }
            });
        } else if (key === 'boreholes') {
            const layer = layers.value.find(l => l.get('id') === 'boreholes');
            if (layer) {
                layer.setVisible(visible);
            }
        }
    }
};

const handleLayerOpacityChange = ({ key, opacity }: { key: string, opacity: number }) => {
    if (layerConfig.value[key]) {
        layerConfig.value[key].opacity = opacity;
        const val = opacity / 100;
        
        if (key === 'raster') {
             const baseMapLayers = ['tdt-vec', 'tdt-cva', 'tdt-img', 'tdt-cia', 'osm', 'esri-sat'];
             layers.value.forEach(layer => {
                const id = layer.get('id');
                if (id && baseMapLayers.includes(id)) {
                    layer.setOpacity(val);
                }
             });
        } else if (key === 'boreholes') {
            const layer = layers.value.find(l => l.get('id') === 'boreholes');
            if (layer) {
                layer.setOpacity(val);
            }
        }
    }
};

const loadGeoData = async (source: VectorSource) => {
    try {
        const res = await geoDataApi.getList();
        console.log('Geo data API response:', res);
        const data = Array.isArray(res) ? res : (res as any).data || [];
        
        if (data.length === 0) {
            console.warn('No geo data returned from API');
        }

        rawFeatures.value = data; // Sync for Cesium

        source.clear();
        data.forEach((item: GeoDataItem) => {
             if (item.center_x && item.center_y) {
                 const coords = toMapCoords([item.center_x, item.center_y], item.srid);
                 const feature = new Feature({
                     geometry: new Point(coords),
                     ...item
                 });
                 source.addFeature(feature);
             }
        });
        console.log(`Loaded ${source.getFeatures().length} features into source`);
    } catch (e: any) {
        console.error('Failed to load geo data:', e);
        ElMessage.error(`数据加载失败: ${e.message || '请检查接口权限'}`);
    }
};

const handleLocation = () => {
    locating.value = true;
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const coords = toMapCoords([pos.coords.longitude, pos.coords.latitude], 4326);
            flyTo(coords, 15);
            setNavigationMarker(coords, '当前位置');
            locating.value = false;
            ElMessage.success('定位成功');
        },
        (_err) => {
            ElMessage.error('定位失败');
            locating.value = false;
        }
    );
};

const handleShare = async () => {
    if (!map.value) return;
    const view = map.value.getView();
    const center = view.getCenter();
    const zoom = view.getZoom();
    
    if (center && zoom) {
        const lonLat = toLonLat(center);
        const lon = lonLat[0].toFixed(6);
        const lat = lonLat[1].toFixed(6);
        const z = zoom.toFixed(2);
        
        const url = new URL(window.location.href);
        url.searchParams.set('lon', lon);
        url.searchParams.set('lat', lat);
        url.searchParams.set('z', z);
        // Remove other params if needed or keep them?
        // Let's keep others but remove 'id' if we just want to share view
        // But user requirement is just "generate form like ?lon=...".
        // Let's clean up ID to avoid confusion if sharing just view
        url.searchParams.delete('id');
        url.searchParams.delete('name');
        
        try {
            await navigator.clipboard.writeText(url.toString());
            ElMessage.success('链接已复制到剪贴板');
        } catch (err) {
            ElMessage.error('复制失败');
            console.error('Copy failed', err);
        }
    }
};

const clearSelection = () => {
    clearInteractions();
    sidePanelVisible.value = false;
};

// Removed duplicate handleLogout

const closeSidePanel = () => {
    sidePanelVisible.value = false;
    currentFeature.value = null;
};

const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
};

const handleDownload = async (item: GeoDataItem) => {
    try {
        const blob = await geoDataApi.downloadBatch([item.id]);
        const filename = `${item.name || 'geodata'}.zip`;
        downloadBlob(blob, filename);
    } catch (e: any) {
        ElMessage.error(e?.message || '下载失败');
    }
};

const handlePreview = (item: GeoDataItem) => {
    if (item.center_x && item.center_y) {
        const coords = toMapCoords([item.center_x, item.center_y], item.srid);
        flyTo(coords);
        setNavigationMarker(coords, item.name);
    }
};

const locateItem = (item: GeoDataItem) => {
    handlePreview(item);
};

const handleZoomChange = (val: number) => {
    const mapInstance = map.value;
    if (mapInstance) {
        mapInstance.getView().setZoom(val);
    }
};

const zoomIn = () => {
    const mapInstance = map.value;
    if (mapInstance) {
        const view = mapInstance.getView();
        const currentZoom = view.getZoom() || 10;
        view.animate({ zoom: currentZoom + 1, duration: 250 });
    }
};

const zoomOut = () => {
    const mapInstance = map.value;
    if (mapInstance) {
        const view = mapInstance.getView();
        const currentZoom = view.getZoom() || 10;
        view.animate({ zoom: currentZoom - 1, duration: 250 });
    }
};

onUnmounted(() => {
    if (map.value) {
        map.value.setTarget(undefined);
        clearLayers();
        removeInteractions();
        // Clear sources to free memory
        navigationSource.clear();
        geoPointSource.clear();
    }
});
</script>

<style scoped>
/* Dark Mode Support */
.map-view-container.dark-mode :deep(.ol-layer-invertible) {
    filter: invert(100%) hue-rotate(180deg) brightness(0.95) contrast(0.9);
    transition: filter 0.3s ease;
}

/* Optimization for map interactions */
:deep(.map-moving) * {
  animation: none !important;
  transition: none !important;
}

.swipe-control-container {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 50;
    display: flex;
    justify-content: center;
    align-items: center;
}

.swipe-slider {
    pointer-events: auto;
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 100%;
    background: transparent;
    outline: none;
    margin: 0;
    padding: 0;
    cursor: ew-resize;
}

.swipe-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 4px;
    height: 100vh;
    background: #fff;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
    cursor: ew-resize;
}

.swipe-slider::-moz-range-thumb {
    width: 4px;
    height: 100vh;
    background: #fff;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
    cursor: ew-resize;
    border: none;
}

.map-popup-overlay {
  position: absolute;
  min-width: 200px;
}

.popup-content {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  animation: popup-fade-in 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.popup-title {
  font-weight: 600;
  font-size: 16px;
  color: #1d1d1f;
  margin: 0;
}

.popup-body {
  font-size: 14px;
  color: #86868b;
}

.popup-address {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
}

.popup-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.ripple-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: -1;
}

.ripple {
  width: 20px;
  height: 20px;
  background: rgba(0, 113, 227, 0.4);
  border-radius: 50%;
  position: absolute;
  top: 100%; /* Anchor to bottom point */
  left: 50%;
  transform: translate(-50%, -50%);
  animation: ripple-effect 2s infinite;
}

@keyframes ripple-effect {
  0% {
    width: 0;
    height: 0;
    opacity: 0.8;
  }
  100% {
    width: 100px;
    height: 100px;
    opacity: 0;
  }
}

@keyframes popup-fade-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.mouse-tooltip {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  pointer-events: none;
  white-space: nowrap;
  z-index: 1000;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.8);
  z-index: 2000;
}

.error-state {
  background-color: #fff;
  z-index: 3000;
}

.error-text {
  color: #f56c6c;
  margin-bottom: 15px;
}

/* Control Buttons */
.top-right-controls {
  position: absolute;
  top: 30px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 90;
}

.control-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #555;
  font-size: 18px;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.control-btn.active {
  background: #0071E3;
  color: white;
  border-color: #0071E3;
}

.control-btn.danger:hover {
  color: #F56C6C;
  background: rgba(245, 108, 108, 0.1);
}

.divider-horizontal {
  height: 1px;
  background: rgba(0, 0, 0, 0.1);
  margin: 4px 0;
}

/* Bottom Right Navigation */
.bottom-right-controls {
  position: absolute;
  bottom: 120px; /* Adjusted to be above the dock */
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 90;
  align-items: center;
}

.nav-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #333;
  font-size: 20px;
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: scale(1.05);
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.logout-btn {
  color: #FF3B30; /* Apple Red */
}

.logout-btn:hover {
  background: #FF3B30;
  color: white;
}

.map-zoom-control-vertical {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 12px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.zoom-btn {
  font-size: 20px;
  cursor: pointer;
  color: #555;
  padding: 4px;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zoom-btn:hover {
  color: #0071E3;
  transform: scale(1.1);
}

/* Remove old zoom control styling */
.map-zoom-control {
  display: none;
}

/* Top Search Container */
.top-search-container {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  width: auto;
  min-width: 320px;
  transition: all 0.3s ease;
}

/* Slide Transitions */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

</style>
