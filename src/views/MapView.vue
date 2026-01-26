<template>
  <div class="map-view-container">
    <!-- 1. 左侧侧边栏：磨砂玻璃效果 -->
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
              :disabled="!selectedExtent" 
              :icon="Delete" 
              circle 
              @click="clearSelection" 
            />
         </el-tooltip>
          <el-tooltip content="空间下载" placement="left">
            <el-button 
              :disabled="!selectedExtent" 
              :loading="isDownloading"
              :icon="Download" 
              circle 
              @click="executeSpatialDownload" 
            />
         </el-tooltip>
      </div>

      <!-- 图层管理面板 -->
      <transition name="fade">
        <div v-if="showLayerPanel" class="layer-panel">
          <div class="panel-header">
            <h4>图层管理</h4>
            <el-button link :icon="Close" @click="showLayerPanel = false" />
          </div>
          
          <div class="layer-item" v-for="(config, key) in layerConfig" :key="key">
            <div class="layer-control">
              <span class="layer-name">{{ config.name }}</span>
              <el-switch 
                v-model="config.visible" 
                size="small"
                @change="updateLayerVisibility(key)"
              />
            </div>
            <div class="layer-opacity" v-if="config.visible">
              <span class="opacity-label">透明度</span>
              <el-slider 
                v-model="config.opacity" 
                :min="0" 
                :max="100" 
                size="small"
                @input="updateLayerOpacity(key)"
              />
            </div>
          </div>
        </div>
      </transition>

      <!-- 4. 鼠标拾取提示 -->
      <div ref="mouseTooltipRef" class="mouse-tooltip" v-show="tooltipContent">
        {{ tooltipContent }}
      </div>
      
      <!-- 指南针和比例尺容器 (通过 CSS 定位) -->
      <div class="map-controls-container">
         <!-- OpenLayers controls will be here -->
      </div>
    </div>

    <!-- 上传对话框 (保持不变) -->
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
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持上传 .tif、.tfw、.prj 文件，可同时上传多个文件
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from "vue";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import ImageLayer from "ol/layer/Image";
import VectorLayer from "ol/layer/Vector";
import OSM from "ol/source/OSM";
import XYZ from "ol/source/XYZ";
import ImageStatic from "ol/source/ImageStatic";
import VectorSource from "ol/source/Vector";
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
  Mouse,
  Delete,
  DocumentDelete,
  Download,
  Files,
  Crop,
  Compass,
  Close,
} from "@element-plus/icons-vue";
import DragBox from "ol/interaction/DragBox";
import { geoDataApi } from "@/api/geodata";
import Geolocation from "ol/Geolocation";
import Point from "ol/geom/Point";
import LineString from "ol/geom/LineString";

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
const showLayerPanel = ref(false);
const layerConfig = ref({
  satellite: { visible: true, opacity: 100, name: '卫星影像 (Base)' },
  faults: { visible: false, opacity: 80, name: '矢量断裂带 (SHP)' },
  boreholes: { visible: false, opacity: 90, name: '钻孔分布点 (Point)' },
  raster: { visible: true, opacity: 80, name: '栅格影像 (TIF)' }
});

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

// 图层切换
const isSatellite = ref(true);

// 区域截选工具相关
const isDragBoxActive = ref(false);
const selectedExtent = ref<[number, number, number, number] | null>(null);
const isDownloading = ref(false);
let dragBoxInteraction: DragBox | null = null;
let selectionLayer: VectorLayer<VectorSource> | null = null;
let selectionFeature: Feature | null = null;

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
      zoom: false, // Hide default zoom, we might want custom or just keep it. User didn't say remove zoom.
      attribution: false,
    }).extend([
      new ScaleLine({
        units: "metric",
        bar: true,
        steps: 4,
        text: true,
        minWidth: 140,
        className: "custom-scale-line", // For styling
      }),
    ]),
    view: new View({
      center: fromLonLat([116.3974, 39.9093]),
      zoom: 10,
    }),
  });

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
  } else {
    console.error("无法获取 EPSG:3857 投影，Geolocation 初始化失败");
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

  // 1. Vector Faults (Mock)
  const faultsSource = new VectorSource();
  const center = fromLonLat([116.3974, 39.9093]);
  // 创建几条随机断裂带
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
  lines.forEach(geom => faultsSource.addFeature(new Feature(geom)));

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
  for (let i = 0; i < 50; i++) {
     const x = center[0] + (Math.random() - 0.5) * 30000;
     const y = center[1] + (Math.random() - 0.5) * 30000;
     boreholesSource.addFeature(new Feature(new Point([x, y])));
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

// 更新图层可见性
const updateLayerVisibility = (key: string) => {
  const config = layerConfig.value[key as keyof typeof layerConfig.value];
  const visible = config.visible;

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

// 更新图层透明度
const updateLayerOpacity = (key: string) => {
  const config = layerConfig.value[key as keyof typeof layerConfig.value];
  const opacity = config.opacity / 100;

  switch (key) {
    case 'satellite':
      if (satelliteLayer) satelliteLayer.setOpacity(opacity);
      if (labelLayer) labelLayer.setOpacity(opacity);
      break;
    case 'faults':
      if (faultsLayer) faultsLayer.setOpacity(opacity);
      break;
    case 'boreholes':
      if (boreholesLayer) boreholesLayer.setOpacity(opacity);
      break;
    case 'raster':
      if (imageLayer) imageLayer.setOpacity(opacity);
      break;
  }
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
  const extent = dragBoxInteraction.getGeometry().getExtent();
  selectedExtent.value = extent as [number, number, number, number];

  // 添加详细的调试信息，确认浏览器拿到了地理范围
  console.log("选区坐标已获取:", extent);
  console.log(`框选范围: ${selectedExtent.value}`);
  console.log(`坐标范围格式: [minX, minY, maxX, maxY]`);

  // 在地图上显示选择区域
  showSelectionArea(extent as [number, number, number, number]);
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

  // 重置状态，恢复初始
  if (isDragBoxActive.value && map.value && dragBoxInteraction) {
    isDragBoxActive.value = false;
    map.value.removeInteraction(dragBoxInteraction);
  }

  ElMessage.info("已清除选择");
};

// 执行空间下载
const executeSpatialDownload = async () => {
  if (!map.value || !selectedExtent.value) return;

  isDownloading.value = true;

  try {
    const API_BASE_URL =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:9988";
    const token = localStorage.getItem("token");
    const headers: HeadersInit = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // 发送请求到后端空间下载接口
    const response = await fetch(
      `${API_BASE_URL}/api/geodata/spatial-download`,
      {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          extent: selectedExtent.value,
          srid: 3857, // 前端地图使用 EPSG:3857
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
    console.log("地质数据列表响应:", response);
    // 检查响应结构
    if (response) {
      // 如果响应有 data 属性（完整响应对象）
      if (Array.isArray(response.data)) {
        geoDataList.value = response.data;
        console.log("从 response.data 加载地质数据列表:", response.data);
      }
      // 如果响应本身是数组（响应拦截器已处理）
      else if (Array.isArray(response)) {
        geoDataList.value = response;
        console.log("从直接响应加载地质数据列表:", response);
      }
      // 如果响应是 GeoDataListResponse 格式
      else if (response.data && Array.isArray(response.data)) {
        geoDataList.value = response.data;
        console.log("从 GeoDataListResponse 加载地质数据列表:", response.data);
      }
    }
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

    console.log(`预览数据: ID=${row.id}, 名称=${row.name}, SRID=${sourceSrid}`);
    console.log(`原始 Extent: ${row.extent}`);

    if (sourceSrid === 3857) {
      // 已经是 3857，直接使用原始坐标
      extent3857 = [
        row.extent[0],
        row.extent[1],
        row.extent[2],
        row.extent[3],
      ] as [number, number, number, number];
      console.log(`直接使用 EPSG:3857 坐标: ${extent3857}`);
    } else {
      // 从任意 EPSG 代码转换为 3857
      try {
        const sourceSridStr = `EPSG:${sourceSrid}`;
        extent3857 = transformExtent(
          row.extent,
          sourceSridStr,
          "EPSG:3857",
        ) as [number, number, number, number];
        console.log(`从 ${sourceSridStr} 转换到 EPSG:3857: ${extent3857}`);
      } catch (transformError) {
        console.error(`投影转换失败: ${transformError}`);
        // 如果转换失败，尝试使用原始坐标（可能已经是 3857 或其他可识别格式）
        extent3857 = [
          row.extent[0],
          row.extent[1],
          row.extent[2],
          row.extent[3],
        ] as [number, number, number, number];
        console.log(`使用原始坐标作为备选: ${extent3857}`);
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
  const allowedTypes = [".tif", ".tfw", ".prj"];
  const fileExt = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

  if (!allowedTypes.includes(fileExt)) {
    ElMessage.warning(`不支持的文件类型: ${fileExt}，仅支持 .tif, .tfw, .prj`);
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

  // 定义定位函数，支持配置
  // 注意：定位功能常见问题排查：
  // 1. 浏览器必须允许网站获取位置权限（通常在地址栏左侧锁图标处设置）
  // 2. 本地开发环境建议使用 http://localhost 或配置 https，非安全上下文可能被浏览器禁用定位
  // 3. macOS 系统需要在“系统偏好设置 -> 安全性与隐私 -> 定位服务”中允许浏览器访问位置
  // 4. 如果使用 VPN 或代理，可能会影响基于 IP 的定位
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

  uploading.value = true;

  try {
    // 创建 FormData，强制使用键名 'files'，并使用 file.raw
    const formData = new FormData();
    // 直接从 fileList.value 中提取文件，确保使用 .raw 原始对象
    for (const file of fileList.value) {
      if (file.raw && file.status !== "fail") {
        formData.append("files", file.raw as File);
        console.log("添加文件到 FormData:", file.name);
      }
    }

    // 直接使用 api.post 发送 FormData
    const API_BASE_URL =
      import.meta.env.VITE_API_BASE_URL || "http://localhost:9988";
    const token = localStorage.getItem("token");
    const headers: HeadersInit = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    // 不要显式设置 Content-Type，浏览器会自动添加正确的 boundary

    const response = await fetch(`${API_BASE_URL}/api/geodata/upload`, {
      method: "POST",
      headers: headers,
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "上传失败");
    }

    if (data.warning) {
      ElMessage.warning(data.message || "上传成功，但解析失败");
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
    console.error("上传失败:", error);
    const errorMsg = error.message || "上传失败，请稍后重试";
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

/* Layer Panel Styles */
.layer-panel {
  position: absolute;
  top: 80px; /* Below toolbar */
  right: 20px;
  width: 280px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.layer-item {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}

.layer-item:last-child {
  border-bottom: none;
}

.layer-control {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.layer-name {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.layer-opacity {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 8px;
}

.opacity-label {
  font-size: 12px;
  color: #909399;
  width: 40px;
}

/* Vertical Slider (Removed, kept for reference if needed but logic removed) */
/* .vertical-slider-container { ... } */

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
