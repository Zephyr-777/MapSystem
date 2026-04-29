export type CatalogRegionId = 'himalaya' | 'heihe' | 'heihe-basin' | 'china' | 'southwest-china' | 'central-asia' | 'badaling' | 'hepingjie';
export type CatalogDataTypeId = 'remote-sensing' | 'geology-point' | 'vector' | 'thematic';
export type CatalogSourceId = 'shared' | 'local' | 'platform';

export interface CatalogRegion {
  id: CatalogRegionId;
  name: string;
  shortName: string;
  center: [number, number];
  bbox: [number, number, number, number];
  defaultZoom: number;
}

export interface CatalogDataType {
  id: CatalogDataTypeId;
  label: string;
}

export interface CatalogSource {
  id: CatalogSourceId;
  label: string;
}

export interface CatalogLayerBinding {
  key: string;
  kind: 'raster-overlay' | 'vector-overlay' | 'vector-cluster' | 'point-cluster' | 'thematic';
  minZoom?: number;
}

export interface CatalogItem {
  id: string;
  title: string;
  description: string;
  regionId: CatalogRegionId;
  dataTypeId: CatalogDataTypeId;
  sourceId: CatalogSourceId;
  layerBindings: CatalogLayerBinding[];
  tags: string[];
  statusLabel?: string;
}

export const catalogRegions: CatalogRegion[] = [
  {
    id: 'himalaya',
    name: '喜马拉雅山脉',
    shortName: '喜马拉雅',
    center: [85.66902225816468, 30.78292418091033],
    bbox: [73.774855591498, 26.637090847577, 97.56318892483135, 34.92875751424367],
    defaultZoom: 7,
  },
  {
    id: 'heihe',
    name: '黑河下游',
    shortName: '黑河',
    center: [101.130455, 41.99698],
    bbox: [101.12262, 41.98922, 101.13829, 42.00474],
    defaultZoom: 12,
  },
  {
    id: 'heihe-basin',
    name: '黑河流域',
    shortName: '黑河流域',
    center: [99.7391772188044, 40.210612346942135],
    bbox: [97.40097811215156, 37.73604623934951, 102.07737632545724, 42.68517845453476],
    defaultZoom: 8,
  },
  {
    id: 'china',
    name: '中国区域',
    shortName: '中国',
    center: [104.25, 36],
    bbox: [73.5, 18, 135, 54],
    defaultZoom: 4,
  },
  {
    id: 'southwest-china',
    name: '中国西南地区',
    shortName: '西南地区',
    center: [103.5, 27.8],
    bbox: [97, 21, 110, 34],
    defaultZoom: 6,
  },
  {
    id: 'central-asia',
    name: '中亚地区',
    shortName: '中亚',
    center: [66.90726364135745, 45.29593876342775],
    bbox: [46.491859436035185, 35.14108276367185, 87.31266784667972, 55.45119476318365],
    defaultZoom: 5,
  },
  {
    id: 'badaling',
    name: '八达岭镇',
    shortName: '八达岭',
    center: [116.015625, 40.2539065],
    bbox: [115.6640625, 40.078125, 116.3671875, 40.4296875],
    defaultZoom: 10,
  },
  {
    id: 'hepingjie',
    name: '和平街街道',
    shortName: '和平街',
    center: [116.54296875, 39.90234375],
    bbox: [116.3671875, 39.7265625, 116.71875, 40.078125],
    defaultZoom: 10,
  },
];

export const catalogDataTypes: CatalogDataType[] = [
  { id: 'remote-sensing', label: '遥感影像' },
  { id: 'geology-point', label: '地质点' },
  { id: 'vector', label: '矢量数据' },
  { id: 'thematic', label: '专题数据' },
];

export const catalogSources: CatalogSource[] = [
  { id: 'shared', label: '共享数据' },
  { id: 'local', label: '本地区数据' },
  { id: 'platform', label: '平台数据' },
];

export const catalogItems: CatalogItem[] = [
  {
    id: 'himalaya-topography-2018',
    title: '喜马拉雅山脉遥感影像',
    description: '喜马拉雅山区 1:25 万地形 GeoTIFF，达到指定缩放级别后作为地图影像图层叠加。',
    regionId: 'himalaya',
    dataTypeId: 'remote-sensing',
    sourceId: 'local',
    layerBindings: [{ key: 'local-raster-himalaya-topography-2018', kind: 'raster-overlay', minZoom: 3 }],
    tags: ['GeoTIFF', '地形影像', '可下载'],
    statusLabel: '本地 TIF',
  },
  {
    id: 'heihe-soil-respiration',
    title: '黑河地区数据',
    description: '黑河下游 Li-8100 土壤呼吸观测数据，默认以站点聚合展示，放大后查看逐次观测点。',
    regionId: 'heihe',
    dataTypeId: 'thematic',
    sourceId: 'shared',
    layerBindings: [
      { key: 'heihe-sites', kind: 'point-cluster' },
      { key: 'heihe-observations', kind: 'point-cluster' },
    ],
    tags: ['Li-8100', '土壤呼吸', 'GeoJSON', '可下载'],
    statusLabel: '专题数据',
  },
  {
    id: 'heihe-grassland-1988',
    title: '黑河流域草场分布数据集',
    description: '黑河流域 1:100 万草场分布 Shapefile（1988），以面图层展示草场类型，并提供聚合索引点和原始数据整包下载。',
    regionId: 'heihe-basin',
    dataTypeId: 'vector',
    sourceId: 'shared',
    layerBindings: [
      { key: 'heihe-grassland-polygons', kind: 'vector-overlay' },
      { key: 'heihe-grassland-points', kind: 'point-cluster', minZoom: 7 },
    ],
    tags: ['Shapefile', '草场分布', '1988', '可下载'],
    statusLabel: '草场专题',
  },
  {
    id: 'china-forest-carbon-2002-2021',
    title: '中国森林植被碳储量数据集',
    description: '中国森林地上和地下植被碳储量 GeoTIFF 时间序列（2002-2021），默认显示 2021 年地上碳储量，可在地图中切换年份和指标。',
    regionId: 'china',
    dataTypeId: 'thematic',
    sourceId: 'shared',
    layerBindings: [{ key: 'forest-carbon-raster', kind: 'raster-overlay', minZoom: 4 }],
    tags: ['GeoTIFF', 'AGBC', 'BGBC', '森林碳储量', '2002-2021'],
    statusLabel: '时间序列栅格',
  },
  {
    id: 'southwest-china-temperature-90ka',
    title: '中国西南地区过去9万年以来定量温度数据集',
    description: 'Excel 表格数据，地图仅提供一个索引点用于快速定位与下载原始文件。',
    regionId: 'southwest-china',
    dataTypeId: 'thematic',
    sourceId: 'local',
    layerBindings: [{ key: 'southwest-temperature-point', kind: 'thematic' }],
    tags: ['Excel', '温度重建', '9万年', '可下载'],
    statusLabel: '表格数据',
  },
  {
    id: 'central-asia-desert-urban-2012-2016',
    title: '中亚沙漠油气田与城镇分布数据集',
    description: '当前目录中已检出国家边界与城镇分布面 Shapefile。地图采用国家边界底层 + 城镇聚合索引点 + 放大后城镇面叠加的方式展示，并提供整包下载。',
    regionId: 'central-asia',
    dataTypeId: 'vector',
    sourceId: 'local',
    layerBindings: [
      { key: 'central-asia-countries', kind: 'vector-overlay' },
      { key: 'central-asia-urban-points', kind: 'point-cluster', minZoom: 8 },
      { key: 'central-asia-urban-polygons', kind: 'vector-overlay', minZoom: 10 },
    ],
    tags: ['Shapefile', '中亚', '城镇分布', '国家边界', '2012-2016', '可下载'],
    statusLabel: '区域矢量专题',
  },
  {
    id: 'badaling-town-imagery',
    title: '八达岭镇分级遥感影像',
    description: '八达岭镇双分幅 GeoTIFF 金字塔影像，地图会根据缩放级别自动切换 L11-L16 分辨率并叠加显示。',
    regionId: 'badaling',
    dataTypeId: 'remote-sensing',
    sourceId: 'local',
    layerBindings: [
      { key: 'badaling-imagery', kind: 'raster-overlay', minZoom: 8 },
      { key: 'badaling-guide-point', kind: 'thematic' },
    ],
    tags: ['GeoTIFF', '影像金字塔', '八达岭镇', 'L11-L16', '可下载'],
    statusLabel: '多级影像',
  },
  {
    id: 'hepingjie-street-imagery',
    title: '和平街街道分级遥感影像',
    description: '和平街街道单分幅 GeoTIFF 金字塔影像，地图会根据缩放级别自动切换 L11-L16 分辨率并叠加显示。',
    regionId: 'hepingjie',
    dataTypeId: 'remote-sensing',
    sourceId: 'local',
    layerBindings: [
      { key: 'hepingjie-imagery', kind: 'raster-overlay', minZoom: 8 },
      { key: 'hepingjie-guide-point', kind: 'thematic' },
    ],
    tags: ['GeoTIFF', '影像金字塔', '和平街街道', 'L11-L16', '可下载'],
    statusLabel: '多级影像',
  },
];

export const findCatalogRegion = (id?: string) => catalogRegions.find((region) => region.id === id);
export const findCatalogItem = (id?: string) => catalogItems.find((item) => item.id === id);

export const getCatalogItemRegion = (item: CatalogItem) => findCatalogRegion(item.regionId);

export const matchesCatalogFilter = (
  item: CatalogItem,
  filters: { regionId?: string; dataTypeId?: string; sourceId?: string; keyword?: string }
) => {
  if (filters.regionId && item.regionId !== filters.regionId) return false;
  if (filters.dataTypeId && item.dataTypeId !== filters.dataTypeId) return false;
  if (filters.sourceId && item.sourceId !== filters.sourceId) return false;

  const keyword = filters.keyword?.trim().toLowerCase();
  if (!keyword) return true;

  const region = getCatalogItemRegion(item);
  const haystack = [
    item.title,
    item.description,
    item.statusLabel,
    region?.name,
    ...item.tags,
  ].join(' ').toLowerCase();
  return haystack.includes(keyword);
};
