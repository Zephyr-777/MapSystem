<template>
  <div class="gallery-view">
    <div class="gallery-header glass-panel">
      <div class="header-left">
        <el-button circle class="back-btn" @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1 class="title">地质资产库</h1>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索地质数据..."
          class="search-input"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <div class="filter-strip glass-panel">
      <div class="filter-block">
        <span class="filter-title">地区</span>
        <el-segmented v-model="filters.regionId" :options="regionOptions" size="small" />
      </div>
      <div class="filter-block">
        <span class="filter-title">类型</span>
        <el-segmented v-model="filters.dataTypeId" :options="typeOptions" size="small" />
      </div>
      <div class="filter-block">
        <span class="filter-title">来源</span>
        <el-segmented v-model="filters.sourceId" :options="sourceOptions" size="small" />
      </div>
      <el-button link class="reset-filter" @click="resetFilters">重置筛选</el-button>
    </div>

    <div class="gallery-content custom-scrollbar">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="3" animated />
      </div>
      
      <div v-else-if="displayCards.length === 0" class="empty-state">
        <el-empty description="暂无公开地质数据" />
      </div>

      <div v-else class="card-grid">
        <div 
          v-for="card in displayCards" 
          :key="card.key" 
          class="asset-card glass-panel"
          @mouseenter="hoveredId = card.key"
          @mouseleave="hoveredId = null"
        >
          <div class="card-preview">
            <div class="preview-icon">
              <el-icon :size="48" color="#409EFF" v-if="card.dataTypeId === 'vector' || card.type === '矢量'"><Location /></el-icon>
              <el-icon :size="48" color="#67C23A" v-else-if="card.dataTypeId === 'remote-sensing' || card.type === '栅格'"><Picture /></el-icon>
              <el-icon :size="48" color="#E6A23C" v-else><Document /></el-icon>
            </div>
            <div class="card-overlay" :class="{ 'visible': hoveredId === card.key }">
              <el-button type="primary" round @click="handleLocate(card)">
                定位到地图 <el-icon class="el-icon--right"><Right /></el-icon>
              </el-button>
            </div>
          </div>
          
          <div class="card-info">
            <h3 class="asset-name" :title="card.name">{{ card.name }}</h3>
            <div class="asset-meta">
              <span class="tag type-tag">{{ card.dataTypeLabel || card.type }}</span>
              <span class="tag source-tag">{{ card.sourceLabel }}</span>
            </div>
            <div class="region-row">
              <el-tag v-if="card.regionLabel" size="small" effect="plain">{{ card.regionLabel }}</el-tag>
              <el-tag v-if="card.statusLabel" size="small" type="success" effect="plain">{{ card.statusLabel }}</el-tag>
              <span v-if="card.uploadTime" class="date">{{ formatDate(card.uploadTime) }}</span>
            </div>
            <p class="asset-desc">{{ card.description || '暂无描述信息' }}</p>
            <div class="card-actions">
              <el-button size="small" type="success" plain @click="handleLocate(card)">定位</el-button>
              <el-button size="small" plain @click="handleView(card)">查看</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowLeft, Search, Location, Picture, Document, Right } from '@element-plus/icons-vue';
import { geoDataApi, type GeoDataItem } from '@/api/geodata';
import { ElMessage } from 'element-plus';
import {
  catalogDataTypes,
  catalogItems,
  catalogRegions,
  catalogSources,
  getCatalogItemRegion,
  matchesCatalogFilter,
  type CatalogDataTypeId,
  type CatalogRegionId,
  type CatalogSourceId,
} from '@/config/geodataCatalog';

const router = useRouter();
const assets = ref<GeoDataItem[]>([]);
const loading = ref(true);
const searchQuery = ref('');
const hoveredId = ref<string | null>(null);

type FilterValue<T extends string> = '' | T;

const filters = reactive<{
  regionId: FilterValue<CatalogRegionId>;
  dataTypeId: FilterValue<CatalogDataTypeId>;
  sourceId: FilterValue<CatalogSourceId>;
}>({
  regionId: '',
  dataTypeId: '',
  sourceId: '',
});

const regionOptions = computed(() => [
  { label: '全部', value: '' },
  ...catalogRegions.map((region) => ({ label: region.shortName, value: region.id })),
]);

const typeOptions = computed(() => [
  { label: '全部', value: '' },
  ...catalogDataTypes.map((type) => ({ label: type.label, value: type.id })),
]);

const sourceOptions = computed(() => [
  { label: '全部', value: '' },
  ...catalogSources.map((source) => ({ label: source.label, value: source.id })),
]);

interface DisplayCard {
  key: string;
  id?: number;
  catalogId?: string;
  name: string;
  description?: string;
  type?: string;
  dataTypeId?: CatalogDataTypeId;
  dataTypeLabel?: string;
  sourceId?: CatalogSourceId;
  sourceLabel?: string;
  regionId?: CatalogRegionId;
  regionLabel?: string;
  statusLabel?: string;
  uploadTime?: string;
  center_x?: number;
  center_y?: number;
  extent?: [number, number, number, number];
  srid?: number;
}



const formatDate = (dateStr: string) => {
  if (!dateStr) return '';
  return dateStr.split('T')[0];
};

const getTypeLabel = (id?: string) => catalogDataTypes.find((type) => type.id === id)?.label || '专题数据';
const getSourceLabel = (id?: string) => catalogSources.find((source) => source.id === id)?.label || '平台数据';

const catalogCards = computed<DisplayCard[]>(() =>
  catalogItems.map((item) => {
    const region = getCatalogItemRegion(item);
    return {
      key: `catalog:${item.id}`,
      catalogId: item.id,
      name: item.title,
      description: item.description,
      dataTypeId: item.dataTypeId,
      dataTypeLabel: getTypeLabel(item.dataTypeId),
      sourceId: item.sourceId,
      sourceLabel: getSourceLabel(item.sourceId),
      regionId: item.regionId,
      regionLabel: region?.name,
      statusLabel: item.statusLabel,
      center_x: region?.center[0],
      center_y: region?.center[1],
      extent: region?.bbox,
      srid: 4326,
    };
  })
);

const inferAssetDataType = (asset: GeoDataItem): CatalogDataTypeId => {
  if (asset.asset_family === 'raster' || asset.type === '栅格') return 'remote-sensing';
  if (asset.asset_family === 'vector' || asset.type === '矢量') return 'vector';
  if (asset.dataset_id) return 'thematic';
  return 'geology-point';
};

const assetCards = computed<DisplayCard[]>(() =>
  assets.value.map((asset) => {
    const dataTypeId = inferAssetDataType(asset);
    return {
      key: `asset:${asset.id}`,
      id: asset.id,
      name: asset.name,
      description: asset.description,
      type: asset.type,
      dataTypeId,
      dataTypeLabel: getTypeLabel(dataTypeId),
      sourceId: 'platform',
      sourceLabel: getSourceLabel('platform'),
      uploadTime: asset.uploadTime,
      center_x: asset.center_x,
      center_y: asset.center_y,
      extent: asset.extent,
      srid: asset.srid,
    };
  })
);

const displayCards = computed(() => {
  const keyword = searchQuery.value;
  const filterPayload = {
    regionId: filters.regionId || undefined,
    dataTypeId: filters.dataTypeId || undefined,
    sourceId: filters.sourceId || undefined,
    keyword,
  };

  const matchedCatalogCards = catalogCards.value.filter((card) => {
    const item = catalogItems.find((entry) => entry.id === card.catalogId);
    return item ? matchesCatalogFilter(item, filterPayload) : false;
  });

  const matchedAssetCards = assetCards.value.filter((card) => {
    if (filters.regionId) return false;
    if (filters.dataTypeId && card.dataTypeId !== filters.dataTypeId) return false;
    if (filters.sourceId && card.sourceId !== filters.sourceId) return false;
    if (!keyword.trim()) return true;
    return `${card.name} ${card.description || ''}`.toLowerCase().includes(keyword.trim().toLowerCase());
  });

  return [...matchedCatalogCards, ...matchedAssetCards];
});

const resetFilters = () => {
  filters.regionId = '';
  filters.dataTypeId = '';
  filters.sourceId = '';
  searchQuery.value = '';
};

const loadAssets = async (query = '') => {
  loading.value = true;
  try {
    let res;
    if (query) {
      res = await geoDataApi.search(query);
    } else {
      res = await geoDataApi.getList();
    }
    
    // Use type assertion or check response structure
    const data = Array.isArray(res) ? res : (res as any).data || [];
    assets.value = data;
  } catch (e) {
    console.error(e);
    ElMessage.error('获取地质数据失败');
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  if (!filters.regionId && !filters.dataTypeId && !filters.sourceId) {
    loadAssets(searchQuery.value);
  }
};

onMounted(() => {
  loadAssets();
});

const buildCardQuery = (card: DisplayCard) => {
  const query: Record<string, string> = {
    name: card.name,
  };
  if (card.id) query.id = String(card.id);
  if (card.catalogId) {
    query.catalog = card.catalogId;
    query.layer = card.catalogId;
  }
  if (card.regionId) query.region = card.regionId;
  if (typeof card.center_x === 'number' && typeof card.center_y === 'number') {
    query.center = `${card.center_x},${card.center_y}`;
    query.lat = String(card.center_y);
    query.lon = String(card.center_x);
  }
  if (!card.regionId) query.zoom = '14';
  return query;
};

const handleView = (card: DisplayCard) => {
  router.push({
    name: 'Map',
    query: buildCardQuery(card),
  });
};

const handleLocate = (card: DisplayCard) => {
  router.push({
    name: 'Map',
    query: {
      ...buildCardQuery(card),
      action: 'locate',
    },
  });
};
</script>

<style scoped>
.gallery-view {
  width: 100vw;
  height: 100vh;
  background: #f5f7fa; /* Fallback */
  background-image: radial-gradient(circle at 50% 50%, #eef2f8 0%, #dbe4ef 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.glass-panel {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}

.gallery-header {
  height: 70px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  z-index: 10;
}

.filter-strip {
  margin: 18px 30px 0;
  padding: 14px 18px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  border-radius: 18px;
}

.filter-block {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-title {
  font-size: 13px;
  font-weight: 700;
  color: #425466;
}

.reset-filter {
  margin-left: auto;
  color: #52616f;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  border: none;
  background: rgba(255, 255, 255, 0.5);
  transition: all 0.3s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.8);
  transform: scale(1.1);
}

.title {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.5px;
}

.search-input {
  width: 300px;
  --el-input-bg-color: rgba(255, 255, 255, 0.5);
  --el-input-border-color: transparent;
  --el-input-hover-border-color: rgba(0, 0, 0, 0.1);
  --el-input-focus-border-color: #409EFF;
}

.gallery-content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 30px;
  padding-bottom: 40px;
}

.asset-card {
  border-radius: 20px;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  cursor: default;
  display: flex;
  flex-direction: column;
  height: 320px;
}

.asset-card:hover {
  transform: scale(1.05);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
  z-index: 5;
}

.card-preview {
  height: 180px;
  background: rgba(240, 244, 250, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.preview-icon {
  transition: transform 0.4s ease;
}

.asset-card:hover .preview-icon {
  transform: scale(1.1);
}

.card-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.card-overlay.visible {
  opacity: 1;
}

.card-info {
  padding: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.asset-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
}

.region-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  margin-bottom: 8px;
}

.source-tag {
  background: rgba(45, 90, 39, 0.1);
  color: #2d5a27;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
  font-weight: 500;
}

.date {
  font-size: 12px;
  color: #909399;
}

.asset-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>
