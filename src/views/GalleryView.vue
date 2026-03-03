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
          prefix-icon="Search"
          class="search-input"
          clearable
        />
      </div>
    </div>

    <div class="gallery-content custom-scrollbar">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="3" animated />
      </div>
      
      <div v-else-if="filteredAssets.length === 0" class="empty-state">
        <el-empty description="暂无公开地质数据" />
      </div>

      <div v-else class="card-grid">
        <div 
          v-for="asset in filteredAssets" 
          :key="asset.id" 
          class="asset-card glass-panel"
          @mouseenter="hoveredId = asset.id"
          @mouseleave="hoveredId = null"
        >
          <div class="card-preview">
            <div class="preview-icon">
              <el-icon :size="48" color="#409EFF" v-if="asset.type === '矢量'"><Location /></el-icon>
              <el-icon :size="48" color="#67C23A" v-else-if="asset.type === '栅格'"><Picture /></el-icon>
              <el-icon :size="48" color="#E6A23C" v-else><Document /></el-icon>
            </div>
            <div class="card-overlay" :class="{ 'visible': hoveredId === asset.id }">
              <el-button type="primary" round @click="handleView(asset)">
                去查看 <el-icon class="el-icon--right"><Right /></el-icon>
              </el-button>
            </div>
          </div>
          
          <div class="card-info">
            <h3 class="asset-name" :title="asset.name">{{ asset.name }}</h3>
            <div class="asset-meta">
              <span class="tag type-tag">{{ asset.type }}</span>
              <span class="date">{{ formatDate(asset.uploadTime) }}</span>
            </div>
            <p class="asset-desc">{{ asset.description || '暂无描述信息' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowLeft, Search, Location, Picture, Document, Right } from '@element-plus/icons-vue';
import { geoDataApi, type GeoDataItem } from '@/api/geodata';
import { ElMessage } from 'element-plus';

const router = useRouter();
const assets = ref<GeoDataItem[]>([]);
const loading = ref(true);
const searchQuery = ref('');
const hoveredId = ref<number | null>(null);

const filteredAssets = computed(() => {
  if (!searchQuery.value) return assets.value;
  const q = searchQuery.value.toLowerCase();
  return assets.value.filter(a => 
    a.name.toLowerCase().includes(q) || 
    (a.description && a.description.toLowerCase().includes(q))
  );
});

const formatDate = (dateStr: string) => {
  if (!dateStr) return '';
  return dateStr.split('T')[0];
};

const loadAssets = async () => {
  loading.value = true;
  try {
    const res = await geoDataApi.getList();
    // Use type assertion or check response structure
    const data = Array.isArray(res) ? res : (res as any).data || [];
    assets.value = data;
  } catch (e) {
    console.error(e);
    ElMessage.error('加载数据失败');
  } finally {
    loading.value = false;
  }
};

const handleView = (asset: GeoDataItem) => {
  if (asset.center_x && asset.center_y) {
    router.push({
      name: 'Map', // Ensure route name matches
      query: {
        lat: asset.center_y,
        lon: asset.center_x,
        zoom: 14,
        id: asset.id,
        name: asset.name
      }
    });
  } else {
    ElMessage.warning('该数据缺少坐标信息，无法定位');
    // Still go to map? Maybe just go to map center
    router.push({ name: 'Map' });
  }
};

onMounted(() => {
  loadAssets();
});
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
