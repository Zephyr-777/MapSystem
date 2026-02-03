<template>
  <div class="map-view-container">
    <ErrorBoundary>
      <MapContainer ref="mapContainerRef" :map-instance="map">
        <!-- Mouse Tooltip Overlay Content -->
        <div ref="mouseTooltipRef" class="mouse-tooltip" v-show="tooltipContent">
          {{ tooltipContent }}
        </div>
      </MapContainer>

      <div v-if="!mapReady" class="loading-overlay">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span style="margin-left: 10px">正在初始化地图...</span>
      </div>

      <Suspense>
        <template #default>
          <div v-if="mapReady">
          <SearchBox 
            :results="searchResults" 
            @search="handleSearch" 
            @select-result="handleSelectResult"
            @upload="showUploadDialog = true"
          />

          <LayerControl 
            :visible="showLayerPanel"
            :layer-config="layerConfig"
            @close="showLayerPanel = false"
            @update:visibility="handleLayerVisibilityChange"
            @update:opacity="handleLayerOpacityChange"
          />

          <InfoPanel 
            :visible="sidePanelVisible"
            :title="panelTitle"
            :feature="currentFeature"
            :is-multi-selection="isMultiSelection"
            :selected-items="selectedItems"
            @close="closeSidePanel"
            @download="handleDownload"
            @preview="handlePreview"
            @batch-download="executeSpatialDownload"
            @locate-item="locateItem"
            @preview-report="previewReport"
          />

          <StatsPanel 
            v-if="showAttributeDashboard"
            :data="selectedStats" 
          />
          
          <div class="floating-toolbar">
             <el-tooltip :content="currentBaseMap === 'vector' ? '切换卫星影像' : '切换电子地图'" placement="left">
                <el-button 
                  :type="currentBaseMap === 'satellite' ? 'success' : 'default'"
                  :icon="MapLocation" 
                  circle 
                  @click="toggleBaseMap" 
                />
             </el-tooltip>
             <el-tooltip content="图层管理" placement="left">
                <el-button 
                  :type="showLayerPanel ? 'primary' : 'default'"
                  :icon="Files" 
                  circle 
                  @click="showLayerPanel = !showLayerPanel" 
                />
             </el-tooltip>
             <el-tooltip content="框选工具" placement="left">
                <el-button 
                  :type="isDragBoxActive ? 'primary' : 'default'" 
                  :icon="Crop" 
                  circle 
                  @click="toggleDragBox" 
                />
             </el-tooltip>
             <el-tooltip content="定位" placement="left">
                <el-button 
                  :loading="locating" 
                  :icon="Location" 
                  circle 
                  @click="handleLocation" 
                />
             </el-tooltip>
             <el-tooltip content="清除选择" placement="left">
                <el-button 
                  :disabled="!selectedExtent" 
                  :icon="Delete" 
                  circle 
                  @click="clearSelection" 
                />
             </el-tooltip>
             <el-tooltip content="退出登录" placement="left">
                <el-button 
                  type="danger" 
                  plain
                  :icon="SwitchButton" 
                  circle 
                  @click="handleLogout" 
                />
             </el-tooltip>
          </div>
        </div>
      </template>
      <template #fallback>
        <div class="loading-overlay">正在加载地图组件...</div>
      </template>
    </Suspense>
      
      <!-- Upload Dialog (Simplified) -->
      <el-dialog v-model="showUploadDialog" title="上传地质数据">
         <span>上传功能开发中...</span>
      </el-dialog>
    </ErrorBoundary>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, defineAsyncComponent, shallowRef } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { geoDataApi } from '@/api/geodata';
import { ElMessage } from 'element-plus';
import { MapLocation, Files, Crop, Location, Delete, SwitchButton, Loading } from '@element-plus/icons-vue';
import type Map from 'ol/Map';
import type { GeoDataItem, LayerConfig, SearchResult } from '@/views/map/types/map';
import useMapCore from '@/composables/useMapCore';
import useMapLayers from '@/composables/useMapLayers';
import useMapInteractions from '@/composables/useMapInteractions';
import VectorSource from 'ol/source/Vector';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import { fromLonLat } from 'ol/proj';

// Components
import ErrorBoundary from '@/components/ErrorBoundary.vue';
import MapContainer from '@/views/map/components/MapContainer.vue';
const SearchBox = defineAsyncComponent({ loader: () => import('@/views/map/components/SearchBox.vue') });
const LayerControl = defineAsyncComponent({ loader: () => import('@/views/map/components/LayerControl.vue') });
const InfoPanel = defineAsyncComponent({ loader: () => import('@/views/map/components/InfoPanel.vue') });
const StatsPanel = defineAsyncComponent({ loader: () => import('@/views/map/components/StatsPanel.vue') });

// Composables
const { initMap, mapReady } = useMapCore();
const { addOSMLayer, addEsriSatelliteLayer, addNavigationLayer, addClusterLayer, activeLayerKeys, clearLayers } = useMapLayers();
const { initInteractions, toggleDragBox, isDragBoxActive, selectedExtent, clearSelection: clearInteractions, initTooltip, flyTo } = useMapInteractions();

const router = useRouter();
const authStore = useAuthStore();
const map = shallowRef<Map | null>(null);
const mapContainerRef = ref<any>(null);

// State
const showLayerPanel = ref(false);
const sidePanelVisible = ref(false);
const showAttributeDashboard = ref(true);
const panelTitle = ref('详情');
const currentFeature = ref<GeoDataItem | undefined>(undefined);
const isMultiSelection = ref(false);
const selectedItems = ref<GeoDataItem[]>([]);
const searchResults = ref<SearchResult[]>([]);
const showUploadDialog = ref(false);
const locating = ref(false);
const mouseTooltipRef = ref<HTMLElement | null>(null);
const tooltipContent = ref('');
const selectedStats = ref<Array<{name: string, value: number}>>([]);
const currentBaseMap = ref<'vector' | 'satellite'>('vector');
const navigationSource = new VectorSource();
const zoomLevel = ref(10);

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

const setNavigationMarker = (coord: [number, number], name?: string) => {
  navigationSource.clear();
  const feature = new Feature({
    geometry: new Point(coord),
    name: name || '导航点'
  });
  navigationSource.addFeature(feature);
};

// Init Map
onMounted(async () => {
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
          });
          
          clearLayers();

          console.log('Initializing layers...');
          addOSMLayer();
          addEsriSatelliteLayer();
          addNavigationLayer(navigationSource);
          updateBaseMapLayers();

          // Mock Data Layer (Cluster)
          const geoPointSource = new VectorSource();
          addClusterLayer(geoPointSource, 60);

          // Load Data
          console.log('Loading geo data...');
          await loadGeoData(geoPointSource);

          // Init Interactions
          console.log('Initializing interactions...');
          initInteractions(
            (featureProps) => {
                currentFeature.value = featureProps as GeoDataItem;
                sidePanelVisible.value = true;
                panelTitle.value = featureProps.name || '详情';
                isMultiSelection.value = false;
            },
            (extent) => {
                updateSelectedStats(extent);
                isMultiSelection.value = true;
                sidePanelVisible.value = true;
                panelTitle.value = '已选点位';
            }
          );

          if (mouseTooltipRef.value) {
              initTooltip(mouseTooltipRef.value);
          }
          console.log('MapView initialization complete');
      } catch (error: any) {
          console.error('Failed to initialize map:', error);
          ElMessage.error(`地图初始化失败: ${error.message || '请检查网络或配置'}`);
      }
  } else {
      console.error('Map container element not found - check if MapContainer.vue is rendering');
      ElMessage.error('无法定位地图容器，请尝试刷新页面');
  }
});

// Methods
const handleSearch = async (query: string) => {
    try {
        const res = await geoDataApi.search(query);
        if (Array.isArray(res)) {
            searchResults.value = res;
        } else if ((res as any).data) {
            searchResults.value = (res as any).data;
        }
    } catch (e) {
        console.error(e);
    }
};

const handleSelectResult = (item: SearchResult) => {
    currentFeature.value = item;
    sidePanelVisible.value = true;
    panelTitle.value = item.name;
    isMultiSelection.value = false;
    if (item.center_x && item.center_y) {
        const coords = toMapCoords([item.center_x, item.center_y], item.srid);
        flyTo(coords);
        setNavigationMarker(coords, item.name);
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
    const keys = [];
    if (currentBaseMap.value === 'vector') {
        keys.push('osm');
    } else if (currentBaseMap.value === 'satellite') {
        keys.push('esri-sat');
    }
    
    const otherKeys = activeLayerKeys.value.filter(k => k !== 'osm' && k !== 'esri-sat');
    activeLayerKeys.value = [...otherKeys, ...keys];
};

const handleLayerVisibilityChange = ({ key, visible }: { key: string, visible: boolean }) => {
    if (layerConfig.value[key]) {
        layerConfig.value[key].visible = visible;
        // Update activeLayerKeys if these map to layer IDs
        // This requires mapping config keys to layer IDs.
        // For now, simplified.
    }
};

const handleLayerOpacityChange = ({ key, opacity }: { key: string, opacity: number }) => {
    if (layerConfig.value[key]) {
        layerConfig.value[key].opacity = opacity;
        // Update layer opacity
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

const updateSelectedStats = (_extent: [number, number, number, number]) => {
    // Logic to calculate stats from layers based on extent
    // This requires accessing layer sources.
    // For now, mock implementation or access via useMapLayers if exposed.
    selectedStats.value = [
        { name: '花岗岩', value: Math.floor(Math.random() * 10) },
        { name: '玄武岩', value: Math.floor(Math.random() * 10) }
    ];
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

const clearSelection = () => {
    clearInteractions();
    sidePanelVisible.value = false;
    selectedStats.value = [];
};

const handleLogout = () => {
    authStore.logout();
    router.push('/login');
};

const closeSidePanel = () => {
    sidePanelVisible.value = false;
    currentFeature.value = undefined;
};

const handleDownload = (item: GeoDataItem) => {
    ElMessage.success(`下载: ${item.name}`);
};

const handlePreview = (item: GeoDataItem) => {
    if (item.center_x && item.center_y) {
        const coords = toMapCoords([item.center_x, item.center_y], item.srid);
        flyTo(coords);
        setNavigationMarker(coords, item.name);
    }
};

const executeSpatialDownload = () => {
    ElMessage.success('批量下载中...');
};

const locateItem = (item: GeoDataItem) => {
    handlePreview(item);
};

const previewReport = (report: any) => {
    ElMessage.info(`预览报告: ${report.title}`);
};

onUnmounted(() => {
    if (map.value) {
        map.value.setTarget(undefined);
        clearLayers();
        // Clear sources to free memory
        navigationSource.clear();
    }
});
</script>

<style scoped>
/* Optimization for map interactions */
:deep(.map-moving) * {
  animation: none !important;
  transition: none !important;
}

.map-view-container {
  position: absolute;
  width: 100vw;
  height: 100vh;
  top: 0;
  left: 0;
  overflow: hidden;
  background: #f0f2f5;
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
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.8);
  padding: 20px;
  border-radius: 8px;
  pointer-events: none;
}

.floating-toolbar {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #fff;
  padding: 8px;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 100;
}

.floating-toolbar .el-button {
  margin-left: 0 !important;
}
</style>
