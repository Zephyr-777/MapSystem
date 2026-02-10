<template>
  <div class="map-view-container">
    <ErrorBoundary>
      <MapContainer ref="mapContainerRef" :map-instance="map">
        <!-- Mouse Tooltip Overlay Content -->
        <div ref="mouseTooltipRef" class="mouse-tooltip" v-show="tooltipContent">
          {{ tooltipContent }}
        </div>
        
        <!-- Result Popover Overlay -->
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

        <!-- Zoom Control -->
        <div class="map-zoom-control card-shadow">
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
        <SearchBox 
          :fetch-suggestions="handleSearchSuggestions"
          @select-result="handleSelectResult"
          @upload="showUploadDialog = true"
        />

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

        <Transition name="fade-slide">
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
          />
        </Transition>

        <Transition name="fade-slide">
          <StatsPanel 
            v-if="showAttributeDashboard"
          />
        </Transition>
        
        <div class="floating-toolbar">
           <el-tooltip :content="currentBaseMap === 'vector' ? '切换卫星影像' : '切换电子地图'" placement="left">
              <button 
                class="toolbar-btn"
                :class="{ 'active': currentBaseMap === 'satellite' }"
                @click="toggleBaseMap" 
              >
                <el-icon><MapLocation /></el-icon>
              </button>
           </el-tooltip>
           
           <el-tooltip content="图层管理" placement="left">
              <button 
                class="toolbar-btn"
                :class="{ 'active': showLayerPanel }"
                @click="showLayerPanel = !showLayerPanel" 
              >
                <el-icon><Files /></el-icon>
              </button>
           </el-tooltip>
           
           <el-tooltip content="数据统计" placement="left">
              <button 
                class="toolbar-btn"
                :class="{ 'active': showAttributeDashboard }"
                @click="showAttributeDashboard = !showAttributeDashboard" 
              >
                <el-icon><PieChart /></el-icon>
              </button>
           </el-tooltip>
           
           <el-tooltip content="框选工具" placement="left">
              <button 
                class="toolbar-btn"
                :class="{ 'active': isDragBoxActive }"
                @click="toggleDragBox" 
              >
                <el-icon><Crop /></el-icon>
              </button>
           </el-tooltip>
           
           <el-tooltip content="定位" placement="left">
              <button 
                class="toolbar-btn"
                :class="{ 'loading': locating }"
                @click="handleLocation" 
              >
                <el-icon :class="{ 'is-loading': locating }"><Location /></el-icon>
              </button>
           </el-tooltip>
           
           <el-tooltip content="清除选择" placement="left">
              <button 
                class="toolbar-btn"
                :disabled="!selectedExtent"
                @click="clearSelection" 
              >
                <el-icon><Delete /></el-icon>
              </button>
           </el-tooltip>
           
           <div class="divider"></div>
           
           <el-tooltip content="退出登录" placement="left">
              <button 
                class="toolbar-btn danger"
                @click="handleLogout" 
              >
                <el-icon><SwitchButton /></el-icon>
              </button>
           </el-tooltip>
        </div>
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
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { geoDataApi, type GeoDataItem } from '@/api/geodata';
import { ElMessage } from 'element-plus';
import { MapLocation, Files, Crop, Location, Delete, SwitchButton, Loading, Plus, Minus, RefreshRight, PieChart, Close, LocationInformation } from '@element-plus/icons-vue';
import type Map from 'ol/Map';
import type { LayerConfig } from '@/views/map/types/map';
import useMapCore from '@/composables/useMapCore';
import useMapLayers from '@/composables/useMapLayers';
import useMapInteractions from '@/composables/useMapInteractions';
import VectorSource from 'ol/source/Vector';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import { fromLonLat, toLonLat } from 'ol/proj';
import { Style, Fill, Stroke, Circle as CircleStyle } from 'ol/style';
import VectorLayer from 'ol/layer/Vector';
import Overlay from 'ol/Overlay';

// Components
import ErrorBoundary from '@/components/ErrorBoundary.vue';
import MapContainer from '@/views/map/components/MapContainer.vue';
import SearchBox from '@/views/map/components/SearchBox.vue';
import LayerControl from '@/views/map/components/LayerControl.vue';
import InfoPanel from '@/views/map/components/InfoPanel.vue';
import StatsPanel from '@/views/map/components/StatsPanel.vue';
import UploadDialog from '@/views/map/components/UploadDialog.vue';

// Composables
const { initMap, mapReady } = useMapCore();
const { addOSMLayer, addEsriSatelliteLayer, addTDTLayer, addNavigationLayer, addClusterLayer, removeLayer, activeLayerKeys, clearLayers } = useMapLayers();
const { initInteractions, toggleDragBox, isDragBoxActive, selectedExtent, clearSelection: clearInteractions, initTooltip, flyTo, removeInteractions, selectedItems } = useMapInteractions();

const router = useRouter();
const authStore = useAuthStore();
const map = shallowRef<Map | null>(null);
const mapContainerRef = ref<any>(null);

// State
const initError = ref(false);
const errorMessage = ref('');
const showLayerPanel = ref(false);
const sidePanelVisible = ref(false);
const showAttributeDashboard = ref(true);
const currentFeature = ref<GeoDataItem | null>(null);
const showUploadDialog = ref(false);
const locating = ref(false);
const mouseTooltipRef = ref<HTMLElement | null>(null);
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

const handleUploadSuccess = async (asset: any) => {
    // Reload data
    await loadGeoData(geoPointSource);
    
    // Fly to
    if (asset.center_x && asset.center_y) {
        const coords = toMapCoords([asset.center_x, asset.center_y], asset.srid || 4326);
        flyTo(coords);
        setNavigationMarker(coords, asset.name);
        ElMessage.success(`已跳转到新数据: ${asset.name}`);
    }
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
          addClusterLayer(geoPointSource, 60);

          // Load Data
          console.log('Loading geo data...');
          await loadGeoData(geoPointSource);

          // Init Interactions
          console.log('Initializing interactions...');
          if (map.value) {
            map.value.addLayer(highlightLayer);
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
                    selectedItems.value = selected;
                    sidePanelVisible.value = true;
                } else {
                    ElMessage.info('该区域内未找到点位');
                }
            },
            () => {
                // Blank Click Handler
                currentFeature.value = null;
                sidePanelVisible.value = false;
                highlightSource.clear(); // Clear highlights
                closePopup();
            },
            async (_lon, _lat, coords) => {
                // Identify Handler
                const lonLat = toLonLat(coords);
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
};

const handleLogout = () => {
    authStore.logout();
    router.push('/login');
};

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
/* Optimization for map interactions */
:deep(.map-moving) * {
  animation: none !important;
  transition: none !important;
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

.floating-toolbar {
  position: absolute;
  top: 50%;
  right: 20px;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 100;
  background: transparent;
  box-shadow: none;
  padding: 0;
}

.toolbar-btn {
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
  transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
  color: #1d1d1f;
  font-size: 20px;
}

.toolbar-btn:hover {
  transform: scale(1.1);
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.toolbar-btn.active {
  background: #0071E3;
  color: white;
  border-color: #0071E3;
}

.toolbar-btn.danger {
  color: #FF3B30;
}

.toolbar-btn.danger:hover {
  background: #FF3B30;
  color: white;
  border-color: #FF3B30;
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.1);
  margin: 4px 10px;
}

/* Global Transitions */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.floating-toolbar .el-button {
  margin-left: 0 !important;
}

.map-zoom-control {
  position: absolute;
  bottom: 30px;
  right: 20px;
  background: #FFFFFF;
  padding: 8px 4px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 100;
  width: 32px;
}

.card-shadow {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.zoom-btn {
  cursor: pointer;
  color: #606266;
  font-size: 16px;
  transition: color 0.2s;
}

.zoom-btn:hover {
  color: #1576FF;
}

:deep(.el-slider__bar) {
  background-color: #1576FF;
}

:deep(.el-slider__button) {
  border-color: #1576FF;
  width: 14px;
  height: 14px;
}
</style>
