<template>
  <div class="map-view-container">
    <!-- 1. 左侧侧边栏：磨砂玻璃效果 (保持不变) -->
    <div class="data-sidebar" :style="{ width: `${sidebarWidth}px` }">
      <div class="sidebar-header">
        <h3>地质数据管理</h3>
        <el-button
          type="primary"
          size="small"
          @click="showUploadDialog = true"
          color="#1a73e8"
          style="margin-top: 8px"
        >
          上传地质数据
        </el-button>
      </div>
      <div class="sidebar-content">
        <!-- 表格样式优化 -->
        <el-table 
          :data="geoDataList" 
          style="width: 100%" 
          :header-cell-style="{ background: 'transparent', color: '#2c3e50', fontWeight: 'bold' }"
          :cell-style="{ background: 'transparent' }"
          class="glass-table"
          row-class-name="data-row"
        >
          <el-table-column prop="name" label="文件名" min-width="150" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="90">
             <template #default="{ row }">
                <el-tag 
                  :color="row.type && row.type.toLowerCase().includes('tif') ? '#ecf5ff' : '#f9f0ff'"
                  :style="{ color: row.type && row.type.toLowerCase().includes('tif') ? '#1a73e8' : '#8e44ad', borderColor: 'transparent' }"
                  effect="light"
                >
                  {{ row.type }}
                </el-tag>
             </template>
          </el-table-column>
          <el-table-column prop="uploadTime" label="上传时间" width="160" show-overflow-tooltip />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                @click="handlePreview(row)"
              >
                预览
              </el-button>
              <el-button
                link
                type="success"
                size="small"
                @click="handleDownload(row)"
              >
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 拖拽条 -->
    <div class="resize-divider" @mousedown="handleMouseDown"></div>

    <!-- 2. 右侧地图容器 -->
    <div class="map-container">
      <div ref="mapEl" class="map-el"></div>

      <!-- 悬浮工具箱 (Floating Toolbar) -->
      <div class="floating-toolbar">
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
              :disabled="selectedGeoItems.length === 0" 
              :icon="Delete" 
              circle 
              @click="clearSelection" 
            />
         </el-tooltip>
          <el-tooltip content="空间下载" placement="left">
            <el-button 
              :disabled="selectedGeoItems.length === 0" 
              :loading="isDownloading"
              :icon="Download" 
              circle 
              @click="executeSpatialDownload" 
            />
         </el-tooltip>
      </div>

      <!-- 新版图层管理器组件 -->
      <LayerManager 
        :visible="showLayerPanel"
        :layer-config="layerConfig"
        @close="showLayerPanel = false"
        @update:visibility="handleLayerVisibilityChange"
        @update:opacity="handleLayerOpacityChange"
      />

      <!-- 属性统计看板 -->
      <transition name="fade">
        <AttributeDashboard 
            v-if="showAttributeDashboard"
            :data="selectedStats"
        />
      </transition>

      <!-- 4. 鼠标拾取提示 -->
      <div ref="mouseTooltipRef" class="mouse-tooltip" v-show="tooltipContent">
        {{ tooltipContent }}
      </div>
      
    </div>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传地质数据"
      width="500px"
      @close="handleUploadDialogClose"
    >
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        multiple
        drag
        :limit="10"
        :name="'files'"
        v-model:file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持上传 .zip (推荐)、.tif、.shp、.mdb、.dbf、.csv 等地质数据
          </div>
        </template>
      </el-upload>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" @click="handleUpload" :loading="uploading">
            上传
          </el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showGeoSelectDialog"
      title="已选点位"
      width="520px"
    >
      <el-table :data="selectedGeoItems" height="300">
        <el-table-column prop="name" label="名称" min-width="200" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="uploadTime" label="创建时间" width="160" />
      </el-table>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showGeoSelectDialog = false">关闭</el-button>
          <el-button type="primary" @click="executeSpatialDownload" :loading="isDownloading">
            一键下载
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog
        v-model="detailVisible"
        :title="currentFeature?.properties?.name || '要素详情'"
        width="400px"
        draggable
    >
        <div v-if="currentFeature">
            <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="类型">{{ currentFeature.properties.type }}</el-descriptions-item>
                <el-descriptions-item label="岩性">{{ currentFeature.properties.lithology }}</el-descriptions-item>
                <el-descriptions-item label="描述">{{ currentFeature.properties.description }}</el-descriptions-item>
                <el-descriptions-item label="坐标">
                    {{ currentFeature.geometry.flatCoordinates ? 
                        `${currentFeature.geometry.flatCoordinates[0].toFixed(2)}, ${currentFeature.geometry.flatCoordinates[1].toFixed(2)}` 
                        : 'N/A' 
                    }}
                </el-descriptions-item>
            </el-descriptions>

            <div class="reports-section" v-if="currentFeature.properties.reports && currentFeature.properties.reports.length">
                <h4>关联报告</h4>
                <div v-for="(report, index) in currentFeature.properties.reports" :key="index" class="report-item">
                    <span>{{ report.title }}</span>
                    <el-button link type="primary" size="small" @click="previewReport(report)">预览</el-button>
                </div>
            </div>
             <div v-else class="no-reports">
                暂无关联报告
            </div>
        </div>
    </el-dialog>

    <!-- PDF 预览弹窗 -->
    <el-dialog
        v-model="pdfPreviewVisible"
        title="报告预览"
        width="80%"
        top="5vh"
        custom-class="pdf-preview-dialog"
    >
        <iframe v-if="currentPdfUrl" :src="currentPdfUrl" width="100%" height="600px" frameborder="0"></iframe>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import ImageLayer from "ol/layer/Image";
import VectorLayer from "ol/layer/Vector";
import OSM from "ol/source/OSM";
import XYZ from "ol/source/XYZ";
import ImageStatic from "ol/source/ImageStatic";
import VectorSource from "ol/source/Vector";
import Cluster from "ol/source/Cluster";
import Overlay from "ol/Overlay";
import { ScaleLine, defaults as defaultControls } from "ol/control";
import {
  fromLonLat,
  toLonLat,
  transformExtent,
  get as getProjection,
} from "ol/proj";
import { Polygon } from "ol/geom";
import { Style, Stroke, Circle as CircleStyle, Fill, Text } from "ol/style";
import Feature from "ol/Feature";
import { ElMessage, ElUpload, type UploadFile } from "element-plus";
import {
  UploadFilled,
  Location,
  Delete,
  Download,
  Files,
  Crop,
} from "@element-plus/icons-vue";
import DragBox from "ol/interaction/DragBox";
import { geoDataApi } from "@/api/geodata";
import Geolocation from "ol/Geolocation";
import Point from "ol/geom/Point";
import LineString from "ol/geom/LineString";
import LayerManager from "@/components/LayerManager.vue";
import AttributeDashboard from "@/components/AttributeDashboard.vue";

// 地图相关
const mapEl = ref<HTMLDivElement | null>(null);
const map = ref<Map | null>(null);
let previewLayer: VectorLayer<VectorSource> | null = null;
let imageLayer: ImageLayer<ImageStatic> | null = null;
let satelliteLayer: TileLayer<XYZ> | null = null;
let labelLayer: TileLayer<XYZ> | null = null; // 路网/文字标注图层
let geolocation: Geolocation | null = null;
let locationLayer: VectorLayer<VectorSource> | null = null; // 定位点图层
let faultsLayer: VectorLayer<VectorSource> | null = null; // 矢量断裂带图层
let boreholesLayer: VectorLayer<VectorSource> | null = null; // 钻孔分布点图层

// 图层管理状态
const showLayerPanel = ref(true); // 默认开启
const layerConfig = ref({
  satellite: { visible: true, opacity: 100, name: '卫星影像 (Base)' },
  faults: { visible: true, opacity: 80, name: '矢量断裂带 (SHP)' },
  boreholes: { visible: true, opacity: 90, name: '钻孔分布点 (Point)' },
  raster: { visible: true, opacity: 80, name: '栅格影像 (TIF)' }
});

// 属性看板相关
const showAttributeDashboard = ref(true);
const selectedStats = ref<Array<{name: string, value: number}>>([]);

// 详情弹窗相关
const detailVisible = ref(false);
const currentFeature = ref<any>(null);
const pdfPreviewVisible = ref(false);
const currentPdfUrl = ref('');

// 侧边栏宽度（响应式）
const sidebarWidth = ref(400);
const MIN_WIDTH = 200;
const MAX_WIDTH = 800;

// 拖拽相关状态
let isDragging = false;
let startX = 0;
let startWidth = 0;
let animationFrameId: number | null = null;

// 地质数据列表
interface GeoDataItem {
  id: number;
  name: string;
  type: string;
  uploadTime: string;
  extent?: [number, number, number, number]; // [minX, minY, maxX, maxY]
  srid?: number; // 坐标系统 EPSG 代码（如 3857 或 4326）
  center_x?: number;
  center_y?: number;
}

const geoDataList = ref<GeoDataItem[]>([]);

// 上传相关
const showUploadDialog = ref(false);
const fileList = ref<UploadFile[]>([]);
const uploading = ref(false);
const uploadRef = ref<InstanceType<typeof ElUpload>>();

// 定位相关
const locating = ref(false);
let locationOverlay: Overlay | null = null; // 定位点 Overlay

// 鼠标提示
const mouseTooltipRef = ref<HTMLDivElement | null>(null);
const tooltipContent = ref("");
let tooltipOverlay: Overlay | null = null;

// 区域截选工具相关
const isDragBoxActive = ref(false);
const selectedExtent = ref<[number, number, number, number] | null>(null);
const isDownloading = ref(false);
let dragBoxInteraction: DragBox | null = null;
let selectionLayer: VectorLayer<VectorSource> | null = null;
let selectionFeature: Feature | null = null;
let geoPointSource: VectorSource | null = null;
let geoClusterSource: Cluster | null = null;
let geoClusterLayer: VectorLayer<VectorSource> | null = null;
const selectedGeoItems = ref<GeoDataItem[]>([]);
const showGeoSelectDialog = ref(false);
const clusterStyleCache = new globalThis.Map<number, Style>();

const createGeoClusterLayer = () => {
  if (!map.value) return;
  geoPointSource = new VectorSource();
  geoClusterSource = new Cluster({
    distance: 40,
    source: geoPointSource,
  });

  geoClusterLayer = new VectorLayer({
    source: geoClusterSource,
    zIndex: 1002,
    style: (feature) => {
      const features = feature.get("features") as Feature[];
      const size = features.length;
      if (size === 1) {
        return new Style({
          image: new CircleStyle({
            radius: 6,
            fill: new Fill({ color: "#00B8D9" }),
            stroke: new Stroke({ color: "#fff", width: 2 }),
          }),
        });
      }

      const cached = clusterStyleCache.get(size);
      if (cached) return cached;

      const style = new Style({
        image: new CircleStyle({
          radius: Math.min(20, 6 + size),
          fill: new Fill({ color: "#1890ff" }),
          stroke: new Stroke({ color: "#fff", width: 2 }),
        }),
        text: new Text({
          text: size.toString(),
          fill: new Fill({ color: "#fff" }),
        }),
      });
      clusterStyleCache.set(size, style);
      return style;
    },
  });

  map.value.addLayer(geoClusterLayer);
};

const updateGeoPointFeatures = () => {
  if (!geoPointSource) return;
  geoPointSource.clear();
  for (const item of geoDataList.value) {
    let centerX = item.center_x;
    let centerY = item.center_y;
    if ((centerX === undefined || centerY === undefined) && item.extent) {
      centerX = (item.extent[0] + item.extent[2]) / 2;
      centerY = (item.extent[1] + item.extent[3]) / 2;
    }
    if (centerX === undefined || centerY === undefined) {
      continue;
    }
    const coordinate =
      item.srid === 3857
        ? [centerX, centerY]
        : fromLonLat([centerX, centerY]);
    const feature = new Feature({
      geometry: new Point(coordinate),
      id: item.id,
      name: item.name,
      type: item.type,
      uploadTime: item.uploadTime,
    });
    geoPointSource.addFeature(feature);
  }
};

// 初始化地图
onMounted(async () => {
  if (!mapEl.value) return;

  // 创建卫星底图图层（使用高德卫星影像）
  satelliteLayer = new TileLayer({
    source: new XYZ({
      url: "https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
      crossOrigin: "anonymous",
      tilePixelRatio: 2,
    }),
    zIndex: 0, // 底图在最下层
  });

  // 创建高德路网/文字标注图层（叠加在卫星图上）
  labelLayer = new TileLayer({
    source: new XYZ({
      url: "https://wprd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&style=8&x={x}&y={y}&z={z}",
      crossOrigin: "anonymous",
      tilePixelRatio: 2,
    }),
    zIndex: 2, // 标注图层在卫星图上方
  });

  // 创建 OSM 图层作为备用底图
  const osmLayer = new TileLayer({
    source: new OSM(),
    zIndex: 1,
    visible: false, // 默认隐藏，使用卫星图
  });

  // 创建地图
  map.value = new Map({
    target: mapEl.value,
    layers: [satelliteLayer, labelLayer, osmLayer],
    controls: defaultControls({
      rotate: true, // Compass
      zoom: false, // Hide default zoom
      attribution: false,
    }).extend([
      new ScaleLine({
        units: "metric",
        bar: true,
        steps: 4,
        text: true,
        minWidth: 140,
        className: "custom-scale-line",
      }),
    ]),
    view: new View({
      center: fromLonLat([116.3974, 39.9093]),
      zoom: 10,
    }),
  });

  createGeoClusterLayer();

  // 初始化鼠标提示 Overlay
  if (mouseTooltipRef.value) {
    tooltipOverlay = new Overlay({
      element: mouseTooltipRef.value,
      offset: [15, 0],
      positioning: "center-left",
      stopEvent: false, // Allow clicks through
    });
    map.value.addOverlay(tooltipOverlay);
  }

  // 监听鼠标移动
  map.value.on("pointermove", (evt) => {
    if (evt.dragging) {
      tooltipOverlay?.setPosition(undefined);
      return;
    }
    const coordinate = evt.coordinate;
    const lonLat = toLonLat(coordinate);
    tooltipContent.value = `Lon: ${lonLat[0].toFixed(6)}, Lat: ${lonLat[1].toFixed(6)}`;
    tooltipOverlay?.setPosition(coordinate);
  });
  
  // 监听点击事件（详情联动）
  map.value.on('singleclick', handleMapClick);

  // 监听鼠标离开地图区域
  mapEl.value.addEventListener("mouseleave", () => {
    tooltipOverlay?.setPosition(undefined);
  });

  // 初始化定位 Overlay (脉冲动画)
  const locationEl = document.createElement("div");
  locationEl.className = "location-pulse";
  locationOverlay = new Overlay({
    element: locationEl,
    positioning: "center-center",
    stopEvent: false,
  });
  map.value.addOverlay(locationOverlay);

  // 初始化 Geolocation
  const projection = getProjection("EPSG:3857");
  if (projection) {
    geolocation = new Geolocation({
      tracking: false, // 不自动跟踪
      projection: projection,
    });

    // 监听位置变化事件
    geolocation.on("change:position", () => {
      if (geolocation) {
        const coordinates = geolocation.getPosition();
        if (coordinates && map) {
          updateLocationMarker(coordinates);
        }
      }
    });
  }

  // 监听定位错误
  if (geolocation) {
    geolocation.on("error", (error) => {
      console.error("定位失败:", error);
      ElMessage.error("定位失败，请检查浏览器位置权限设置");
      locating.value = false;
    });
  }

  // 初始化区域截选工具
  initAreaSelectionTools();

  // 初始化多源图层（Mock）
  initMockLayers();

  // 加载地质数据列表
  await loadGeoDataList();
});

// 初始化多源图层（Mock 数据）
const initMockLayers = () => {
  if (!map.value) return;

  const center = fromLonLat([116.3974, 39.9093]);

  // 1. Vector Faults (Mock)
  const faultsSource = new VectorSource();
  const faultLithologies = ['花岗岩', '玄武岩', '片麻岩'];
  
  const lines = [
    new LineString([
      [center[0] - 5000, center[1] - 5000],
      [center[0] + 5000, center[1] + 5000]
    ]),
    new LineString([
      [center[0] - 5000, center[1] + 5000],
      [center[0] + 5000, center[1] - 5000]
    ]),
     new LineString([
       [center[0] - 8000, center[1] + 2000],
       [center[0] + 2000, center[1] - 8000]
    ])
  ];
  
  lines.forEach((geom, index) => {
      const feature = new Feature(geom);
      // 添加 Mock 属性
      feature.setProperties({
          name: `断裂带 F${index + 1}`,
          type: '断层',
          lithology: faultLithologies[index % 3],
          description: `这是一条${faultLithologies[index % 3]}断裂带，走向NE。`,
          reports: [
              { title: `F${index + 1}断层勘察报告.pdf`, url: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf' }
          ]
      });
      faultsSource.addFeature(feature);
  });

  faultsLayer = new VectorLayer({
    source: faultsSource,
    visible: layerConfig.value.faults.visible,
    opacity: layerConfig.value.faults.opacity / 100,
    style: new Style({
      stroke: new Stroke({ color: '#f5222d', width: 3, lineDash: [10, 10] }),
      text: new Text({ text: '断裂带', font: '12px sans-serif', fill: new Fill({color: 'red'}), offsetY: -10 })
    }),
    zIndex: 10
  });
  map.value.addLayer(faultsLayer);

  // 2. Boreholes (Mock)
  const boreholesSource = new VectorSource();
  const boreholeLithologies = ['砂岩', '泥岩', '石灰岩', '花岗岩'];
  
  for (let i = 0; i < 50; i++) {
     const x = center[0] + (Math.random() - 0.5) * 30000;
     const y = center[1] + (Math.random() - 0.5) * 30000;
     const feature = new Feature(new Point([x, y]));
     
     const lithology = boreholeLithologies[Math.floor(Math.random() * boreholeLithologies.length)];
     
     feature.setProperties({
         name: `钻孔 ZK${i + 1}`,
         type: '钻孔',
         lithology: lithology,
         description: `深度 120m，主要岩性为${lithology}。`,
         reports: Math.random() > 0.5 ? [
             { title: `ZK${i + 1}钻探记录表.pdf`, url: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf' }
         ] : []
     });
     
     boreholesSource.addFeature(feature);
  }

  boreholesLayer = new VectorLayer({
    source: boreholesSource,
    visible: layerConfig.value.boreholes.visible,
    opacity: layerConfig.value.boreholes.opacity / 100,
    style: new Style({
      image: new CircleStyle({
        radius: 6,
        fill: new Fill({ color: '#52c41a' }),
        stroke: new Stroke({ color: '#fff', width: 2 })
      })
    }),
    zIndex: 11
  });
  map.value.addLayer(boreholesLayer);
};

// 处理图层可见性变化
const handleLayerVisibilityChange = ({ key, visible }: { key: string, visible: boolean }) => {
    if (layerConfig.value[key as keyof typeof layerConfig.value]) {
        layerConfig.value[key as keyof typeof layerConfig.value].visible = visible;
    }
    
    // 更新 OpenLayers 图层
    switch (key) {
        case 'satellite':
            if (satelliteLayer) satelliteLayer.setVisible(visible);
            if (labelLayer) labelLayer.setVisible(visible);
            break;
        case 'faults':
            if (faultsLayer) faultsLayer.setVisible(visible);
            break;
        case 'boreholes':
            if (boreholesLayer) boreholesLayer.setVisible(visible);
            break;
        case 'raster':
            if (imageLayer) imageLayer.setVisible(visible);
            break;
    }
};

// 处理图层透明度变化
const handleLayerOpacityChange = ({ key, opacity }: { key: string, opacity: number }) => {
    if (layerConfig.value[key as keyof typeof layerConfig.value]) {
        layerConfig.value[key as keyof typeof layerConfig.value].opacity = opacity;
    }
    
    const opacityValue = opacity / 100;
    switch (key) {
        case 'satellite':
            if (satelliteLayer) satelliteLayer.setOpacity(opacityValue);
            if (labelLayer) labelLayer.setOpacity(opacityValue);
            break;
        case 'faults':
            if (faultsLayer) faultsLayer.setOpacity(opacityValue);
            break;
        case 'boreholes':
            if (boreholesLayer) boreholesLayer.setOpacity(opacityValue);
            break;
        case 'raster':
            if (imageLayer) imageLayer.setOpacity(opacityValue);
            break;
    }
};

// 处理地图点击（详情联动）
const handleMapClick = (evt: any) => {
    // 如果正在使用框选工具，不触发详情
    if (isDragBoxActive.value) return;

    const pixel = map.value!.getEventPixel(evt.originalEvent);
    const hit = map.value!.forEachFeatureAtPixel(pixel, (feature) => {
        return feature;
    });

    if (hit) {
        const props = hit.getProperties();
        // 过滤掉非业务图层的 feature (如选择框、预览框等)
        // 可以通过判断是否有 'name' 或 'type' 等业务属性
        if (props.name || props.type) {
            currentFeature.value = {
                properties: props,
                geometry: hit.getGeometry()
            };
            detailVisible.value = true;
        }
    } else {
        // 点击空白处，不做处理，或者关闭弹窗？
        // detailVisible.value = false;
    }
};

// 预览报告
const previewReport = (report: any) => {
    currentPdfUrl.value = report.url;
    pdfPreviewVisible.value = true;
};

// 初始化区域截选工具
const initAreaSelectionTools = () => {
  if (!map.value) return;

  // 创建选择区域显示图层
  const selectionSource = new VectorSource();
  selectionLayer = new VectorLayer({
    source: selectionSource,
    zIndex: 1003,
    style: new Style({
      fill: new Fill({
        color: "rgba(64, 158, 255, 0.3)",
      }),
      stroke: new Stroke({
        color: "#409EFF",
        width: 2,
      }),
    }),
  });
  map.value.addLayer(selectionLayer);

  // 创建拖拽框交互
  dragBoxInteraction = new DragBox({
    className: 'ol-dragbox',
  });

  // 监听拖拽结束事件
  dragBoxInteraction.on("boxend", handleDragBoxEnd);

  // 初始不激活
  map.value.removeInteraction(dragBoxInteraction);
};

// 处理拖拽框结束事件
const handleDragBoxEnd = () => {
  if (!map.value || !dragBoxInteraction) return;

  // 获取拖拽框的 extent
  const geometry = dragBoxInteraction.getGeometry();
  const extent = geometry.getExtent();
  selectedExtent.value = extent as [number, number, number, number];

  // 在地图上显示选择区域
  showSelectionArea(extent as [number, number, number, number]);

  updateSelectedGeoItems(extent as [number, number, number, number]);
};

const updateSelectedGeoItems = (extent: [number, number, number, number]) => {
  if (!geoPointSource) return;
  const features = geoPointSource.getFeaturesInExtent(extent);
  const items: GeoDataItem[] = [];
  const seen = new Set<number>();
  for (const feature of features) {
    const id = feature.get("id");
    if (seen.has(id)) continue;
    seen.add(id);
    items.push({
      id,
      name: feature.get("name"),
      type: feature.get("type"),
      uploadTime: feature.get("uploadTime"),
    });
  }

  selectedGeoItems.value = items;
  const stats: Record<string, number> = {};
  for (const item of items) {
    stats[item.type] = (stats[item.type] || 0) + 1;
  }
  selectedStats.value = Object.entries(stats).map(([name, value]) => ({ name, value }));
  if (items.length > 0) {
    showGeoSelectDialog.value = true;
  } else {
    showGeoSelectDialog.value = false;
    ElMessage.info("选区内无点位");
  }
};

// 在地图上显示选择区域
const showSelectionArea = (extent: [number, number, number, number]) => {
  if (!map.value || !selectionLayer) return;

  // 清除旧的选择区域
  clearSelectionArea();

  // 创建新的选择区域 Feature
  const [minX, minY, maxX, maxY] = extent;
  const polygon = new Polygon([
    [
      [minX, minY],
      [maxX, minY],
      [maxX, maxY],
      [minX, maxY],
      [minX, minY],
    ],
  ]);

  selectionFeature = new Feature({
    geometry: polygon,
  });

  // 添加到选择图层
  selectionLayer.getSource()?.addFeature(selectionFeature);
};

// 清除选择区域
const clearSelectionArea = () => {
  if (!selectionLayer || !selectionFeature) return;

  selectionLayer.getSource()?.removeFeature(selectionFeature);
  selectionFeature = null;
};

// 切换拖拽框工具
const toggleDragBox = () => {
  if (!map.value || !dragBoxInteraction) return;

  isDragBoxActive.value = !isDragBoxActive.value;

  if (isDragBoxActive.value) {
    map.value.addInteraction(dragBoxInteraction);
    ElMessage.info("框选工具已开启，请在地图上拖拽选择区域");
  } else {
    map.value.removeInteraction(dragBoxInteraction);
    ElMessage.info("框选工具已关闭");
  }
};

// 清除选择
const clearSelection = () => {
  selectedExtent.value = null;
  clearSelectionArea();
  selectedStats.value = [];
  selectedGeoItems.value = [];
  showGeoSelectDialog.value = false;

  // 重置状态，恢复初始
  if (isDragBoxActive.value && map.value && dragBoxInteraction) {
    isDragBoxActive.value = false;
    map.value.removeInteraction(dragBoxInteraction);
  }

  ElMessage.info("已清除选择");
};

const executeSpatialDownload = async () => {
  if (selectedGeoItems.value.length === 0) {
    ElMessage.warning("请先框选点位");
    return;
  }

  isDownloading.value = true;

  try {
    const API_BASE_URL =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:9988";
    const token = localStorage.getItem("token");
    const headers: HeadersInit = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE_URL}/api/geodata/download-batch`,
      {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ids: selectedGeoItems.value.map((item) => item.id),
        }),
      },
    );

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: "下载失败" }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    // 获取 blob 数据
    const blob = await response.blob();

    // 创建下载链接并触发浏览器下载
    const contentDisposition =
      response.headers.get("Content-Disposition") || "";
    let filename = "geodata_export.zip";

    // 从响应头中提取文件名
    const filenameMatch = contentDisposition.match(
      /filename\*?=\s*(?:"([^"]+)"|([^;]+))/,
    );
    if (filenameMatch) {
      filename = filenameMatch[1] || filenameMatch[2] || filename;
    }

    // 解码文件名，处理可能的 URL 编码
    filename = decodeURIComponent(filename);

    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", filename);
    link.style.display = "none";

    // 添加到 DOM 并触发点击
    document.body.appendChild(link);
    link.click();

    // 清理 DOM 和 URL 对象
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    ElMessage.success("空间下载成功");
  } catch (error: any) {
    console.error("空间下载失败:", error);
    ElMessage.error(error.message || "空间下载失败，请稍后重试");
  } finally {
    isDownloading.value = false;
  }
};

// 加载地质数据列表
const loadGeoDataList = async () => {
  try {
    const response = await geoDataApi.getList();
    // 检查响应结构
    if (response) {
      // 如果响应有 data 属性（完整响应对象）
      if (Array.isArray(response.data)) {
        geoDataList.value = response.data;
      }
      // 如果响应本身是数组（响应拦截器已处理）
      else if (Array.isArray(response)) {
        geoDataList.value = response;
      }
      // 如果响应是 GeoDataListResponse 格式
      else if (response.data && Array.isArray(response.data)) {
        geoDataList.value = response.data;
      }
    }
    updateGeoPointFeatures();
  } catch (error) {
    console.error("加载地质数据列表失败:", error);
    // 使用硬编码数据作为后备
  }
};

// 预览功能：地图自动定位，绘制红色矩形边框，并叠加 TIF 图像
const handlePreview = async (row: GeoDataItem) => {
  if (!map.value) {
    ElMessage.warning("地图未初始化");
    return;
  }

  if (!row.extent || row.extent.length !== 4) {
    ElMessage.warning("该数据没有有效的空间范围信息");
    return;
  }

  try {
    // 根据原始坐标系统决定是否需要转换
    // 支持所有 EPSG 代码，不仅限于 4326 和 3857
    const sourceSrid = row.srid || 4326; // 默认 4326
    let extent3857: [number, number, number, number];

    if (sourceSrid === 3857) {
      // 已经是 3857，直接使用原始坐标
      extent3857 = [
        row.extent[0],
        row.extent[1],
        row.extent[2],
        row.extent[3],
      ] as [number, number, number, number];
    } else {
      // 从任意 EPSG 代码转换为 3857
      try {
        const sourceSridStr = `EPSG:${sourceSrid}`;
        extent3857 = transformExtent(
          row.extent,
          sourceSridStr,
          "EPSG:3857",
        ) as [number, number, number, number];
      } catch (transformError) {
        console.error(`投影转换失败: ${transformError}`);
        // 如果转换失败，尝试使用原始坐标（可能已经是 3857 或其他可识别格式）
        extent3857 = [
          row.extent[0],
          row.extent[1],
          row.extent[2],
          row.extent[3],
        ] as [number, number, number, number];
      }
    }

    // 移除旧的预览图层（如果存在）
    if (previewLayer) {
      map.value.removeLayer(previewLayer);
      previewLayer = null;
    }
    if (imageLayer) {
      map.value.removeLayer(imageLayer);
      imageLayer = null;
    }

    // 创建预览矩形框（红色边框）
    const [minX, minY, maxX, maxY] = extent3857;

    const polygon = new Polygon([
      [
        [minX, minY], // 左下角
        [maxX, minY], // 右下角
        [maxX, maxY], // 右上角
        [minX, maxY], // 左上角
        [minX, minY], // 闭合
      ],
    ]);

    // 创建矢量图层
    const vectorSource = new VectorSource({
      features: [
        new Feature({
          geometry: polygon,
        }),
      ],
    });

    // 创建发光效果边框图层
    previewLayer = new VectorLayer({
      source: vectorSource,
      style: [
        // 外发光
        new Style({
          stroke: new Stroke({
            color: "rgba(26, 115, 232, 0.4)",
            width: 8,
          }),
        }),
        // 核心线
        new Style({
          stroke: new Stroke({
            color: "#1a73e8", // 科技蓝
            width: 2,
          }),
        }),
      ],
      zIndex: 1001, // 确保预览图层在最上层
    });

    // 添加预览图层到地图
    map.value.addLayer(previewLayer);

    // 加载 TIF 图像（使用预览接口，后端转换为 PNG）
    try {
      const API_BASE_URL =
        import.meta.env.VITE_API_BASE_URL || "http://localhost:9988";
      // 使用预览接口，后端会将 TIF 转换为 PNG
      const imageUrl = `${API_BASE_URL}/api/geodata/preview/${row.id}`;

      const projection = getProjection("EPSG:3857");
      if (!projection) {
        throw new Error("无法获取 EPSG:3857 投影");
      }

      const imageSource = new ImageStatic({
        url: imageUrl,
        imageExtent: extent3857,
        projection: projection,
        crossOrigin: "anonymous", // 允许跨域
      });

      imageLayer = new ImageLayer({
        source: imageSource,
        zIndex: 1000, // 在边框下方，但在地图底图上方
        opacity: 0, // 初始透明度为 0，用于淡入动画
      });

      // 监听图像加载错误
      imageSource.on("imageloaderror", () => {
        ElMessage.warning("图像加载失败，仅显示边框");
        if (imageLayer && map.value) {
          map.value.removeLayer(imageLayer);
          imageLayer = null;
        }
      });

      map.value.addLayer(imageLayer);

      // 淡入动画
      const start = Date.now();
      const duration = 800; // 800ms 淡入
      const targetOpacity = layerConfig.value.raster.opacity / 100;

      const animateFadeIn = () => {
        if (!imageLayer) return;
        const elapsed = Date.now() - start;
        const progress = Math.min(elapsed / duration, 1);
        
        imageLayer.setOpacity(progress * targetOpacity);

        if (progress < 1) {
          requestAnimationFrame(animateFadeIn);
        }
      };
      requestAnimationFrame(animateFadeIn);

    } catch (imageError) {
      console.warn("图像加载失败，仅显示边框:", imageError);
      ElMessage.warning("图像加载失败，仅显示边框");
      // 图像加载失败不影响边框显示
    }

    // 使用 map.getView().fit() 实现地图自动定位，平滑飞行效果
    const view = map.value.getView();
    view.fit(extent3857, {
      duration: 1000, // 动画时长 1 秒
      padding: [50, 50, 50, 50], // 添加边距，确保矩形框完整显示
      maxZoom: 18, // 最大缩放级别
    });

    ElMessage.success(`已定位到: ${row.name}`);
  } catch (error) {
    console.error("预览失败:", error);
    ElMessage.error("预览失败，请检查数据格式");
  }
};

// 下载功能：从后端 storage 目录下载文件
const handleDownload = async (row: GeoDataItem) => {
  try {
    ElMessage.info("开始下载...");

    const API_BASE_URL =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:9988";
    const url = `${API_BASE_URL}/api/geodata/download/${row.id}`;

    // 使用 fetch 获取文件，支持添加认证 header
    const token = localStorage.getItem("token");
    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: "下载失败" }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    // 获取 blob 数据
    const blob = await response.blob();

    // 创建下载链接并触发浏览器下载
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", row.name);
    link.style.display = "none";

    // 添加到 DOM 并触发点击
    document.body.appendChild(link);
    link.click();

    // 清理 DOM 和 URL 对象
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    ElMessage.success(`下载成功: ${row.name}`);
  } catch (error: any) {
    console.error("下载失败:", error);
    const errorMsg = error.message || "下载失败，请稍后重试";
    ElMessage.error(errorMsg);
  }
};

// 拖拽开始
const handleMouseDown = (e: MouseEvent) => {
  isDragging = true;
  startX = e.clientX;
  startWidth = sidebarWidth.value;

  // 阻止默认行为和事件冒泡
  e.preventDefault();
  e.stopPropagation();

  // 添加全局事件监听
  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);

  // 添加样式防止文本选中
  document.body.style.userSelect = "none";
  document.body.style.cursor = "col-resize";
};

// 拖拽中
const handleMouseMove = (e: MouseEvent) => {
  if (!isDragging) return;

  // 使用 requestAnimationFrame 优化性能
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  animationFrameId = requestAnimationFrame(() => {
    const deltaX = e.clientX - startX;
    let newWidth = startWidth + deltaX;

    // 限制宽度范围
    newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, newWidth));

    sidebarWidth.value = newWidth;

    // 更新地图尺寸，防止拉伸变形
    if (map.value) {
      map.value.updateSize();
    }
  });
};

// 拖拽结束
const handleMouseUp = () => {
  isDragging = false;

  // 移除全局事件监听
  window.removeEventListener("mousemove", handleMouseMove);
  window.removeEventListener("mouseup", handleMouseUp);

  // 恢复样式
  document.body.style.userSelect = "";
  document.body.style.cursor = "";

  // 清理 animation frame
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }

  // 最后更新一次地图尺寸
  if (map.value) {
    map.value.updateSize();
  }
};

// 上传相关函数
const handleFileChange = (file: UploadFile) => {
  // 检查文件类型
  const allowedTypes = [
    ".tif", ".tfw", ".prj", 
    ".zip", ".rar", 
    ".shp", ".shx", ".dbf", ".geojson", ".json", 
    ".csv", ".txt", 
    ".pdf", ".doc", ".docx",
    ".mdb", ".db", ".gdb", ".sbx", ".sbn", ".xml"
  ];
  const fileExt = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

  if (!allowedTypes.includes(fileExt)) {
    ElMessage.warning(`不支持的文件类型: ${fileExt}，请上传 .zip, .shp, .mdb 等格式`);
    uploadRef.value?.handleRemove(file);
    return false;
  }
};

const handleFileRemove = () => {
  // 文件移除时的处理
};

const handleUploadDialogClose = () => {
  fileList.value = [];
  uploadRef.value?.clearFiles();
};

// 更新定位点标记
const updateLocationMarker = (coordinates: number[]) => {
  if (!locationOverlay || !map.value) return;

  // 更新 Overlay 位置
  locationOverlay.setPosition(coordinates);
};

// 定位功能：获取用户位置并定位
const handleLocation = async () => {
  if (!map.value) {
    ElMessage.warning("地图未初始化");
    return;
  }

  locating.value = true;

  if (!navigator.geolocation) {
    ElMessage.error("您的浏览器不支持地理定位");
    locating.value = false;
    return;
  }

  const getPosition = (options: PositionOptions): Promise<GeolocationPosition> => {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, options);
    });
  };

  try {
    let position: GeolocationPosition;
    try {
      console.log("尝试高精度定位...");
      // 尝试高精度，超时 10s
      position = await getPosition({
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      });
    } catch (error: any) {
      console.warn("高精度定位失败，尝试低精度定位...", error);
      ElMessage.info("高精度定位超时，正在切换低精度定位...");
      // 如果高精度失败（超时或不可用），尝试低精度，超时 10s
      position = await getPosition({
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 0,
      });
    }

    const coords = position.coords;
    console.log("定位成功:", coords);

    // 转换为 EPSG:3857
    const coordinates = fromLonLat([coords.longitude, coords.latitude]);
    const [lon, lat] = [coords.longitude, coords.latitude];

    // 更新定位点标记
    updateLocationMarker(coordinates);

    // 动画定位到用户位置
    const view = map.value.getView();
    view.animate({
      center: coordinates,
      zoom: 15,
      duration: 1000,
    });

    ElMessage.success(`定位成功：${lat.toFixed(6)}, ${lon.toFixed(6)}`);
  } catch (error: any) {
    console.error("定位最终失败:", error);
    let errorMsg = "定位失败，请检查浏览器位置权限设置";
    if (error.code === 1) {
      errorMsg = "访问被拒绝，请允许浏览器获取位置信息";
    } else if (error.code === 2) {
      errorMsg = "无法获取位置信息，请检查网络或GPS信号";
    } else if (error.code === 3) {
      errorMsg = "定位超时，请稍后重试";
    }
    ElMessage.error(errorMsg);
  } finally {
    locating.value = false;
  }
};

const handleUpload = async () => {
  if (!uploadRef.value) return;

  if (fileList.value.length === 0) {
    ElMessage.warning("请先选择文件");
    return;
  }

  uploading.value = true;

  try {
    const formData = new FormData();
    for (const file of fileList.value) {
      if (file.raw && file.status !== "fail") {
        formData.append("files", file.raw as File);
      }
    }

    const API_BASE_URL =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:9988";
    const token = localStorage.getItem("token");
    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/api/geodata/upload`, {
      method: "POST",
      headers: headers,
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
        console.log("上传请求失败，响应数据:", data);
        const errorDetail = data.detail;
        const errorMsg = typeof errorDetail === 'object' ? JSON.stringify(errorDetail) : (errorDetail || "上传失败");
        throw new Error(errorMsg);
    }

    const hasErrors = data.errors && data.errors.length > 0;
    const hasSuccess = (data.processed && data.processed.length > 0) || (data.zip_results && Object.keys(data.zip_results).length > 0);

    if (hasErrors) {
      const errorList = data.errors.join('; ');
      if (hasSuccess) {
        ElMessage.warning(`部分文件上传/处理失败: ${errorList}`);
      } else {
        throw new Error(errorList); // 让 catch 块处理
      }
    } else if (!hasSuccess) {
      ElMessage.warning("未识别到有效的地质数据文件，请检查文件格式");
    } else {
      ElMessage.success(data.message || "上传成功");
    }

    // 关闭对话框
    showUploadDialog.value = false;
    fileList.value = [];
    uploadRef.value.clearFiles();

    // 刷新列表
    await loadGeoDataList();
  } catch (error: any) {
    console.log("完整错误对象:", error);
    const errorMsg =
      error?.response?.data?.detail ||
      error?.message ||
      "未知错误";
    ElMessage.error(errorMsg);
  } finally {
    uploading.value = false;
  }
};

// 清理资源
onUnmounted(() => {
  // 清理拖拽事件
  window.removeEventListener("mousemove", handleMouseMove);
  window.removeEventListener("mouseup", handleMouseUp);

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  // 恢复样式
  document.body.style.userSelect = "";
  document.body.style.cursor = "";

  if (previewLayer && map.value) {
    map.value.removeLayer(previewLayer);
    previewLayer = null;
  }

  if (imageLayer && map.value) {
    map.value.removeLayer(imageLayer);
    imageLayer = null;
  }

  if (geoClusterLayer && map.value) {
    map.value.removeLayer(geoClusterLayer);
    geoClusterLayer = null;
  }

  if (locationLayer && map.value) {
    map.value.removeLayer(locationLayer);
    locationLayer = null;
  }

  if (geolocation) {
    geolocation.setTracking(false);
    geolocation = null;
  }

  if (map.value) {
    map.value.setTarget(undefined);
    map.value = null;
  }
});
</script>

<style scoped>
.map-view-container {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  user-select: none; /* 防止拖拽时选中文本 */
}

.data-sidebar {
  height: 100%;
  background: var(--geo-bg-glass, rgba(255, 255, 255, 0.8));
  backdrop-filter: blur(10px);
  border-right: none;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.05);
  flex-shrink: 0; /* 防止被压缩 */
  z-index: 2;
}

.sidebar-header {
  padding: 16px;
  background: transparent;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  user-select: text; /* 表格内容可以选中 */
}

/* Glass Table Styles */
:deep(.glass-table) {
  background: transparent !important;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(26, 115, 232, 0.1);
  --el-table-border-color: transparent;
}

:deep(.glass-table .el-table__inner-wrapper::before) {
  display: none; /* Remove bottom border */
}

:deep(.glass-table tr) {
  transition: transform 0.2s ease, background-color 0.2s ease;
}

:deep(.glass-table .data-row:hover) {
  transform: translateX(4px);
  background-color: rgba(26, 115, 232, 0.05) !important;
}

.resize-divider {
  width: 4px;
  height: 100%;
  background: transparent;
  cursor: col-resize;
  z-index: 10;
  transition: background 0.2s;
}

.resize-divider:hover {
  background: #409eff;
}

.map-container {
  flex: 1;
  position: relative;
  height: 100%;
  box-shadow: inset 5px 0 15px -5px rgba(0, 0, 0, 0.1);
}

.map-el {
  width: 100%;
  height: 100%;
}

/* Floating Toolbar */
.floating-toolbar {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(5px);
  padding: 8px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 100;
}

.floating-toolbar .el-button {
  margin-left: 0 !important;
}

.reports-section {
    margin-top: 20px;
    border-top: 1px solid #eee;
    padding-top: 10px;
}

.report-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    font-size: 12px;
}

.no-reports {
    margin-top: 20px;
    color: #909399;
    font-size: 12px;
    text-align: center;
}

/* Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<!-- Global Styles for Map Elements -->
<style>
/* Mouse Tooltip */
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
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* Pulse Animation */
.location-pulse {
  width: 20px;
  height: 20px;
  background: #1a73e8;
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
  position: relative;
  animation: pulse 2s infinite;
}

.location-pulse::after {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(26, 115, 232, 0.5);
  animation: pulse-ring 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(26, 115, 232, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(26, 115, 232, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(26, 115, 232, 0); }
}

@keyframes pulse-ring {
  0% { width: 20px; height: 20px; opacity: 1; }
  100% { width: 60px; height: 60px; opacity: 0; }
}

/* Map Controls Customization */
.ol-scale-line {
  background: rgba(255, 255, 255, 0.8) !important;
  border-radius: 4px;
  bottom: 10px;
  left: 10px;
  padding: 2px;
}

.ol-scale-line-inner {
  color: #333 !important;
  border: 1px solid #333 !important;
  border-top: none !important;
  font-weight: bold;
}

.ol-rotate {
  top: auto !important;
  bottom: 40px !important;
  left: 10px !important;
  right: auto !important;
}

/* Custom Scale Line (if used manually) */
.custom-scale-line {
  background: rgba(255, 255, 255, 0.7);
  padding: 2px;
  border-radius: 4px;
}
</style>
