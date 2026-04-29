<template>
  <div class="map-view-container">
    <ErrorBoundary>
      <MapContainer ref="mapContainerRef" :map-instance="map">

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

        <aside class="map-hall-panel glass-panel">
          <div class="map-hall-header">
            <h2>地质数据大厅</h2>
            <el-dropdown @command="handleHallExport">
              <el-button type="primary" link>
                导出数据 <el-icon class="el-icon--right"><Download /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="csv">Excel 兼容 CSV</el-dropdown-item>
                  <el-dropdown-item command="json">目录元数据 JSON</el-dropdown-item>
                  <el-dropdown-item command="markdown">目录报告 Markdown</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="map-hall-modules custom-scrollbar">
            <div
              v-for="group in hallCatalogGroups"
              :key="group.id"
              class="map-hall-section"
            >
              <button class="map-hall-section-title" type="button">
                <span>{{ group.label }}</span>
                <span class="map-hall-section-count">{{ group.items.length }}</span>
              </button>
              <div class="map-hall-list">
                <button
                  v-for="item in group.items"
                  :key="item.id"
                  class="map-hall-entry"
                  @click="openCatalogDataset(item.id)"
                >
                  <div class="map-hall-entry-main">
                    <span class="map-hall-entry-title">{{ item.title }}</span>
                    <span class="map-hall-entry-region">{{ getCatalogRegionLabel(item.id) }}</span>
                  </div>
                  <div class="map-hall-entry-meta">
                    <span>{{ getCatalogSourceLabel(item.sourceId) }}</span>
                    <span v-if="item.statusLabel">{{ item.statusLabel }}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>

          <div class="map-hall-summary">
            <span>共 {{ hallCatalogGroups.length }} 类 / {{ hallCatalogItems.length }} 条数据</span>
          </div>
        </aside>

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
          @open-geology-hall="$router.push('/geology')"
          @share-view="handleShareView"
          @upload="showUploadDialog = true"
        />

      </MapContainer>

      <div v-if="!mapReady && !initError" class="loading-overlay">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span style="margin-left: 10px">正在初始化地图...</span>
      </div>

      <div v-if="mapReady && isMapDataLoading" class="map-data-loading-overlay">
        <div class="map-data-loading-card glass-panel">
          <el-icon class="is-loading" :size="20"><Loading /></el-icon>
          <span>正在加载当前视野数据...</span>
        </div>
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
          <SmartSearchBox 
            @search-result="handleSmartSearchResult"
          />
        </div>

        <div v-if="heiheQuickLocateVisible" class="left-overview-panel">
          <button class="heihe-locate-btn" @click="handleQuickLocateHeihe">
            快速定位黑河下游
          </button>
        </div>

        <div v-if="forestCarbonOverlay" class="forest-carbon-panel glass-panel">
          <div class="forest-carbon-title">森林碳储量</div>
          <div class="forest-carbon-controls">
            <el-select v-model="forestCarbonMetric" size="small" class="carbon-select" @change="handleForestCarbonChange">
              <el-option
                v-for="metric in forestCarbonOverlay.metrics"
                :key="metric.id"
                :label="metric.label"
                :value="metric.id"
              />
            </el-select>
            <el-select v-model="forestCarbonYear" size="small" class="year-select" @change="handleForestCarbonChange">
              <el-option
                v-for="year in forestCarbonOverlay.years"
                :key="year"
                :label="`${year}`"
                :value="year"
              />
            </el-select>
          </div>
          <div class="forest-carbon-meta">{{ forestCarbonOverlay.unit }} · {{ forestCarbonOverlay.metric }}</div>
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
            @share="handleShareFeature"
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
import { useGeodataStore } from '@/stores/geodata';
import { useMapStore } from '@/stores/map';
import {
  geoDataApi,
  type GeoDataItem,
  type LocalRasterOverlay,
  type ForestCarbonOverlay,
  type SouthwestTemperatureDataset,
  type CentralAsiaDesertGeoJSONResponse,
  type BadalingImageryDataset
} from '@/api/geodata';
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus';
import { Location, Loading, Plus, Minus, RefreshRight, SwitchButton, Download } from '@element-plus/icons-vue';
import type OLMap from 'ol/Map';
import type { LayerConfig } from '@/views/map/types/map';
import useMapCore from '@/composables/useMapCore';
import useMapLayers from '@/composables/useMapLayers';
import useMapInteractions from '@/composables/useMapInteractions';
import VectorSource from 'ol/source/Vector';
import Cluster from 'ol/source/Cluster';
import VectorLayer from 'ol/layer/Vector';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import GeoJSON from 'ol/format/GeoJSON';
import { fromLonLat, toLonLat, transformExtent } from 'ol/proj';
import { Style, Fill, Stroke, Circle as CircleStyle, Text } from 'ol/style';
import { toMapCoords, createHighlightLayer, createBufferLayer } from '@/services/mapInteraction';
import {
    catalogDataTypes,
    catalogItems,
    catalogSources,
    findCatalogItem,
    findCatalogRegion,
    getCatalogItemRegion,
    type CatalogSourceId,
} from '@/config/geodataCatalog';





// Components
import ErrorBoundary from '@/components/ErrorBoundary.vue';
import MapContainer from '@/views/map/components/MapContainer.vue';
import SmartSearchBox from '@/views/map/components/SmartSearchBox.vue';
import BottomDock from '@/components/layout/BottomDock.vue';
import LayerControl from '@/views/map/components/LayerControl.vue';
import InfoPanel from '@/views/map/components/InfoPanel.vue';
import UploadDialog from '@/views/map/components/UploadDialog.vue';
import StatsPanel from '@/views/map/components/StatsPanel.vue';



// Composables
const { initMap, mapReady } = useMapCore();
const { addOSMLayer, addEsriSatelliteLayer, addTDTLayer, addNavigationLayer, addClusterLayer, addHeatmapLayer, addGeoTiffOverlayLayer, removeLayer, activeLayerKeys, clearLayers, layers } = useMapLayers();
const { initInteractions, toggleDragBox, isDragBoxActive, initTooltip, flyTo, removeInteractions, selectedItems, startDrawing, stopDrawing } = useMapInteractions();

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const geodataStore = useGeodataStore();
const mapStore = useMapStore();
const map = shallowRef<OLMap | null>(null);
const mapContainerRef = ref<any>(null);

// State
const activeTool = ref<string>('');
const initError = ref(false);
const errorMessage = ref('');
const showLayerPanel = ref(false);
const sidePanelVisible = ref(false);
const mapDataLoadingCount = ref(0);
const isMapDataLoading = computed(() => mapDataLoadingCount.value > 0);

const currentFeature = ref<GeoDataItem | null>(null);
const showUploadDialog = ref(false);
const locating = ref(false);
const isNearbyActive = ref(false);
const isSwipeActive = ref(false);
const swipeValue = ref(50);
const mouseTooltipRef = ref<HTMLElement | null>(null);


const localRasterOverlays = ref<LocalRasterOverlay[]>([]);
const hasAutoFocusedLocalOverlay = ref(false);
const forestCarbonOverlay = ref<ForestCarbonOverlay | null>(null);
const forestCarbonMetric = ref<'AGBC' | 'BGBC'>('AGBC');
const forestCarbonYear = ref(2021);
const lastDataBBoxKey = ref('');
const southwestTemperatureDataset = ref<SouthwestTemperatureDataset | null>(null);
const badalingImageryDataset = ref<BadalingImageryDataset | null>(null);
const hepingjieImageryDataset = ref<BadalingImageryDataset | null>(null);
const centralAsiaCountriesSource = new VectorSource();
const centralAsiaUrbanPolygonSource = new VectorSource();
const centralAsiaUrbanPointSource = new VectorSource();
const centralAsiaUrbanPointClusterSource = new Cluster({
  distance: 72,
  minDistance: 24,
  source: centralAsiaUrbanPointSource,
});
let centralAsiaCountriesLayer: VectorLayer<VectorSource> | null = null;
let centralAsiaUrbanPolygonLayer: VectorLayer<VectorSource> | null = null;
let centralAsiaUrbanPointLayer: VectorLayer<Cluster> | null = null;
const centralAsiaGeoJSON = new GeoJSON();
const centralAsiaDatasetBBox = ref<[number, number, number, number] | null>(null);
const centralAsiaSelectedId = ref<string | number | null>(null);
const centralAsiaPolygonBBoxKey = ref('');
const centralAsiaPointBBoxKey = ref('');
const CENTRAL_ASIA_POINT_MIN_ZOOM = 8;
const CENTRAL_ASIA_POLYGON_MIN_ZOOM = 10;
const BADALING_IMAGERY_LAYER_PREFIX = 'badaling-imagery';
const HEPINGJIE_IMAGERY_LAYER_PREFIX = 'hepingjie-imagery';

const getLocalRasterLayerId = (overlayId: string) => `local-raster-${overlayId}`;
const getLocalRasterLayerKey = (overlayId: string) => `localRaster_${overlayId}`;
const getOverlayIdFromLayerKey = (key: string) =>
  key.startsWith('localRaster_') ? key.slice('localRaster_'.length) : null;
const FOREST_CARBON_LAYER_ID = 'forest-carbon-raster';
const getBadalingLayerId = (level: number, tileId: string) => `${BADALING_IMAGERY_LAYER_PREFIX}-${level}-${tileId}`;
const getHepingjieLayerId = (level: number, tileId: string) => `${HEPINGJIE_IMAGERY_LAYER_PREFIX}-${level}-${tileId}`;

const beginMapLoading = () => {
    mapDataLoadingCount.value += 1;
};

const endMapLoading = () => {
    mapDataLoadingCount.value = Math.max(0, mapDataLoadingCount.value - 1);
};

const withMapLoading = async <T,>(task: () => Promise<T>) => {
    beginMapLoading();
    try {
        return await task();
    } finally {
        endMapLoading();
    }
};

const getCurrentMapBBox = (): [number, number, number, number] | undefined => {
    if (!map.value) return undefined;
    const size = map.value.getSize();
    if (!size) return undefined;
    const extent = map.value.getView().calculateExtent(size);
    return transformExtent(extent, 'EPSG:3857', 'EPSG:4326') as [number, number, number, number];
};

const buildBBoxKey = (bbox?: [number, number, number, number]) =>
    bbox ? bbox.map((value) => value.toFixed(2)).join(',') : '';

const hallCatalogItems = computed(() => catalogItems);
const hallCatalogGroups = computed(() =>
    catalogDataTypes
        .map((type) => ({
            ...type,
            items: hallCatalogItems.value.filter((item) => item.dataTypeId === type.id),
        }))
        .filter((group) => group.items.length > 0)
);

const getCatalogRegionLabel = (catalogId: string) => {
    const item = findCatalogItem(catalogId);
    const region = item ? getCatalogItemRegion(item) : undefined;
    return region?.shortName || '专题数据';
};

const getCatalogTypeLabel = (catalogId: string) => {
    const item = findCatalogItem(catalogId);
    return catalogDataTypes.find((entry) => entry.id === item?.dataTypeId)?.label || '专题数据';
};

const getCatalogSourceLabel = (sourceId?: CatalogSourceId) =>
    catalogSources.find((entry) => entry.id === sourceId)?.label || '平台数据';

const openCatalogDataset = (catalogId: string) => {
    const item = findCatalogItem(catalogId);
    if (!item) return;

    enableCatalogLayers(item.id);
    fitCatalogRegion(item.regionId);
    ElMessage.success(`已定位到：${item.title}`);

    router.replace({
        name: 'Map',
        query: {
            ...route.query,
            catalog: item.id,
            layer: item.id,
            region: item.regionId,
        },
    });
};

const catalogExportRows = computed(() =>
    hallCatalogItems.value.map((item) => {
        const region = getCatalogItemRegion(item);
        return {
            id: item.id,
            title: item.title,
            type: getCatalogTypeLabel(item.id),
            source: getCatalogSourceLabel(item.sourceId),
            region: region?.name || '',
            status: item.statusLabel || '',
            tags: item.tags.join('、'),
            description: item.description,
        };
    })
);

const escapeCsvCell = (value: unknown) => {
    const text = String(value ?? '');
    return `"${text.replace(/"/g, '""')}"`;
};

const downloadTextFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
};

const buildCatalogCsv = () => {
    const headers = ['ID', '名称', '数据类型', '来源', '区域', '状态', '标签', '描述'];
    const rows = catalogExportRows.value.map((row) => [
        row.id,
        row.title,
        row.type,
        row.source,
        row.region,
        row.status,
        row.tags,
        row.description,
    ]);
    return [headers, ...rows].map((row) => row.map(escapeCsvCell).join(',')).join('\n');
};

const buildCatalogMarkdown = () => {
    const lines = [
        '# 地质数据大厅目录',
        '',
        `导出时间：${new Date().toLocaleString()}`,
        '',
        `共 ${hallCatalogGroups.value.length} 类 / ${hallCatalogItems.value.length} 条数据。`,
        '',
    ];

    hallCatalogGroups.value.forEach((group) => {
        lines.push(`## ${group.label}`, '');
        group.items.forEach((item) => {
            const region = getCatalogItemRegion(item);
            lines.push(`- ${item.title}`);
            lines.push(`  - 区域：${region?.name || '-'}`);
            lines.push(`  - 来源：${getCatalogSourceLabel(item.sourceId)}`);
            lines.push(`  - 状态：${item.statusLabel || '-'}`);
            lines.push(`  - 描述：${item.description}`);
        });
        lines.push('');
    });

    return lines.join('\n');
};

const handleHallExport = (format: string) => {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');

    if (format === 'json') {
        downloadTextFile(
            JSON.stringify(catalogExportRows.value, null, 2),
            `geology-catalog-${timestamp}.json`,
            'application/json;charset=utf-8'
        );
    } else if (format === 'markdown') {
        downloadTextFile(
            buildCatalogMarkdown(),
            `geology-catalog-${timestamp}.md`,
            'text/markdown;charset=utf-8'
        );
    } else {
        downloadTextFile(
            `\ufeff${buildCatalogCsv()}`,
            `geology-catalog-${timestamp}.csv`,
            'text/csv;charset=utf-8'
        );
    }

    ElMessage.success('地质数据大厅目录已导出');
};

const bboxIntersects = (
    a?: [number, number, number, number] | null,
    b?: [number, number, number, number] | null
) => {
    if (!a || !b) return false;
    return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3]);
};



const fitLocalOverlay = (overlay: LocalRasterOverlay, duration = 1200) => {
    if (!map.value) return;
    const imageExtent = transformExtent(overlay.extent, 'EPSG:4326', 'EPSG:3857');
    map.value.getView().fit(imageExtent, {
        padding: [80, 80, 80, 80],
        duration,
        maxZoom: 7,
    });
};

const fitCatalogRegion = (regionId?: string, duration = 1000) => {
    if (!map.value || !regionId) return false;
    const region = findCatalogRegion(regionId);
    if (!region) return false;
    const extent = transformExtent(region.bbox, 'EPSG:4326', 'EPSG:3857');
    map.value.getView().fit(extent, {
        padding: [88, 88, 88, 88],
        duration,
        maxZoom: region.defaultZoom,
    });
    return true;
};

const enableCatalogLayers = (catalogId?: string) => {
    const catalogItem = findCatalogItem(catalogId);
    if (!catalogItem) return;

    catalogItem.layerBindings.forEach((binding) => {
        if (binding.key === 'heihe-sites') {
            layerConfig.value.heiheSites.visible = true;
            heiheSiteLayer?.setVisible(true);
        } else if (binding.key === 'heihe-observations') {
            layerConfig.value.heiheObservations.visible = true;
            heiheObservationLayer?.setVisible(true);
        } else if (binding.key === 'heihe-grassland-polygons') {
            layerConfig.value.grasslandPolygons.visible = true;
            grasslandPolygonLayer?.setVisible(true);
        } else if (binding.key === 'heihe-grassland-points') {
            layerConfig.value.grasslandPoints.visible = true;
            grasslandPointLayer?.setVisible(true);
        } else if (binding.key === FOREST_CARBON_LAYER_ID) {
            layerConfig.value.forestCarbon.visible = true;
            layers.value.find(l => l.get('id') === FOREST_CARBON_LAYER_ID)?.setVisible(true);
        } else if (binding.key === 'southwest-temperature-point') {
            localOverlayGuideLayer.setVisible(true);
        } else if (binding.key === 'central-asia-countries') {
            layerConfig.value.centralAsiaCountries.visible = true;
            centralAsiaCountriesLayer?.setVisible(true);
        } else if (binding.key === 'central-asia-urban-points') {
            layerConfig.value.centralAsiaUrbanPoints.visible = true;
            centralAsiaUrbanPointLayer?.setVisible(true);
        } else if (binding.key === 'central-asia-urban-polygons') {
            layerConfig.value.centralAsiaUrbanPolygons.visible = true;
            centralAsiaUrbanPolygonLayer?.setVisible(true);
        } else if (binding.key === 'badaling-imagery') {
            layerConfig.value.badalingImagery.visible = true;
            layers.value
                .filter((layer) => String(layer.get('id') || '').startsWith(BADALING_IMAGERY_LAYER_PREFIX))
                .forEach((layer) => layer.setVisible(true));
        } else if (binding.key === 'badaling-guide-point') {
            localOverlayGuideLayer.setVisible(true);
        } else if (binding.key === 'hepingjie-imagery') {
            layerConfig.value.hepingjieImagery.visible = true;
            layers.value
                .filter((layer) => String(layer.get('id') || '').startsWith(HEPINGJIE_IMAGERY_LAYER_PREFIX))
                .forEach((layer) => layer.setVisible(true));
        } else if (binding.key === 'hepingjie-guide-point') {
            localOverlayGuideLayer.setVisible(true);
        } else if (binding.key.startsWith('local-raster-')) {
            const overlayId = binding.key.replace('local-raster-', '');
            const layerKey = getLocalRasterLayerKey(overlayId);
            if (layerConfig.value[layerKey]) {
                layerConfig.value[layerKey].visible = true;
            }
            syncLocalRasterOverlayVisibility();
        }
    });
};

const applyCatalogRouteTarget = () => {
    const catalogId = route.query.catalog || route.query.layer;
    const regionId = route.query.region;
    const catalogKey = Array.isArray(catalogId) ? catalogId[0] : catalogId;
    const regionKey = Array.isArray(regionId) ? regionId[0] : regionId;

    if (typeof catalogKey === 'string') {
        const catalogItem = findCatalogItem(catalogKey);
        enableCatalogLayers(catalogKey);
        if (catalogItem && fitCatalogRegion(catalogItem.regionId)) {
            ElMessage.success(`已定位到：${catalogItem.title}`);
            return true;
        }
    }

    if (typeof regionKey === 'string' && fitCatalogRegion(regionKey)) {
        ElMessage.success(`已定位到：${findCatalogRegion(regionKey)?.name || regionKey}`);
        return true;
    }

    return false;
};

const syncLocalRasterOverlayVisibility = () => {
    if (!map.value) return;
    const zoom = map.value.getView().getZoom() ?? 0;
    localRasterOverlays.value.forEach((overlay) => {
        const layerKey = getLocalRasterLayerKey(overlay.id);
        const layer = layers.value.find(l => l.get('id') === getLocalRasterLayerId(overlay.id));
        const configuredVisible = layerConfig.value[layerKey]?.visible ?? true;
        const shouldShow = configuredVisible && zoom >= overlay.min_zoom;
        layer?.setVisible(shouldShow);
    });
};

const appendIndexFeaturesToSource = (source: VectorSource, items: GeoDataItem[]) => {
    items.forEach((item) => {
        if (item.index_point_enabled === false) {
            return;
        }
        if (typeof item.center_x !== 'number' || typeof item.center_y !== 'number') {
            return;
        }
        const coords = toMapCoords([item.center_x, item.center_y], item.srid);
        const feature = new Feature({
            geometry: new Point(coords),
            ...item
        });
        source.addFeature(feature);
    });
};

const localOverlayGuideSource = new VectorSource();
const localOverlayGuideLayer = new VectorLayer({
    source: localOverlayGuideSource,
    zIndex: 1004,
    updateWhileAnimating: true,
    style: (feature) => {
        const featureType = feature.get('guideType');
        const name = feature.get('name') || '';
        const isForestCarbon = feature.get('dataset_id') === 'china-forest-carbon-2002-2021';
        const borderColor = isForestCarbon ? 'rgba(28, 111, 62, 0.92)' : 'rgba(204, 59, 34, 0.95)';
        const fillColor = isForestCarbon ? 'rgba(28, 111, 62, 0.11)' : 'rgba(204, 59, 34, 0.14)';
        const textColor = isForestCarbon ? '#174a2b' : '#7a1f10';
        const pointColor = isForestCarbon ? '#1f7a42' : '#cc3b22';
        const pointTextColor = isForestCarbon ? '#163f27' : '#5c1b11';

        if (featureType === 'extent') {
            return new Style({
                stroke: new Stroke({
                    color: borderColor,
                    width: 4,
                    lineDash: [14, 8],
                }),
                fill: new Fill({
                    color: fillColor,
                }),
                text: new Text({
                    text: name,
                    font: 'bold 14px sans-serif',
                    fill: new Fill({ color: textColor }),
                    stroke: new Stroke({ color: 'rgba(255,255,255,0.95)', width: 4 }),
                    overflow: true,
                    offsetY: -14,
                }),
            });
        }

        return new Style({
            image: new CircleStyle({
                radius: 11,
                fill: new Fill({ color: pointColor }),
                stroke: new Stroke({ color: '#fff7f2', width: 3 }),
            }),
            text: new Text({
                text: name,
                font: 'bold 12px sans-serif',
                fill: new Fill({ color: pointTextColor }),
                stroke: new Stroke({ color: 'rgba(255,255,255,0.92)', width: 3 }),
                offsetY: -18,
                overflow: true,
            }),
        });
    }
});

const refreshLocalOverlayGuides = (overlays: LocalRasterOverlay[]) => {
    localOverlayGuideSource.clear();

    overlays.forEach((overlay) => {
        if (typeof overlay.center_x === 'number' && typeof overlay.center_y === 'number') {
            const centerFeature = new Feature({
                geometry: new Point(toMapCoords([overlay.center_x, overlay.center_y], overlay.srid)),
                guideType: 'center',
                name: '喜马拉雅 GeoTIFF 下载点',
                overlayId: overlay.id,
                type: 'GeoTIFF地质数据',
                sub_type: 'LocalRasterGuide',
                extent: overlay.extent,
                srid: overlay.srid,
                center_x: overlay.center_x,
                center_y: overlay.center_y,
                description: `${overlay.name} 的快速定位入口。放大到 ${overlay.min_zoom} 级后自动显示影像，可直接下载原始 TIF 数据。`,
                downloadable: true,
                overlay_id: overlay.id,
                source: 'local-overlay',
            });
            localOverlayGuideSource.addFeature(centerFeature);
        }
    });
};

const refreshForestCarbonGuide = (overlay: ForestCarbonOverlay) => {
    localOverlayGuideSource.getFeatures()
        .filter((feature) => feature.get('dataset_id') === 'china-forest-carbon-2002-2021')
        .forEach((feature) => localOverlayGuideSource.removeFeature(feature));

    if (typeof overlay.center_x === 'number' && typeof overlay.center_y === 'number') {
        const centerFeature = new Feature({
            geometry: new Point(toMapCoords([overlay.center_x, overlay.center_y], overlay.srid)),
            guideType: 'center',
            name: '森林碳储量索引点',
            type: '森林碳储量栅格',
            sub_type: 'ForestCarbonRasterGuide',
            dataset_id: overlay.dataset_id,
            extent: overlay.extent,
            srid: overlay.srid,
            center_x: overlay.center_x,
            center_y: overlay.center_y,
            description: `${overlay.name} 的快速定位与下载入口。`,
            downloadable: true,
            source: 'forest-carbon',
            metric: overlay.metric,
            year: overlay.year,
            metadata: overlay.metadata,
        });
        localOverlayGuideSource.addFeature(centerFeature);
    }
};

const refreshSouthwestTemperatureGuide = (dataset: SouthwestTemperatureDataset) => {
    localOverlayGuideSource.getFeatures()
        .filter((feature) => feature.get('dataset_id') === 'southwest-china-temperature-90ka')
        .forEach((feature) => localOverlayGuideSource.removeFeature(feature));

    const centerFeature = new Feature({
        geometry: new Point(toMapCoords([dataset.center_x, dataset.center_y], dataset.srid)),
        guideType: 'center',
        name: '西南温度数据集索引点',
        type: '定量温度数据',
        sub_type: 'SouthwestTemperatureDataset',
        dataset_id: dataset.dataset_id,
        extent: dataset.bbox,
        bbox: dataset.bbox,
        srid: dataset.srid,
        center_x: dataset.center_x,
        center_y: dataset.center_y,
        description: dataset.description,
        downloadable: true,
        source: 'southwest-temperature',
        time_range: dataset.time_range,
        metadata: dataset.metadata,
    });
    localOverlayGuideSource.addFeature(centerFeature);
};

const refreshBadalingImageryGuide = (dataset: BadalingImageryDataset) => {
    localOverlayGuideSource.getFeatures()
        .filter((feature) => feature.get('dataset_id') === 'badaling-town-imagery')
        .forEach((feature) => localOverlayGuideSource.removeFeature(feature));

    const centerFeature = new Feature({
        geometry: new Point(toMapCoords([dataset.center_x, dataset.center_y], dataset.srid)),
        guideType: 'center',
        name: '八达岭镇影像索引点',
        type: '分级遥感影像',
        sub_type: 'BadalingImageryDataset',
        dataset_id: dataset.dataset_id,
        extent: dataset.bbox,
        bbox: dataset.bbox,
        srid: dataset.srid,
        center_x: dataset.center_x,
        center_y: dataset.center_y,
        description: dataset.description,
        downloadable: true,
        source: 'badaling-imagery',
        time_range: dataset.time_range,
        metadata: dataset.metadata,
    });
    localOverlayGuideSource.addFeature(centerFeature);
};

const refreshHepingjieImageryGuide = (dataset: BadalingImageryDataset) => {
    localOverlayGuideSource.getFeatures()
        .filter((feature) => feature.get('dataset_id') === 'hepingjie-street-imagery')
        .forEach((feature) => localOverlayGuideSource.removeFeature(feature));

    const centerFeature = new Feature({
        geometry: new Point(toMapCoords([dataset.center_x, dataset.center_y], dataset.srid)),
        guideType: 'center',
        name: '和平街街道影像索引点',
        type: '分级遥感影像',
        sub_type: 'HepingjieImageryDataset',
        dataset_id: dataset.dataset_id,
        extent: dataset.bbox,
        bbox: dataset.bbox,
        srid: dataset.srid,
        center_x: dataset.center_x,
        center_y: dataset.center_y,
        description: dataset.description,
        downloadable: true,
        source: 'hepingjie-imagery',
        time_range: dataset.time_range,
        metadata: dataset.metadata,
    });
    localOverlayGuideSource.addFeature(centerFeature);
};

const setSelectedFeatureState = (feature: GeoDataItem | null) => {
  currentFeature.value = feature;
  if (feature?.id) {
    mapStore.selectFeature(feature);
  } else {
    mapStore.clearSelection();
  }
};

const getShareableSources = () => [
    geoPointSource,
    localOverlayGuideSource,
    heiheSiteSource,
    heiheObservationSource,
    grasslandPolygonSource,
    grasslandPointSource,
    centralAsiaCountriesSource,
    centralAsiaUrbanPolygonSource,
    centralAsiaUrbanPointSource,
];

const findSharedFeature = (query: Record<string, unknown>) => {
    const id = typeof query.id === 'string' ? query.id : '';
    const datasetId = typeof query.dataset === 'string' ? query.dataset : '';
    const overlayId = typeof query.overlay === 'string' ? query.overlay : '';
    const name = typeof query.name === 'string' ? query.name : '';

    for (const source of getShareableSources()) {
        const feature = source.getFeatures().find((candidate) => {
            const props = candidate.getProperties();
            if (id && String(props.id) === id) return true;
            if (datasetId && props.dataset_id === datasetId) return true;
            if (overlayId && props.overlay_id === overlayId) return true;
            if (name && props.name === name) return true;
            return false;
        });

        if (feature) {
            return {
                ...feature.getProperties(),
                geometry: feature.getGeometry(),
            } as GeoDataItem & { geometry?: any };
        }
    }

    return null;
};

const openSharedFeatureFromQuery = (coords: [number, number], zoom: number) => {
    const sharedFeature = findSharedFeature(route.query as Record<string, unknown>);
    const name = (route.query.name as string) || sharedFeature?.name || '目标位置';

    flyTo(coords, zoom);
    setNavigationMarker(coords, name, true);

    if (sharedFeature) {
        setSelectedFeatureState(sharedFeature as GeoDataItem);
        selectedItems.value = [sharedFeature as GeoDataItem];
        sidePanelVisible.value = true;

        highlightSource.clear();
        if (sharedFeature.geometry) {
            const clone = new Feature(sharedFeature.geometry.clone());
            const props = { ...sharedFeature };
            delete props.geometry;
            clone.setProperties(props);
            highlightSource.addFeature(clone);
        } else if (typeof sharedFeature.center_x === 'number' && typeof sharedFeature.center_y === 'number') {
            highlightSource.addFeature(new Feature(new Point(coords)));
        }
    }

    ElMessage.success(`已定位到: ${name}`);
};

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
                        setSelectedFeatureState(data[0]);
                        selectedItems.value = data;
                    } else {
                        setSelectedFeatureState(null);
                        selectedItems.value = data;
                        mapStore.selectFeatures(data);
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
    const url = `${window.location.origin}/map?lon=${lon}&lat=${lat}&z=${z}`;
    
    try {
      await copyTextToClipboard(url);
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

const copyTextToClipboard = async (text: string) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  textarea.remove();

  if (!copied) {
    throw new Error('Clipboard copy failed');
  }
};

const buildFeatureShareUrl = (item: GeoDataItem) => {
  const url = new URL('/map', window.location.origin);
  const catalogItem = item.dataset_id ? findCatalogItem(item.dataset_id) : undefined;
  const lon = typeof item.center_x === 'number' ? item.center_x : undefined;
  const lat = typeof item.center_y === 'number' ? item.center_y : undefined;
  const zoom = map.value?.getView().getZoom() ?? 14;

  url.searchParams.set('name', item.name || '地质数据');
  url.searchParams.set('z', zoom.toFixed(2));
  url.searchParams.set('share', 'feature');

  if (item.id !== undefined && item.id !== null) {
    url.searchParams.set('id', String(item.id));
  }
  if (item.dataset_id) {
    url.searchParams.set('dataset', item.dataset_id);
  }
  if (item.overlay_id) {
    url.searchParams.set('overlay', item.overlay_id);
  }
  if (catalogItem) {
    url.searchParams.set('catalog', catalogItem.id);
    url.searchParams.set('layer', catalogItem.id);
    url.searchParams.set('region', catalogItem.regionId);
  }
  if (typeof lon === 'number' && typeof lat === 'number') {
    url.searchParams.set('lon', lon.toFixed(6));
    url.searchParams.set('lat', lat.toFixed(6));
  }

  return url.toString();
};

const handleShareFeature = async (item: GeoDataItem) => {
  try {
    const url = buildFeatureShareUrl(item);
    await copyTextToClipboard(url);
    ElNotification({
      title: '分享成功',
      message: '地质点链接已复制到剪贴板',
      type: 'success',
      duration: 3000,
      offset: 80,
    });
  } catch (err) {
    console.error('Failed to share feature:', err);
    ElNotification({
      title: '复制失败',
      message: '浏览器拒绝剪贴板访问，请稍后重试',
      type: 'error',
      duration: 3000,
      offset: 80,
    });
  }
};

const tooltipContent = ref('');
const currentBaseMap = ref<'vector' | 'satellite'>('vector');
const navigationSource = new VectorSource();
const geoPointSource = new VectorSource();
const heiheSiteSource = new VectorSource();
const heiheObservationSource = new VectorSource();
const heiheObservationClusterSource = new Cluster({
  distance: 54,
  minDistance: 18,
  source: heiheObservationSource,
});
const grasslandPolygonSource = new VectorSource();
const grasslandPointSource = new VectorSource();
const grasslandPointClusterSource = new Cluster({
  distance: 66,
  minDistance: 22,
  source: grasslandPointSource,
});
const zoomLevel = ref(10);
let heiheSiteLayer: VectorLayer<VectorSource> | null = null;
let heiheObservationLayer: VectorLayer<Cluster> | null = null;
let grasslandPolygonLayer: VectorLayer<VectorSource> | null = null;
let grasslandPointLayer: VectorLayer<Cluster> | null = null;
const heiheGeoJSON = new GeoJSON();
const grasslandGeoJSON = new GeoJSON();
const heiheDatasetBBox = ref<[number, number, number, number] | null>(null);
const grasslandDatasetBBox = ref<[number, number, number, number] | null>(null);
const heiheQuickLocateVisible = ref(false);
const heiheSelectedSiteKey = ref<string | null>(null);
const grasslandSelectedId = ref<string | number | null>(null);
const GRASSLAND_POINT_MIN_ZOOM = 7;

const sidePanelTitle = computed(() => {
  if (isNearbyActive.value) return '周边分析结果';
  if (selectedItems.value.length > 1) return '批量操作';
  return currentFeature.value?.name || '详细信息';
});

const { source: highlightSource, layer: highlightLayer } = createHighlightLayer();
const { source: bufferSource, layer: bufferLayer } = createBufferLayer();

const layerConfig = ref<LayerConfig>({
  faults: { visible: true, opacity: 80, name: '矢量断裂带' },
  boreholes: { visible: true, opacity: 90, name: '钻孔分布点' },
  raster: { visible: true, opacity: 80, name: '栅格影像' },
  heiheSites: { visible: true, opacity: 95, name: '黑河站点汇总' },
  heiheObservations: { visible: true, opacity: 88, name: '黑河逐次观测' },
  grasslandPolygons: { visible: true, opacity: 62, name: '黑河草场分布面' },
  grasslandPoints: { visible: true, opacity: 92, name: '黑河草场索引点' },
  forestCarbon: { visible: true, opacity: 72, name: '森林碳储量栅格' },
  centralAsiaCountries: { visible: true, opacity: 68, name: '中亚国家边界' },
  centralAsiaUrbanPoints: { visible: true, opacity: 92, name: '中亚城镇索引点' },
  centralAsiaUrbanPolygons: { visible: true, opacity: 60, name: '中亚城镇分布面' },
  badalingImagery: { visible: true, opacity: 90, name: '八达岭镇分级影像' },
  hepingjieImagery: { visible: true, opacity: 90, name: '和平街街道分级影像' }
});

const syncHeiheQuickLocateVisibility = () => {
  if (!map.value || !heiheDatasetBBox.value) {
    heiheQuickLocateVisible.value = false;
    return;
  }

  const center = map.value.getView().getCenter();
  if (!center) {
    heiheQuickLocateVisible.value = false;
    return;
  }

  const [lon, lat] = toLonLat(center);
  const [minLon, minLat, maxLon, maxLat] = heiheDatasetBBox.value;
  heiheQuickLocateVisible.value = lon < minLon || lon > maxLon || lat < minLat || lat > maxLat;
};

const fitHeiheBBox = (bbox?: [number, number, number, number] | null, maxZoom = 12) => {
  if (!map.value || !bbox) return;
  const extent = transformExtent(bbox, 'EPSG:4326', 'EPSG:3857');
  map.value.getView().fit(extent, {
    padding: [90, 90, 90, 90],
    duration: 1000,
    maxZoom,
  });
};

const handleQuickLocateHeihe = () => {
  fitHeiheBBox(heiheDatasetBBox.value, 11);
};

const createHeiheSiteStyle = (feature: Feature) => {
  const isSelected = feature.get('site_key') === heiheSelectedSiteKey.value;
  return new Style({
    image: new CircleStyle({
      radius: isSelected ? 11 : 9,
      fill: new Fill({ color: '#2d5a27' }),
      stroke: new Stroke({
        color: isSelected ? '#cfe7b6' : 'rgba(255,255,255,0.96)',
        width: isSelected ? 4 : 3,
      }),
    }),
    text: new Text({
      text: String(feature.get('name') || ''),
      font: 'bold 12px sans-serif',
      offsetY: -18,
      fill: new Fill({ color: '#1f3f1a' }),
      stroke: new Stroke({ color: 'rgba(255,255,255,0.95)', width: 3 }),
      overflow: true,
    }),
  });
};

const createHeiheObservationStyle = (feature: Feature) => {
  const clusteredFeatures = feature.get('features') as Feature[] | undefined;
  const size = clusteredFeatures?.length || 1;

  if (size > 1) {
    const radius = Math.min(26, 12 + Math.sqrt(size) * 4);
    return new Style({
      image: new CircleStyle({
        radius,
        fill: new Fill({ color: 'rgba(45, 90, 39, 0.86)' }),
        stroke: new Stroke({ color: 'rgba(236, 248, 226, 0.96)', width: 3 }),
      }),
      text: new Text({
        text: String(size),
        font: 'bold 13px sans-serif',
        fill: new Fill({ color: '#ffffff' }),
        stroke: new Stroke({ color: 'rgba(31, 63, 26, 0.72)', width: 2 }),
      }),
    });
  }

  const originalFeature = clusteredFeatures?.[0] || feature;
  const siteKey = originalFeature.get('site_key');
  const isSelectedSite = siteKey && siteKey === heiheSelectedSiteKey.value;
  return new Style({
    image: new CircleStyle({
      radius: isSelectedSite ? 6 : 5,
      fill: new Fill({ color: isSelectedSite ? '#3d7d34' : 'rgba(45, 90, 39, 0.84)' }),
      stroke: new Stroke({ color: 'rgba(255,255,255,0.9)', width: 2 }),
    }),
  });
};

const getGrasslandColor = (feature: Feature) => {
  const mainType = String(feature.get('MAINTYPE') || feature.get('metadata')?.main_type || '');
  const grassType = String(feature.get('TYPE') || feature.get('metadata')?.grass_type || '');

  if (mainType.includes('草场') && !mainType.includes('非草场')) return '#5f8f3d';
  if (grassType.includes('灌丛')) return '#3f7f55';
  if (grassType.includes('草甸')) return '#6ba85a';
  if (grassType.includes('戈壁') || grassType.includes('裸露')) return '#b99a6b';
  if (grassType.includes('耕地')) return '#d7b85c';
  if (grassType.includes('水')) return '#5d95b8';
  return '#7d9b4f';
};

const createGrasslandPolygonStyle = (feature: Feature) => {
  const featureId = feature.get('id') || feature.get('GRASSF_ID');
  const selected = grasslandSelectedId.value !== null && String(featureId) === String(grasslandSelectedId.value);
  const color = getGrasslandColor(feature);

  return new Style({
    fill: new Fill({
      color: selected ? 'rgba(116, 161, 75, 0.48)' : `${color}66`,
    }),
    stroke: new Stroke({
      color: selected ? '#f3f7d5' : 'rgba(62, 95, 48, 0.72)',
      width: selected ? 3 : 1.2,
    }),
  });
};

const createGrasslandPointStyle = (feature: Feature) => {
  const clusteredFeatures = feature.get('features') as Feature[] | undefined;
  const size = clusteredFeatures?.length || 1;

  if (size > 1) {
    const radius = Math.min(28, 11 + Math.sqrt(size) * 3.6);
    return new Style({
      image: new CircleStyle({
        radius,
        fill: new Fill({ color: 'rgba(87, 129, 48, 0.88)' }),
        stroke: new Stroke({ color: 'rgba(255, 252, 232, 0.96)', width: 3 }),
      }),
      text: new Text({
        text: String(size),
        font: 'bold 13px sans-serif',
        fill: new Fill({ color: '#ffffff' }),
        stroke: new Stroke({ color: 'rgba(49, 72, 28, 0.78)', width: 2 }),
      }),
    });
  }

  const originalFeature = clusteredFeatures?.[0] || feature;
  const featureId = originalFeature.get('id') || originalFeature.get('GRASSF_ID');
  const selected = grasslandSelectedId.value !== null && String(featureId) === String(grasslandSelectedId.value);

  return new Style({
    image: new CircleStyle({
      radius: selected ? 7 : 5,
      fill: new Fill({ color: selected ? '#8fbd54' : 'rgba(87, 129, 48, 0.88)' }),
      stroke: new Stroke({ color: selected ? '#fff7cc' : 'rgba(255,255,255,0.9)', width: selected ? 3 : 2 }),
    }),
  });
};

const createCentralAsiaCountryStyle = (feature: Feature) => {
  const selected = centralAsiaSelectedId.value !== null && String(feature.get('id')) === String(centralAsiaSelectedId.value);
  return new Style({
    stroke: new Stroke({
      color: selected ? 'rgba(214, 170, 57, 0.98)' : 'rgba(120, 92, 45, 0.88)',
      width: selected ? 2.6 : 1.6,
    }),
    fill: new Fill({
      color: selected ? 'rgba(214, 170, 57, 0.12)' : 'rgba(194, 173, 127, 0.08)',
    }),
  });
};

const createCentralAsiaUrbanPolygonStyle = (feature: Feature) => {
  const selected = centralAsiaSelectedId.value !== null && String(feature.get('id')) === String(centralAsiaSelectedId.value);
  return new Style({
    stroke: new Stroke({
      color: selected ? 'rgba(255, 238, 178, 0.96)' : 'rgba(138, 73, 33, 0.82)',
      width: selected ? 2.8 : 1.1,
    }),
    fill: new Fill({
      color: selected ? 'rgba(199, 111, 47, 0.40)' : 'rgba(199, 111, 47, 0.22)',
    }),
  });
};

const createCentralAsiaUrbanPointStyle = (feature: Feature) => {
  const clusteredFeatures = feature.get('features') as Feature[] | undefined;
  const size = clusteredFeatures?.length || 1;

  if (size > 1) {
    const radius = Math.min(30, 12 + Math.sqrt(size) * 3.8);
    return new Style({
      image: new CircleStyle({
        radius,
        fill: new Fill({ color: 'rgba(173, 95, 34, 0.9)' }),
        stroke: new Stroke({ color: 'rgba(255, 246, 214, 0.96)', width: 3 }),
      }),
      text: new Text({
        text: String(size),
        font: 'bold 13px sans-serif',
        fill: new Fill({ color: '#ffffff' }),
        stroke: new Stroke({ color: 'rgba(99, 48, 15, 0.78)', width: 2 }),
      }),
    });
  }

  const originalFeature = clusteredFeatures?.[0] || feature;
  const featureId = originalFeature.get('id');
  const selected = centralAsiaSelectedId.value !== null && String(featureId) === String(centralAsiaSelectedId.value);

  return new Style({
    image: new CircleStyle({
      radius: selected ? 8 : 6,
      fill: new Fill({ color: selected ? '#d79a53' : 'rgba(173, 95, 34, 0.9)' }),
      stroke: new Stroke({ color: selected ? '#fff1c2' : 'rgba(255,255,255,0.92)', width: selected ? 3 : 2 }),
    }),
  });
};

const ensureHeiheLayers = () => {
  if (!map.value) return;

  if (!heiheSiteLayer) {
    heiheSiteLayer = new VectorLayer({
      source: heiheSiteSource,
      zIndex: 1001,
      style: (feature) => createHeiheSiteStyle(feature as Feature),
      visible: layerConfig.value.heiheSites.visible,
      opacity: layerConfig.value.heiheSites.opacity / 100,
    });
    heiheSiteLayer.set('id', 'heihe-sites');
    map.value.addLayer(heiheSiteLayer);
    layers.value = [...layers.value, heiheSiteLayer];
  }

  if (!heiheObservationLayer) {
    heiheObservationLayer = new VectorLayer({
      source: heiheObservationClusterSource,
      zIndex: 1000,
      style: (feature) => createHeiheObservationStyle(feature as Feature),
      visible: layerConfig.value.heiheObservations.visible,
      opacity: layerConfig.value.heiheObservations.opacity / 100,
    });
    heiheObservationLayer.set('id', 'heihe-observations');
    map.value.addLayer(heiheObservationLayer);
    layers.value = [...layers.value, heiheObservationLayer];
  }
};

const ensureGrasslandLayers = () => {
  if (!map.value) return;

  if (!grasslandPolygonLayer) {
    grasslandPolygonLayer = new VectorLayer({
      source: grasslandPolygonSource,
      zIndex: 940,
      style: (feature) => createGrasslandPolygonStyle(feature as Feature),
      visible: layerConfig.value.grasslandPolygons.visible,
      opacity: layerConfig.value.grasslandPolygons.opacity / 100,
    });
    grasslandPolygonLayer.set('id', 'heihe-grassland-polygons');
    map.value.addLayer(grasslandPolygonLayer);
    layers.value = [...layers.value, grasslandPolygonLayer];
  }

  if (!grasslandPointLayer) {
    grasslandPointLayer = new VectorLayer({
      source: grasslandPointClusterSource,
      zIndex: 1001,
      minZoom: GRASSLAND_POINT_MIN_ZOOM - 0.01,
      style: (feature) => createGrasslandPointStyle(feature as Feature),
      visible: layerConfig.value.grasslandPoints.visible,
      opacity: layerConfig.value.grasslandPoints.opacity / 100,
    });
    grasslandPointLayer.set('id', 'heihe-grassland-points');
    map.value.addLayer(grasslandPointLayer);
    layers.value = [...layers.value, grasslandPointLayer];
  }
};

const ensureCentralAsiaLayers = () => {
  if (!map.value) return;

  if (!centralAsiaCountriesLayer) {
    centralAsiaCountriesLayer = new VectorLayer({
      source: centralAsiaCountriesSource,
      zIndex: 930,
      style: (feature) => createCentralAsiaCountryStyle(feature as Feature),
      visible: layerConfig.value.centralAsiaCountries.visible,
      opacity: layerConfig.value.centralAsiaCountries.opacity / 100,
    });
    centralAsiaCountriesLayer.set('id', 'central-asia-countries');
    map.value.addLayer(centralAsiaCountriesLayer);
    layers.value = [...layers.value, centralAsiaCountriesLayer];
  }

  if (!centralAsiaUrbanPolygonLayer) {
    centralAsiaUrbanPolygonLayer = new VectorLayer({
      source: centralAsiaUrbanPolygonSource,
      zIndex: 955,
      minZoom: CENTRAL_ASIA_POLYGON_MIN_ZOOM - 0.01,
      style: (feature) => createCentralAsiaUrbanPolygonStyle(feature as Feature),
      visible: layerConfig.value.centralAsiaUrbanPolygons.visible,
      opacity: layerConfig.value.centralAsiaUrbanPolygons.opacity / 100,
    });
    centralAsiaUrbanPolygonLayer.set('id', 'central-asia-urban-polygons');
    map.value.addLayer(centralAsiaUrbanPolygonLayer);
    layers.value = [...layers.value, centralAsiaUrbanPolygonLayer];
  }

  if (!centralAsiaUrbanPointLayer) {
    centralAsiaUrbanPointLayer = new VectorLayer({
      source: centralAsiaUrbanPointClusterSource,
      zIndex: 1002,
      minZoom: CENTRAL_ASIA_POINT_MIN_ZOOM - 0.01,
      style: (feature) => createCentralAsiaUrbanPointStyle(feature as Feature),
      visible: layerConfig.value.centralAsiaUrbanPoints.visible,
      opacity: layerConfig.value.centralAsiaUrbanPoints.opacity / 100,
    });
    centralAsiaUrbanPointLayer.set('id', 'central-asia-urban-points');
    map.value.addLayer(centralAsiaUrbanPointLayer);
    layers.value = [...layers.value, centralAsiaUrbanPointLayer];
  }
};

const loadHeiheSites = async () => {
  const response = await geoDataApi.getHeiheGeoJSON('sites');
  heiheSiteSource.clear();
  if (response.bbox) {
    heiheDatasetBBox.value = response.bbox;
  }

  const features = heiheGeoJSON.readFeatures(response as any, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });
  heiheSiteSource.addFeatures(features);
  syncHeiheQuickLocateVisibility();
};

const loadHeiheObservations = async (siteKey: string) => {
  const response = await geoDataApi.getHeiheGeoJSON('observations', siteKey);
  heiheObservationSource.clear();
  const features = heiheGeoJSON.readFeatures(response as any, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });
  heiheObservationSource.addFeatures(features);
  heiheSelectedSiteKey.value = siteKey;
  heiheSiteLayer?.changed();
  heiheObservationLayer?.changed();
};

const loadHeiheGrassland = async () => {
  const [polygons, points] = await Promise.all([
    geoDataApi.getHeiheGrasslandGeoJSON('polygons'),
    geoDataApi.getHeiheGrasslandGeoJSON('points'),
  ]);

  grasslandPolygonSource.clear();
  grasslandPointSource.clear();

  if (polygons.bbox) {
    grasslandDatasetBBox.value = polygons.bbox;
  }

  const polygonFeatures = grasslandGeoJSON.readFeatures(polygons as any, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });
  const pointFeatures = grasslandGeoJSON.readFeatures(points as any, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });

  grasslandPolygonSource.addFeatures(polygonFeatures);
  grasslandPointSource.addFeatures(pointFeatures);
};

const loadCentralAsiaCountries = async () => {
  const response = await geoDataApi.getCentralAsiaDesertGeoJSON('countries');
  centralAsiaCountriesSource.clear();
  if (response.bbox) {
    centralAsiaDatasetBBox.value = response.bbox;
  }
  const features = centralAsiaGeoJSON.readFeatures(response as any, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });
  centralAsiaCountriesSource.addFeatures(features);
};

const loadCentralAsiaViewportData = async (force = false) => {
  const bbox = getCurrentMapBBox();
  if (!bbox || !centralAsiaDatasetBBox.value || !bboxIntersects(bbox, centralAsiaDatasetBBox.value)) {
    centralAsiaUrbanPolygonSource.clear();
    centralAsiaUrbanPointSource.clear();
    centralAsiaPolygonBBoxKey.value = '';
    centralAsiaPointBBoxKey.value = '';
    return;
  }

  const zoom = map.value?.getView().getZoom() ?? 0;
  const bboxKey = buildBBoxKey(bbox);
  const shouldLoadPoints = layerConfig.value.centralAsiaUrbanPoints.visible && zoom >= CENTRAL_ASIA_POINT_MIN_ZOOM;
  const shouldLoadPolygons = layerConfig.value.centralAsiaUrbanPolygons.visible && zoom >= CENTRAL_ASIA_POLYGON_MIN_ZOOM;

  if (!shouldLoadPoints) {
    centralAsiaUrbanPointSource.clear();
    centralAsiaPointBBoxKey.value = '';
  }
  if (!shouldLoadPolygons) {
    centralAsiaUrbanPolygonSource.clear();
    centralAsiaPolygonBBoxKey.value = '';
  }

  const tasks: Promise<void>[] = [];

  if (shouldLoadPoints && (force || bboxKey !== centralAsiaPointBBoxKey.value)) {
    tasks.push((async () => {
      const response: CentralAsiaDesertGeoJSONResponse = await geoDataApi.getCentralAsiaDesertGeoJSON('urban-points', bbox);
      centralAsiaUrbanPointSource.clear();
      const features = centralAsiaGeoJSON.readFeatures(response as any, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      });
      centralAsiaUrbanPointSource.addFeatures(features);
      centralAsiaPointBBoxKey.value = bboxKey;
    })());
  }

  if (shouldLoadPolygons && (force || bboxKey !== centralAsiaPolygonBBoxKey.value)) {
    tasks.push((async () => {
      const response: CentralAsiaDesertGeoJSONResponse = await geoDataApi.getCentralAsiaDesertGeoJSON('urban-polygons', bbox);
      centralAsiaUrbanPolygonSource.clear();
      const features = centralAsiaGeoJSON.readFeatures(response as any, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      });
      centralAsiaUrbanPolygonSource.addFeatures(features);
      centralAsiaPolygonBBoxKey.value = bboxKey;
    })());
  }

  if (tasks.length > 0) {
    await Promise.all(tasks);
  }
};

const shouldFetchCentralAsiaViewportData = (force = false) => {
  const bbox = getCurrentMapBBox();
  if (!bbox || !centralAsiaDatasetBBox.value || !bboxIntersects(bbox, centralAsiaDatasetBBox.value)) {
    return false;
  }

  const zoom = map.value?.getView().getZoom() ?? 0;
  const bboxKey = buildBBoxKey(bbox);
  const shouldLoadPoints = layerConfig.value.centralAsiaUrbanPoints.visible && zoom >= CENTRAL_ASIA_POINT_MIN_ZOOM;
  const shouldLoadPolygons = layerConfig.value.centralAsiaUrbanPolygons.visible && zoom >= CENTRAL_ASIA_POLYGON_MIN_ZOOM;

  if (force) {
    return shouldLoadPoints || shouldLoadPolygons;
  }

  return (
    (shouldLoadPoints && bboxKey !== centralAsiaPointBBoxKey.value) ||
    (shouldLoadPolygons && bboxKey !== centralAsiaPolygonBBoxKey.value)
  );
};

const fitFeatureOnMap = (feature: any) => {
  if (!map.value) return;

  if (feature?.bbox && Array.isArray(feature.bbox) && feature.bbox.length === 4) {
    fitHeiheBBox(feature.bbox as [number, number, number, number], 13);
    return;
  }

  if (feature?.extent && Array.isArray(feature.extent) && feature.extent.length === 4) {
    try {
      const sourceProjection = feature.srid === 3857 ? 'EPSG:3857' : `EPSG:${feature.srid || 4326}`;
      const extent = sourceProjection === 'EPSG:3857'
        ? feature.extent
        : transformExtent(feature.extent, sourceProjection, 'EPSG:3857');
      map.value.getView().fit(extent, { padding: [90, 90, 90, 90], duration: 900, maxZoom: 13 });
      return;
    } catch (error) {
      console.warn('Failed to fit feature extent:', error);
    }
  }

  if (typeof feature?.center_x === 'number' && typeof feature?.center_y === 'number') {
    const coords = toMapCoords([feature.center_x, feature.center_y], feature.srid || 4326);
    map.value.getView().fit([coords[0] - 200, coords[1] - 200, coords[0] + 200, coords[1] + 200], {
      padding: [90, 90, 90, 90],
      duration: 900,
      maxZoom: 13,
    });
  }
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

const loadLocalRasterOverlays = async () => {
    try {
        const overlays = await geoDataApi.getLocalRasterOverlays();
        localRasterOverlays.value = overlays;
        refreshLocalOverlayGuides(overlays);

        for (const overlay of overlays) {
            const layerId = getLocalRasterLayerId(overlay.id);
            const imageExtent = transformExtent(overlay.extent, 'EPSG:4326', 'EPSG:3857');
            const token = localStorage.getItem('token');

            addGeoTiffOverlayLayer({
                id: layerId,
                url: geoDataApi.getLocalRasterFileUrl(overlay.id),
                extent: imageExtent as [number, number, number, number],
                opacity: overlay.opacity / 100,
                zIndex: 910,
                minZoom: overlay.min_zoom,
                visible: false,
                nodata: overlay.nodata,
                bandCount: overlay.band_count,
                rasterMin: overlay.raster_min,
                rasterMax: overlay.raster_max,
                token,
            });

            layerConfig.value[getLocalRasterLayerKey(overlay.id)] = {
                visible: true,
                opacity: overlay.opacity,
                name: overlay.name,
            };
        }

        syncLocalRasterOverlayVisibility();

        if (overlays.length > 0) {
            const [overlay] = overlays;
            const hasExplicitView =
                Boolean(route.query.lat && route.query.lon) ||
                Boolean(route.query.x && route.query.y);
            if (!hasExplicitView && !hasAutoFocusedLocalOverlay.value) {
                fitLocalOverlay(overlay);
                hasAutoFocusedLocalOverlay.value = true;
            }
            ElNotification({
                title: '本地地形影像已挂载',
                message: `已找到 ${overlay.name}，缩放到 ${overlay.min_zoom} 级后会自动显示地质影像，可点击边界或中心点下载 TIF。`,
                type: 'success',
                duration: 4200,
                offset: 80,
            });
        }
    } catch (error) {
        console.warn('Failed to load local raster overlays:', error);
        ElMessage.error('本地 TIF 影像加载失败，请检查登录状态或影像文件权限');
    }
};

const loadForestCarbonOverlay = async (fitToLayer = false) => {
    try {
        const overlay = await geoDataApi.getForestCarbonOverlay(forestCarbonMetric.value, forestCarbonYear.value);
        forestCarbonOverlay.value = overlay;
        const imageExtent = transformExtent(overlay.extent, 'EPSG:4326', 'EPSG:3857');
        const token = localStorage.getItem('token');

        addGeoTiffOverlayLayer({
            id: FOREST_CARBON_LAYER_ID,
            url: geoDataApi.getForestCarbonRasterUrl(overlay.metric, overlay.year),
            extent: imageExtent as [number, number, number, number],
            opacity: layerConfig.value.forestCarbon.opacity / 100,
            zIndex: 905,
            minZoom: overlay.min_zoom,
            visible: layerConfig.value.forestCarbon.visible,
            nodata: overlay.nodata ?? undefined,
            bandCount: overlay.band_count,
            rasterMin: overlay.raster_min,
            rasterMax: overlay.raster_max,
            colorRamp: 'carbon',
            token,
        });

        layerConfig.value.forestCarbon.name = `${overlay.metric_label} ${overlay.year}`;
        refreshForestCarbonGuide(overlay);

        if (fitToLayer && map.value) {
            map.value.getView().fit(imageExtent, {
                padding: [86, 86, 86, 86],
                duration: 900,
                maxZoom: overlay.min_zoom,
            });
        }
    } catch (error: any) {
        console.error('Failed to load forest carbon overlay:', error);
        ElMessage.error(error?.message || '森林碳储量栅格加载失败');
    }
};

const handleForestCarbonChange = async () => {
    await withMapLoading(async () => {
        await loadForestCarbonOverlay(false);
    });
};

const loadSouthwestTemperatureDataset = async () => {
    try {
        const dataset = await geoDataApi.getSouthwestTemperatureDataset();
        southwestTemperatureDataset.value = dataset;
        refreshSouthwestTemperatureGuide(dataset);
    } catch (error: any) {
        console.error('Failed to load southwest temperature dataset:', error);
        ElMessage.error(error?.message || '西南温度数据集加载失败');
    }
};

const loadBadalingImageryDataset = async () => {
    try {
        const dataset = await geoDataApi.getBadalingImageryDataset();
        badalingImageryDataset.value = dataset;
        refreshBadalingImageryGuide(dataset);
        const token = localStorage.getItem('token');

        dataset.levels.forEach((levelInfo) => {
            levelInfo.tiles.forEach((tile) => {
                const imageExtent = transformExtent(tile.extent, 'EPSG:4326', 'EPSG:3857');
                addGeoTiffOverlayLayer({
                    id: getBadalingLayerId(levelInfo.level, tile.tile_id),
                    url: geoDataApi.getBadalingImageryRasterUrl(levelInfo.level, tile.tile_id),
                    extent: imageExtent as [number, number, number, number],
                    opacity: layerConfig.value.badalingImagery.opacity / 100,
                    zIndex: 912,
                    minZoom: levelInfo.min_zoom,
                    maxZoom: levelInfo.max_zoom ?? undefined,
                    visible: layerConfig.value.badalingImagery.visible,
                    bandCount: tile.band_count,
                    token,
                });
            });
        });
    } catch (error: any) {
        console.error('Failed to load Badaling imagery dataset:', error);
        ElMessage.error(error?.message || '八达岭镇影像加载失败');
    }
};

const loadHepingjieImageryDataset = async () => {
    try {
        const dataset = await geoDataApi.getHepingjieImageryDataset();
        hepingjieImageryDataset.value = dataset;
        refreshHepingjieImageryGuide(dataset);
        const token = localStorage.getItem('token');

        dataset.levels.forEach((levelInfo) => {
            levelInfo.tiles.forEach((tile) => {
                const imageExtent = transformExtent(tile.extent, 'EPSG:4326', 'EPSG:3857');
                addGeoTiffOverlayLayer({
                    id: getHepingjieLayerId(levelInfo.level, tile.tile_id),
                    url: geoDataApi.getHepingjieImageryRasterUrl(levelInfo.level, tile.tile_id),
                    extent: imageExtent as [number, number, number, number],
                    opacity: layerConfig.value.hepingjieImagery.opacity / 100,
                    zIndex: 913,
                    minZoom: levelInfo.min_zoom,
                    maxZoom: levelInfo.max_zoom ?? undefined,
                    visible: layerConfig.value.hepingjieImagery.visible,
                    bandCount: tile.band_count,
                    token,
                });
            });
        });
    } catch (error: any) {
        console.error('Failed to load Hepingjie imagery dataset:', error);
        ElMessage.error(error?.message || '和平街街道影像加载失败');
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
            syncHeiheQuickLocateVisibility();
            syncLocalRasterOverlayVisibility();
            void refreshViewportGeoData();
            if (shouldFetchCentralAsiaViewportData(false)) {
              void withMapLoading(async () => {
                await loadCentralAsiaViewportData(false);
              });
            } else {
              void loadCentralAsiaViewportData(false);
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
          ensureHeiheLayers();
          ensureGrasslandLayers();
          ensureCentralAsiaLayers();

          // Load Data
          console.log('Loading geo data...');
          await withMapLoading(async () => {
            await loadGeoData(geoPointSource);
            await loadLocalRasterOverlays();
            await loadForestCarbonOverlay(false);
            await loadHeiheSites();
            await loadHeiheGrassland();
            await loadSouthwestTemperatureDataset();
            await loadBadalingImageryDataset();
            await loadHepingjieImageryDataset();
            await loadCentralAsiaCountries();
            await loadCentralAsiaViewportData(true);
          });

          // Check Route Query for FlyTo or Initial View
          // Priority: 1. ID/Name (Gallery) 2. Lon/Lat/Z (Share)
          const handledCatalogTarget = applyCatalogRouteTarget();

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
                      if (route.query.share === 'feature' || route.query.id || route.query.dataset || route.query.overlay) {
                          openSharedFeatureFromQuery(coords, zoom);
                      } else {
                          // Share view logic: Direct setCenter for instant restore
                          mapInstance.getView().setCenter(coords);
                          mapInstance.getView().setZoom(zoom);
                          if (!handledCatalogTarget) {
                              ElMessage.success('已恢复分享视图');
                          }
                      }
                  }, 500);
              }
          }

          // Init Interactions
          console.log('Initializing interactions...');
          if (map.value) {
            map.value.addLayer(highlightLayer);
            map.value.addLayer(bufferLayer);
            map.value.addLayer(localOverlayGuideLayer);
          }

          initInteractions(
            async (featureProps) => {
                // Feature Click Handler
                console.log('Feature clicked:', featureProps);
                highlightSource.clear();
                if (featureProps?.geometry) {
                  const clone = new Feature(featureProps.geometry.clone());
                  const props = { ...featureProps };
                  delete props.geometry;
                  clone.setProperties(props);
                  highlightSource.addFeature(clone);
                }

                if (featureProps?.dataset_id === 'heihe-soil-respiration') {
                    fitFeatureOnMap(featureProps);
                    if (featureProps.site_key && featureProps.sub_type === 'HeiheSite') {
                        try {
                            await loadHeiheObservations(featureProps.site_key);
                        } catch (error: any) {
                            console.error('Failed to load Heihe observations:', error);
                            ElMessage.error(error?.message || '黑河观测点加载失败');
                        }
                    }
                } else if (featureProps?.dataset_id === 'heihe-grassland-1988') {
                    grasslandSelectedId.value = featureProps.id ?? featureProps.GRASSF_ID ?? null;
                    grasslandPolygonLayer?.changed();
                    grasslandPointLayer?.changed();
                    fitFeatureOnMap(featureProps);
                } else if (featureProps?.dataset_id === 'central-asia-desert-urban-2012-2016') {
                    centralAsiaSelectedId.value = featureProps.id ?? null;
                    centralAsiaCountriesLayer?.changed();
                    centralAsiaUrbanPolygonLayer?.changed();
                    centralAsiaUrbanPointLayer?.changed();
                    fitFeatureOnMap(featureProps);
                } else if (featureProps?.dataset_id === 'badaling-town-imagery') {
                    fitFeatureOnMap(featureProps);
                } else if (featureProps?.dataset_id === 'hepingjie-street-imagery') {
                    fitFeatureOnMap(featureProps);
                } else if (featureProps?.dataset_id === 'china-forest-carbon-2002-2021') {
                    fitFeatureOnMap(featureProps);
                }
                setSelectedFeatureState(featureProps as GeoDataItem);
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
                        setSelectedFeatureState(selected[0]);
                        selectedItems.value = selected; // InfoPanel might ignore this due to v-if, but good to keep
                    } else {
                        // Multi selection
                        setSelectedFeatureState(null);
                        selectedItems.value = selected;
                        mapStore.selectFeatures(selected);
                    }
                    sidePanelVisible.value = true;
                } else {
                    ElMessage.info('该区域内未找到点位');
                }
            },
            () => {
                // Blank Click Handler
                if (!isNearbyActive.value) {
                    setSelectedFeatureState(null);
                    sidePanelVisible.value = false;
                    highlightSource.clear(); // Clear highlights
                    grasslandSelectedId.value = null;
                    grasslandPolygonLayer?.changed();
                    grasslandPointLayer?.changed();
                    centralAsiaSelectedId.value = null;
                    centralAsiaCountriesLayer?.changed();
                    centralAsiaUrbanPolygonLayer?.changed();
                    centralAsiaUrbanPointLayer?.changed();
                    bufferSource.clear();
                }
            }
          );

          if (mouseTooltipRef.value) {
              initTooltip(mouseTooltipRef.value);
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
const handleSmartSearchResult = (results: GeoDataItem[]) => {
  if (!results || results.length === 0) return;
  
  // Clear previous
  highlightSource.clear();
  selectedItems.value = results;
  
  // Add markers
  const features: Feature[] = [];
  results.forEach(item => {
      if (item.center_x && item.center_y) {
          const coords = toMapCoords([item.center_x, item.center_y], item.srid);
          const f = new Feature(new Point(coords));
          f.setProperties(item);
          highlightSource.addFeature(f);
          features.push(f);
      }
  });
  
  // Fit view
  if (features.length > 0) {
      const extent = highlightSource.getExtent();
      if (!extent.some(isNaN)) {
          map.value?.getView().fit(extent, { padding: [100, 100, 100, 100], duration: 1000 });
      }
  }
  
  // Show side panel
  if (results.length === 1) {
      setSelectedFeatureState(results[0]);
  } else {
      setSelectedFeatureState(null); // Multi mode
      mapStore.selectFeatures(results);
  }
  sidePanelVisible.value = true;
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
        } else if (key === 'heiheSites') {
            heiheSiteLayer?.setVisible(visible);
        } else if (key === 'heiheObservations') {
            heiheObservationLayer?.setVisible(visible);
        } else if (key === 'grasslandPolygons') {
            grasslandPolygonLayer?.setVisible(visible);
        } else if (key === 'grasslandPoints') {
            grasslandPointLayer?.setVisible(visible);
        } else if (key === 'forestCarbon') {
            layers.value.find(l => l.get('id') === FOREST_CARBON_LAYER_ID)?.setVisible(visible);
        } else if (key === 'centralAsiaCountries') {
            centralAsiaCountriesLayer?.setVisible(visible);
        } else if (key === 'centralAsiaUrbanPoints') {
            centralAsiaUrbanPointLayer?.setVisible(visible);
            if (shouldFetchCentralAsiaViewportData(true)) {
                void withMapLoading(async () => {
                    await loadCentralAsiaViewportData(true);
                });
            } else {
                void loadCentralAsiaViewportData(true);
            }
        } else if (key === 'centralAsiaUrbanPolygons') {
            centralAsiaUrbanPolygonLayer?.setVisible(visible);
            if (shouldFetchCentralAsiaViewportData(true)) {
                void withMapLoading(async () => {
                    await loadCentralAsiaViewportData(true);
                });
            } else {
                void loadCentralAsiaViewportData(true);
            }
        } else if (key === 'badalingImagery') {
            layers.value
                .filter((layer) => String(layer.get('id') || '').startsWith(BADALING_IMAGERY_LAYER_PREFIX))
                .forEach((layer) => layer.setVisible(visible));
        } else if (key === 'hepingjieImagery') {
            layers.value
                .filter((layer) => String(layer.get('id') || '').startsWith(HEPINGJIE_IMAGERY_LAYER_PREFIX))
                .forEach((layer) => layer.setVisible(visible));
        } else {
            const overlayId = getOverlayIdFromLayerKey(key);
            if (overlayId) {
                syncLocalRasterOverlayVisibility();
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
        } else if (key === 'heiheSites') {
            heiheSiteLayer?.setOpacity(val);
        } else if (key === 'heiheObservations') {
            heiheObservationLayer?.setOpacity(val);
        } else if (key === 'grasslandPolygons') {
            grasslandPolygonLayer?.setOpacity(val);
        } else if (key === 'grasslandPoints') {
            grasslandPointLayer?.setOpacity(val);
        } else if (key === 'forestCarbon') {
            layers.value.find(l => l.get('id') === FOREST_CARBON_LAYER_ID)?.setOpacity(val);
        } else if (key === 'centralAsiaCountries') {
            centralAsiaCountriesLayer?.setOpacity(val);
        } else if (key === 'centralAsiaUrbanPoints') {
            centralAsiaUrbanPointLayer?.setOpacity(val);
        } else if (key === 'centralAsiaUrbanPolygons') {
            centralAsiaUrbanPolygonLayer?.setOpacity(val);
        } else if (key === 'badalingImagery') {
            layers.value
                .filter((layer) => String(layer.get('id') || '').startsWith(BADALING_IMAGERY_LAYER_PREFIX))
                .forEach((layer) => layer.setOpacity(val));
        } else if (key === 'hepingjieImagery') {
            layers.value
                .filter((layer) => String(layer.get('id') || '').startsWith(HEPINGJIE_IMAGERY_LAYER_PREFIX))
                .forEach((layer) => layer.setOpacity(val));
        } else {
            const overlayId = getOverlayIdFromLayerKey(key);
            if (overlayId) {
                const layer = layers.value.find(l => l.get('id') === getLocalRasterLayerId(overlayId));
                if (layer) {
                    layer.setOpacity(val);
                }
            }
        }
    }
};

const loadGeoData = async (source: VectorSource) => {
    try {
        const bbox = getCurrentMapBBox();
        const bboxKey = buildBBoxKey(bbox);
        await geodataStore.fetchList(bbox);
        if (geodataStore.error) {
            throw new Error(geodataStore.error);
        }

        const data = geodataStore.items || [];
        
        if (data.length === 0) {
            console.warn('No geo data returned from API');
        }

        source.clear();
        appendIndexFeaturesToSource(source, data);
        lastDataBBoxKey.value = bboxKey;
        console.log(`Loaded ${source.getFeatures().length} features into source`);
    } catch (e: any) {
        console.error('Failed to load geo data:', e);
        ElMessage.error(`数据加载失败: ${e.message || '请检查接口权限'}`);
    }
};

const refreshViewportGeoData = async () => {
    const bbox = getCurrentMapBBox();
    const bboxKey = buildBBoxKey(bbox);
    if (!bboxKey || bboxKey === lastDataBBoxKey.value) {
        return;
    }
    await withMapLoading(async () => {
        await loadGeoData(geoPointSource);
    });
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

// Removed duplicate handleLogout

const closeSidePanel = () => {
    sidePanelVisible.value = false;
    setSelectedFeatureState(null);
    highlightSource.clear();
    grasslandSelectedId.value = null;
    grasslandPolygonLayer?.changed();
    grasslandPointLayer?.changed();
    centralAsiaSelectedId.value = null;
    centralAsiaCountriesLayer?.changed();
    centralAsiaUrbanPolygonLayer?.changed();
    centralAsiaUrbanPointLayer?.changed();
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
    if (item.downloadable === false) {
        ElMessage.info('该点用于定位图层范围，不提供文件下载');
        return;
    }
    try {
        const isLocalRaster = item.source === 'local-overlay' && item.overlay_id;
        const isHeiheDataset = item.dataset_id === 'heihe-soil-respiration';
        const isGrasslandDataset = item.dataset_id === 'heihe-grassland-1988';
        const isForestCarbonDataset = item.dataset_id === 'china-forest-carbon-2002-2021';
        const isSouthwestTemperatureDataset = item.dataset_id === 'southwest-china-temperature-90ka';
        const isCentralAsiaDataset = item.dataset_id === 'central-asia-desert-urban-2012-2016';
        const isBadalingDataset = item.dataset_id === 'badaling-town-imagery';
        const isHepingjieDataset = item.dataset_id === 'hepingjie-street-imagery';
        const blob = isHeiheDataset
            ? await geoDataApi.downloadHeiheDataset()
            : isGrasslandDataset
              ? await geoDataApi.downloadHeiheGrasslandDataset()
            : isForestCarbonDataset
              ? await geoDataApi.downloadForestCarbonRaster((item.metric || forestCarbonMetric.value) as 'AGBC' | 'BGBC', Number(item.year || forestCarbonYear.value))
            : isSouthwestTemperatureDataset
              ? await geoDataApi.downloadSouthwestTemperatureDataset()
            : isCentralAsiaDataset
              ? await geoDataApi.downloadCentralAsiaDesertDataset()
            : isBadalingDataset
              ? await geoDataApi.downloadBadalingImageryDataset()
            : isHepingjieDataset
              ? await geoDataApi.downloadHepingjieImageryDataset()
            : isLocalRaster
              ? await geoDataApi.downloadLocalRasterOverlay(item.overlay_id!)
              : await geoDataApi.downloadBatch([item.id]);
        const filename = isLocalRaster
            ? `${item.name || item.overlay_id}.tif`
            : isHeiheDataset
              ? 'heihe_soil_respiration_raw_dataset.zip'
            : isGrasslandDataset
              ? 'heihe_grassland_1988_raw_dataset.zip'
            : isForestCarbonDataset
              ? `${item.metric || forestCarbonMetric.value}Y${item.year || forestCarbonYear.value}.tif`
            : isSouthwestTemperatureDataset
              ? (southwestTemperatureDataset.value?.file_name || 'southwest_temperature_dataset.xlsx')
            : isCentralAsiaDataset
              ? 'central_asia_desert_urban_2012_2016_raw_dataset.zip'
            : isBadalingDataset
              ? 'badaling_town_imagery_raw_dataset.zip'
            : isHepingjieDataset
              ? 'hepingjie_street_imagery_raw_dataset.zip'
            : `${item.name || 'geodata'}.zip`;
        downloadBlob(blob, filename);
    } catch (e: any) {
        ElMessage.error(e?.message || '下载失败');
    }
};

const handlePreview = (item: GeoDataItem) => {
    if (item.dataset_id === 'heihe-soil-respiration') {
        fitFeatureOnMap(item);
        if (item.site_key && item.sub_type === 'HeiheSite') {
            loadHeiheObservations(item.site_key);
        }
        return;
    }

    if (item.dataset_id === 'heihe-grassland-1988') {
        grasslandSelectedId.value = item.id ?? null;
        grasslandPolygonLayer?.changed();
        grasslandPointLayer?.changed();
        fitFeatureOnMap(item);
        return;
    }

    if (item.dataset_id === 'central-asia-desert-urban-2012-2016') {
        centralAsiaSelectedId.value = item.id ?? null;
        centralAsiaCountriesLayer?.changed();
        centralAsiaUrbanPolygonLayer?.changed();
        centralAsiaUrbanPointLayer?.changed();
        fitFeatureOnMap(item);
        return;
    }

    if (item.dataset_id === 'badaling-town-imagery') {
        fitFeatureOnMap(item);
        return;
    }

    if (item.dataset_id === 'hepingjie-street-imagery') {
        fitFeatureOnMap(item);
        return;
    }

    if (item.dataset_id === 'china-forest-carbon-2002-2021') {
        fitFeatureOnMap(item);
        return;
    }

    if (item.dataset_id === 'southwest-china-temperature-90ka') {
        fitFeatureOnMap(item);
        return;
    }

    let fittedToExtent = false;

    if (item.extent && item.extent.length === 4 && map.value) {
        try {
            const sourceProjection = item.srid === 3857 ? 'EPSG:3857' : `EPSG:${item.srid || 4326}`;
            const mapExtent = sourceProjection === 'EPSG:3857'
                ? item.extent
                : transformExtent(item.extent, sourceProjection, 'EPSG:3857');
            map.value.getView().fit(mapExtent, { padding: [100, 100, 100, 100], duration: 900, maxZoom: 11 });
            fittedToExtent = true;
        } catch (error) {
            console.warn('Failed to fit extent, fallback to center:', error);
        }
    }

    if (typeof item.center_x === 'number' && typeof item.center_y === 'number') {
        const coords = toMapCoords([item.center_x, item.center_y], item.srid);
        if (!fittedToExtent) {
            flyTo(coords);
        }
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
        localOverlayGuideSource.clear();
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

.map-hall-panel {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 96;
  width: 320px;
  height: calc(100% - 40px);
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.68);
  box-shadow: 0 12px 32px rgba(19, 36, 53, 0.12);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.map-hall-header {
  min-height: 64px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(226, 232, 240, 0.86);
}

.map-hall-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #1f2937;
  letter-spacing: 0.01em;
}

.map-hall-modules {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.map-hall-section {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(226, 232, 240, 0.84);
  border-radius: 14px;
  overflow: hidden;
  background: rgba(248, 251, 255, 0.56);
}

.map-hall-section-title {
  height: 48px;
  padding: 0 14px;
  border: 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.72);
  background: rgba(255, 255, 255, 0.82);
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #374151;
  font-size: 14px;
  font-weight: 700;
  cursor: default;
}

.map-hall-section-count {
  min-width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: #1d4ed8;
  background: rgba(59, 130, 246, 0.11);
  font-size: 12px;
}

.map-hall-list {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.map-hall-entry {
  width: 100%;
  padding: 13px 14px;
  border: 1px solid rgba(96, 165, 250, 0.2);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 251, 255, 0.98));
  cursor: pointer;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.map-hall-entry:hover {
  transform: translateY(-1px);
  border-color: rgba(64, 158, 255, 0.38);
  box-shadow: 0 10px 20px rgba(31, 78, 121, 0.1);
}

.map-hall-entry-main,
.map-hall-entry-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.map-hall-entry-title {
  min-width: 0;
  color: #25324a;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.4;
}

.map-hall-entry-region {
  flex-shrink: 0;
  padding: 2px 9px;
  border-radius: 999px;
  color: #66748a;
  background: rgba(100, 116, 139, 0.09);
  font-size: 11px;
}

.map-hall-entry-meta {
  margin-top: 8px;
  color: #6b7280;
  font-size: 11px;
}

.map-hall-entry-meta span:last-child {
  color: #2d6a4f;
}

.map-hall-summary {
  padding: 12px 20px;
  border-top: 1px solid rgba(226, 232, 240, 0.86);
  color: #8a94a6;
  font-size: 12px;
  text-align: right;
  background: rgba(255, 255, 255, 0.84);
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

.left-overview-panel {
  position: absolute;
  top: 96px;
  left: 20px;
  z-index: 96;
}

.heihe-locate-btn {
  min-width: 164px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.88);
  color: #21461d;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(33, 70, 29, 0.16);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.heihe-locate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 28px rgba(33, 70, 29, 0.22);
  background: rgba(246, 251, 244, 0.96);
}

.forest-carbon-panel {
  position: absolute;
  top: 96px;
  right: 22px;
  z-index: 96;
  width: 252px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(249, 252, 246, 0.9);
  border: 1px solid rgba(177, 207, 151, 0.52);
  box-shadow: 0 10px 28px rgba(39, 90, 53, 0.16);
}

.forest-carbon-title {
  font-size: 13px;
  font-weight: 700;
  color: #183d25;
  margin-bottom: 8px;
}

.forest-carbon-controls {
  display: grid;
  grid-template-columns: 1fr 82px;
  gap: 8px;
}

.carbon-select,
.year-select {
  width: 100%;
}

.forest-carbon-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #4f6b45;
}

.map-data-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 140;
}

.map-data-loading-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 26px rgba(31, 63, 26, 0.16);
  color: #21461d;
  font-size: 14px;
  font-weight: 600;
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
