<template>
  <div class="geology-hall">
    <!-- Left Sidebar: Filters -->
    <div 
        class="sidebar glass-morphism left-panel"
    >
      <div class="sidebar-header">
        <h2>地质数据大厅</h2>
        <div class="sidebar-actions">
            <el-dropdown @command="handleExport">
                <el-button type="primary" link>
                    导出数据 <el-icon class="el-icon--right"><Download /></el-icon>
                </el-button>
                <template #dropdown>
                    <el-dropdown-menu>
                        <el-dropdown-item command="excel">Excel (.xlsx)</el-dropdown-item>
                        <el-dropdown-item command="csv">CSV (.csv)</el-dropdown-item>
                        <el-dropdown-item command="shapefile">Shapefile (.zip)</el-dropdown-item>
                        <el-dropdown-item command="markdown">Markdown (.md)</el-dropdown-item>
                        <el-dropdown-item command="pdf">PDF (.pdf)</el-dropdown-item>
                    </el-dropdown-menu>
                </template>
            </el-dropdown>
        </div>
      </div>
      
      <!-- Filter Tree -->
      <el-scrollbar class="filter-tree-container">
        <el-collapse v-model="activeNames">
          <el-collapse-item title="专题数据" name="catalog">
            <div class="catalog-list">
              <button
                v-for="item in hallCatalogItems"
                :key="item.id"
                class="catalog-entry"
                @click="openCatalogDataset(item.id)"
              >
                <div class="catalog-entry-main">
                  <span class="catalog-entry-title">{{ item.title }}</span>
                  <span class="catalog-entry-region">{{ getCatalogRegionLabel(item.id) }}</span>
                </div>
                <div class="catalog-entry-meta">
                  <span class="catalog-entry-type">{{ getCatalogTypeLabel(item.id) }}</span>
                  <span v-if="item.statusLabel" class="catalog-entry-status">{{ item.statusLabel }}</span>
                </div>
              </button>
            </div>
          </el-collapse-item>

          <el-collapse-item title="地质年代" name="era">
            <div class="filter-group">
              <el-tag 
                v-for="(_, era) in stats.eras" 
                :key="era"
                :type="filters.era === era ? 'primary' : 'info'"
                class="filter-tag"
                @click="toggleFilter('era', era)"
              >
                {{ era }} ({{ stats.eras[era] }})
              </el-tag>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="岩性分类" name="lithology">
            <div class="filter-group">
              <el-tag 
                v-for="(_, lith) in stats.lithologies" 
                :key="lith"
                :type="filters.lithology === lith ? 'success' : 'info'"
                class="filter-tag"
                @click="toggleFilter('lithology', lith)"
              >
                {{ lith }} ({{ stats.lithologies[lith] }})
              </el-tag>
            </div>
          </el-collapse-item>

          <el-collapse-item title="构造类型" name="structure">
             <div class="filter-group">
              <el-tag 
                v-for="(_, str) in stats.structures" 
                :key="str"
                :type="filters.structure === str ? 'warning' : 'info'"
                class="filter-tag"
                @click="toggleFilter('structure', str)"
              >
                {{ str }} ({{ stats.structures[str] }})
              </el-tag>
            </div>
          </el-collapse-item>

          <el-collapse-item title="矿产资源" name="mineral">
             <div class="filter-group">
              <el-tag 
                v-for="(_, min) in stats.minerals" 
                :key="min"
                :type="filters.mineral === min ? 'danger' : 'info'"
                class="filter-tag"
                @click="toggleFilter('mineral', min)"
              >
                {{ min }} ({{ stats.minerals[min] }})
              </el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-scrollbar>
      
      <div class="list-summary">
        <span>共找到 {{ featureCount }} 条数据</span>
      </div>
    </div>

    <!-- Map Container -->
    <div class="map-wrapper">
      <div id="geology-map" class="map-container"></div>
      
      <!-- Hover Trigger Zone -->
      <!-- <div 
        v-if="!isSidebarClosedPermanently"
        class="sidebar-trigger"
        @mouseenter="handleSidebarHover(true)"
      ></div> -->

      <!-- Top Smart Search & User Profile -->
      <div class="top-search-container">
        <SmartSearchBox 
          @search-result="handleSmartSearchResult"
        />
      </div>
      
      <!-- User Profile (Top Right) -->
      <div class="user-profile-container glass-morphism">
          <el-dropdown @command="handleUserCommand">
            <div class="user-info">
                <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
                <span class="username">{{ authStore.user?.username || 'User' }}</span>
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </div>
            <template #dropdown>
                <el-dropdown-menu>
                    <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                    <el-dropdown-item divided command="logout" style="color: #F56C6C;">退出登录</el-dropdown-item>
                </el-dropdown-menu>
            </template>
          </el-dropdown>
      </div>

      <!-- Right Panel: Feature Details or List -->
      <Transition name="slide-right">
        <div v-if="selectedFeatures.length > 0" class="right-panel glass-morphism">
            <div class="panel-header">
                <h3>
                    <span v-if="focusedFeature || selectedFeatures.length === 1">
                        <el-button link @click="clearSelection" style="margin-right: 5px; padding: 0;">
                            <el-icon :size="18"><Back /></el-icon>
                        </el-button>
                        {{ (focusedFeature || selectedFeatures[0]).properties.name }}
                    </span>
                    <span v-else>已选择 {{ selectedFeatures.length }} 个地质点</span>
                </h3>
                <div class="panel-actions">
                    <el-dropdown v-if="!focusedFeature && selectedFeatures.length > 1" @command="handleBulkExport" trigger="click" size="small">
                        <el-button type="primary" size="small" link :disabled="checkedFeatures.size === 0">
                            批量导出 ({{ checkedFeatures.size }}) <el-icon class="el-icon--right"><Download /></el-icon>
                        </el-button>
                        <template #dropdown>
                            <el-dropdown-menu>
                                <el-dropdown-item command="excel">打开导出配置...</el-dropdown-item>
                            </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                    <el-button link @click="selectedFeatures = []; focusedFeature = null"><el-icon><Close /></el-icon></el-button>
                </div>
            </div>
            
            <div class="panel-body">
                <!-- Single Feature Details -->
                <div v-if="focusedFeature || selectedFeatures.length === 1">
                     <div v-if="currentFeature" class="feature-image-card">
                        <div v-if="featureImageLoading" class="feature-image-skeleton">
                            <div class="feature-image-skeleton-box"></div>
                            <div class="feature-image-skeleton-line"></div>
                        </div>
                        <div v-else-if="featureImageUrl" class="feature-image-wrapper">
                            <el-image
                                :src="featureImageUrl"
                                fit="cover"
                                class="feature-image"
                                :preview-src-list="[featureImageUrl]"
                                :preview-teleported="true"
                            />
                        </div>
                        <div v-else class="feature-image-empty">
                            暂无样例图片
                        </div>
                     </div>
                     <div class="single-feature-actions" style="margin-bottom: 10px; text-align: right;">
                         <el-button type="primary" size="small" @click="openExportDialog([currentFeature!])">
                             导出此点数据 <el-icon class="el-icon--right"><Download /></el-icon>
                         </el-button>
                     </div>
                     <el-descriptions :column="1" border size="small">
                        <el-descriptions-item label="ID">
                             <el-tag size="small">{{ currentFeature?.properties.id }}</el-tag>
                        </el-descriptions-item>
                        <el-descriptions-item label="年代">
                            <span v-html="highlight(currentFeature?.properties.era, 'era')"></span>
                        </el-descriptions-item>
                        <el-descriptions-item label="岩性">
                             <span v-html="highlight(currentFeature?.properties.rock_type, 'rock_type')"></span>
                        </el-descriptions-item>
                        <el-descriptions-item label="构造">
                             <span v-html="highlight(currentFeature?.properties.structure_type, 'structure_type')"></span>
                        </el-descriptions-item>
                        <el-descriptions-item label="矿产">
                             <span v-html="highlight(currentFeature?.properties.mineral, 'mineral')"></span>
                        </el-descriptions-item>
                        <el-descriptions-item label="海拔">{{ currentFeature?.properties.elevation }} m</el-descriptions-item>
                        <el-descriptions-item label="日期">{{ currentFeature?.properties.sample_date }}</el-descriptions-item>
                    </el-descriptions>
                    <div class="desc-text" v-html="highlight(currentFeature?.properties.description, 'description')">
                    </div>
                </div>

                <!-- Multiple Features List -->
                <div v-else class="feature-list">
                    <!-- Batch Filter -->
                    <div class="batch-filter">
                         <el-select v-model="batchFilterEra" placeholder="筛选年代" size="small" clearable style="width: 100%; margin-bottom: 5px">
                            <el-option v-for="(_, era) in stats.eras" :key="era" :label="era" :value="era" />
                         </el-select>
                         <el-select v-model="batchFilterLith" placeholder="筛选岩性" size="small" clearable style="width: 100%; margin-bottom: 5px">
                            <el-option v-for="(_, lith) in stats.lithologies" :key="lith" :label="lith" :value="lith" />
                         </el-select>
                         
                         <div class="filter-actions" style="display: flex; justify-content: space-between; align-items: center; margin-top: 5px;">
                             <el-checkbox 
                                :model-value="isAllChecked" 
                                :indeterminate="isIndeterminate"
                                @change="handleCheckAllChange"
                             >
                                全选
                             </el-checkbox>
                             <div class="filter-count">
                                 筛选: {{ filteredSelection.length }}
                             </div>
                         </div>
                    </div>

                    <div 
                        v-for="feature in filteredSelection.slice(0, 50)" 
                        :key="feature.properties.id" 
                        class="feature-item"
                        @click="selectSingle(feature)"
                    >
                        <div class="feature-item-header">
                            <div class="feature-item-title">
                                <el-checkbox 
                                    :model-value="checkedFeatures.has(feature.properties.id)"
                                    @click.stop="toggleCheck(feature.properties.id)"
                                />
                                <span class="feature-name" style="margin-left: 8px;">{{ feature.properties.name }}</span>
                            </div>
                            <el-tag size="small">{{ feature.properties.lithology_class }}</el-tag>
                        </div>
                        <div class="feature-item-sub">
                            {{ feature.properties.era }} | {{ feature.properties.elevation }}m
                        </div>
                    </div>
                    <div v-if="filteredSelection.length > 50" class="more-items">
                        ... 还有 {{ filteredSelection.length - 50 }} 条数据
                    </div>
                </div>
            </div>
        </div>
      </Transition>

      <!-- User Profile Dialog -->
      <el-dialog v-model="profileDialogVisible" title="个人中心" width="800px" class="profile-dialog">
        <el-tabs v-model="profileActiveTab">
            <!-- Basic Profile -->
            <el-tab-pane label="个人资料" name="profile">
                <div class="profile-tab-content">
                    <div class="avatar-section">
                        <el-avatar :size="100" :src="userProfileForm.avatar" />
                        <el-button size="small" style="margin-top: 10px;" @click="handleAvatarUpload">修改头像</el-button>
                    </div>
                    <el-form :model="userProfileForm" label-width="80px" style="flex: 1;">
                        <el-form-item label="用户名">
                            <el-input v-model="userProfileForm.username" disabled />
                        </el-form-item>
                        <el-form-item label="邮箱">
                            <el-input v-model="userProfileForm.email" />
                        </el-form-item>
                        <el-form-item label="当前角色">
                            <el-tag :type="isAdmin ? 'danger' : 'info'">{{ authStore.role }}</el-tag>
                        </el-form-item>
                        <el-form-item>
                            <el-button type="primary" @click="handleUpdateProfile">保存修改</el-button>
                        </el-form-item>
                    </el-form>
                </div>
            </el-tab-pane>

            <!-- Security -->
            <el-tab-pane label="安全设置" name="security">
                <el-form :model="passwordForm" label-width="100px" style="max-width: 400px; padding: 20px;">
                    <el-form-item label="旧密码">
                        <el-input v-model="passwordForm.oldPassword" type="password" show-password />
                    </el-form-item>
                    <el-form-item label="新密码">
                        <el-input v-model="passwordForm.newPassword" type="password" show-password />
                    </el-form-item>
                    <el-form-item label="确认新密码">
                        <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
                    </el-form-item>
                    <el-form-item>
                        <el-button type="primary" @click="handleChangePassword">修改密码</el-button>
                    </el-form-item>
                </el-form>
            </el-tab-pane>

            <!-- Admin Functions (Conditional) -->
            <el-tab-pane v-if="isAdmin" label="系统管理" name="admin">
                <div class="admin-tab-content" style="padding: 20px;">
                    <el-alert title="系统管理员权限已激活" type="warning" :closable="false" style="margin-bottom: 20px;" />
                    <el-row :gutter="20">
                        <el-col :span="12">
                            <el-card shadow="hover" header="用户管理">
                                <p style="font-size: 13px; color: #909399;">管理系统所有注册用户及其权限分配。</p>
                                <el-button type="primary" size="small" plain @click="ElMessage.info('用户管理模块加载中...')">进入管理</el-button>
                            </el-card>
                        </el-col>
                        <el-col :span="12">
                            <el-card shadow="hover" header="数据审核">
                                <p style="font-size: 13px; color: #909399;">审核用户提交的地质数据和共享内容。</p>
                                <el-button type="success" size="small" plain @click="ElMessage.info('审核队列为空')">开始审核</el-button>
                            </el-card>
                        </el-col>
                    </el-row>
                    <el-row :gutter="20" style="margin-top: 20px;">
                        <el-col :span="12">
                            <el-card shadow="hover" header="系统日志">
                                <p style="font-size: 13px; color: #909399;">查看用户操作日志和系统运行异常。</p>
                                <el-button type="info" size="small" plain @click="ElMessage.info('正在获取最新日志...')">查看日志</el-button>
                            </el-card>
                        </el-col>
                        <el-col :span="12">
                            <el-card shadow="hover" header="权限分配">
                                <p style="font-size: 13px; color: #909399;">灵活调整不同角色的功能访问白名单。</p>
                                <el-button type="warning" size="small" plain @click="ElMessage.info('权限引擎初始化中...')">配置权限</el-button>
                            </el-card>
                        </el-col>
                    </el-row>
                </div>
            </el-tab-pane>
        </el-tabs>
      </el-dialog>

      <!-- Export Preview Dialog -->
      <el-dialog v-model="exportDialogVisible" title="导出数据预览" width="500px">
        <div class="export-preview">
            <el-form label-width="100px">
                <el-form-item label="数据总量">
                    <span class="highlight-text">{{ filteredSelection.length }} 条</span>
                </el-form-item>
                <el-form-item label="导出格式">
                    <el-radio-group v-model="exportFormat">
                        <el-radio label="excel">Excel</el-radio>
                        <el-radio label="csv">CSV</el-radio>
                        <el-radio label="shapefile">Shapefile</el-radio>
                        <el-radio label="markdown">Markdown</el-radio>
                        <el-radio label="pdf">PDF</el-radio>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="坐标系">
                     <el-select v-model="exportSrid" placeholder="选择坐标系">
                        <el-option label="WGS84 (EPSG:4326)" :value="4326" />
                        <el-option label="Web Mercator (EPSG:3857)" :value="3857" />
                        <el-option label="CGCS2000 (EPSG:4490)" :value="4490" />
                     </el-select>
                </el-form-item>
            </el-form>
            
            <div class="data-integrity-check" v-if="filteredSelection.length > 0">
                 <el-alert
                    :title="`数据完整性检查通过：所有 ${filteredSelection.length} 条数据均包含必要属性`"
                    type="success"
                    show-icon
                    :closable="false"
                 />
            </div>
        </div>
        <template #footer>
            <span class="dialog-footer">
                <el-button @click="exportDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmExport">确认导出</el-button>
            </span>
        </template>
      </el-dialog>

      <!-- Tool Components -->
      <Transition name="fade">
        <LayerManager 
            v-if="showLayerManager" 
            :map="map" 
            @close="showLayerManager = false" 
        />
      </Transition>
      
      <Transition name="fade">
        <UploadPanel 
            v-if="showUploadPanel" 
            @close="showUploadPanel = false" 
            @upload-success="loadFeatures"
        />
      </Transition>
      
      <ShareDialog 
        v-model:visible="showShareDialog"
        :map-state="mapState"
      />

      <!-- Bottom Dock -->
      <BottomDock 
          :active-tool="activeTool"
          @home="resetView"
          @open-gallery="$router.push('/gallery')"
          @toggle-measure="toggleMeasure"
          @toggle-selection="toggleSelection"
          @toggle-layers="showLayerManager = !showLayerManager"
          @upload="showUploadPanel = !showUploadPanel"
          @share-view="handleShareView"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, watch, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { Close, Download, Back, ArrowDown } from '@element-plus/icons-vue';
import { geologyApi, type FeatureGeoJSON, type GeologyFilterParams } from '@/api/geology';
import SmartSearchBox from '@/views/map/components/SmartSearchBox.vue';
import BottomDock from '@/components/layout/BottomDock.vue';
import { useAuthStore } from '@/stores/auth';
import { useGeologyStore } from '@/stores/geology';
import {
    catalogItems,
    catalogDataTypes,
    getCatalogItemRegion,
} from '@/config/geodataCatalog';
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import XYZ from 'ol/source/XYZ';
import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';
import Cluster from 'ol/source/Cluster';
import GeoJSON from 'ol/format/GeoJSON';
import { Circle as CircleStyle, Fill, Stroke, Style, Text } from 'ol/style';
import { boundingExtent } from 'ol/extent';
import { ElMessage, ElLoading } from 'element-plus';
import { toLonLat } from 'ol/proj';
import { toMapCoords, MapSelectionManager, MeasureManager } from '@/services/mapInteraction';

import LayerManager from '@/components/map/LayerManager.vue';
import UploadPanel from '@/components/map/UploadPanel.vue';
import ShareDialog from '@/components/map/ShareDialog.vue';

const router = useRouter();
const authStore = useAuthStore();
const geologyStore = useGeologyStore();
const { stats, filters, totalCount, features: storeFeatures } = storeToRefs(geologyStore);
const searchQuery = ref(''); 
const activeNames = ref(['catalog', 'era', 'lithology']);
const featureCount = computed(() => totalCount.value || storeFeatures.value.length);
const selectedFeatures = ref<FeatureGeoJSON[]>([]);
const activeTool = ref('');

// Dialogs State
const showLayerManager = ref(false);
const showUploadPanel = ref(false);
const showShareDialog = ref(false);
const mapState = ref<any>({});

// Sidebar State - Removed interactive logic
// const isSidebarVisible = ref(false); // Default hidden
// const isSidebarClosedPermanently = ref(sessionStorage.getItem('sidebarClosed') === 'true');
// let sidebarHoverTimeout: any = null;

// const handleSidebarHover = (show: boolean) => {
//     if (isSidebarClosedPermanently.value) return; 
//     if (sidebarHoverTimeout) clearTimeout(sidebarHoverTimeout);
//     if (show) {
//         isSidebarVisible.value = true;
//     }
// };

// const closeSidebar = () => {
//     isSidebarVisible.value = false;
//     isSidebarClosedPermanently.value = true;
//     sessionStorage.setItem('sidebarClosed', 'true');
// };

// const handleMapClick = (e: MouseEvent) => {
//     // if (isSidebarVisible.value) {
//     //     isSidebarVisible.value = false;
//     // }
// };

const handleUserCommand = (command: string) => {
    if (command === 'logout') {
        authStore.logout();
        router.push('/login');
        ElMessage.success('已退出登录');
    } else if (command === 'profile') {
        profileDialogVisible.value = true;
    }
};

// User Profile
const profileDialogVisible = ref(false);
const profileActiveTab = ref('profile');
const isAdmin = computed(() => authStore.hasRole('admin'));

const userProfileForm = reactive({
    username: authStore.user?.username || '',
    email: authStore.user?.email || '',
    avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
});

const passwordForm = reactive({
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
});

const handleUpdateProfile = () => {
    ElMessage.success('个人资料已更新');
};

const handleChangePassword = () => {
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        ElMessage.error('两次输入的密码不一致');
        return;
    }
    ElMessage.success('密码修改成功');
};

const handleAvatarUpload = () => {
    ElMessage.info('头像上传功能开发中...');
};

// Batch Filter & Export
const batchFilterEra = ref('');
const batchFilterLith = ref('');
const exportDialogVisible = ref(false);
const exportFormat = ref<'excel' | 'csv' | 'shapefile' | 'markdown' | 'pdf'>('excel');
const exportSrid = ref(4326);
const exportTargets = ref<FeatureGeoJSON[]>([]);
// Checkbox selection state
const checkedFeatures = ref<Set<number>>(new Set());
const hallCatalogItems = computed(() => catalogItems);

const focusedFeature = ref<FeatureGeoJSON | null>(null);
const currentFeature = computed(() => focusedFeature.value || selectedFeatures.value[0] || null);
const featureImageUrl = ref<string | null>(null);
const featureImageLoading = ref(false);
let featureImageRequestId = 0;

const filteredSelection = computed(() => {
    if (!selectedFeatures.value.length) return [];
    return selectedFeatures.value.filter(f => {
        const props = f.properties;
        if (batchFilterEra.value && props.era !== batchFilterEra.value) return false;
        if (batchFilterLith.value && props.lithology_class !== batchFilterLith.value) return false;
        return true;
    });
});

// Initialize checked state when selection changes
watch(selectedFeatures, (newVal) => {
    // By default, check all when new selection is made via DragBox
    const ids = new Set<number>();
    newVal.forEach(f => ids.add(f.properties.id));
    checkedFeatures.value = ids;
    focusedFeature.value = null; // Clear focus when new selection arrives
});

const isAllChecked = computed(() => {
    if (filteredSelection.value.length === 0) return false;
    // Check if all filtered items are in checkedFeatures
    return filteredSelection.value.every(f => checkedFeatures.value.has(f.properties.id));
});

const isIndeterminate = computed(() => {
    if (filteredSelection.value.length === 0) return false;
    const checkedCount = filteredSelection.value.filter(f => checkedFeatures.value.has(f.properties.id)).length;
    return checkedCount > 0 && checkedCount < filteredSelection.value.length;
});

const handleCheckAllChange = (val: boolean) => {
    if (val) {
        filteredSelection.value.forEach(f => checkedFeatures.value.add(f.properties.id));
    } else {
        filteredSelection.value.forEach(f => checkedFeatures.value.delete(f.properties.id));
    }
};

const toggleCheck = (id: number) => {
    if (checkedFeatures.value.has(id)) {
        checkedFeatures.value.delete(id);
    } else {
        checkedFeatures.value.add(id);
    }
};

const getCatalogRegionLabel = (catalogId: string) => {
    const item = catalogItems.find((entry) => entry.id === catalogId);
    const region = item ? getCatalogItemRegion(item) : undefined;
    return region?.shortName || '专题数据';
};

const getCatalogTypeLabel = (catalogId: string) => {
    const item = catalogItems.find((entry) => entry.id === catalogId);
    return catalogDataTypes.find((entry) => entry.id === item?.dataTypeId)?.label || '专题数据';
};

const openCatalogDataset = (catalogId: string) => {
    const item = catalogItems.find((entry) => entry.id === catalogId);
    if (!item) return;

    router.push({
        name: 'Map',
        query: {
            catalog: item.id,
            layer: item.id,
            region: item.regionId,
        }
    });
};

let selectionManager: MapSelectionManager<FeatureGeoJSON> | null = null;
let measureManager: MeasureManager | null = null;

let map: Map | null = null;
let clusterSource: Cluster | null = null;
let vectorSource: VectorSource | null = null;

onMounted(async () => {
    initMap();
    await geologyStore.fetchStats();
    await loadFeatures();
});

onUnmounted(() => {
    featureImageRequestId += 1;
    if (featureImageUrl.value) {
        window.URL.revokeObjectURL(featureImageUrl.value);
        featureImageUrl.value = null;
    }
    selectionManager?.destroy();
    measureManager?.destroy();
    if (map) {
        map.setTarget(undefined);
    }
});

const initMap = () => {
    vectorSource = new VectorSource();
    
    clusterSource = new Cluster({
        distance: 40,
        source: vectorSource,
    });

    const styleCache: Record<number, Style> = {};
    const clusters = new VectorLayer({
        source: clusterSource,
        style: (feature) => {
            const size = feature.get('features').length;

            
            // Zoom control: Hide if zoom is too low (resolution too high)
            // Approx resolution at zoom 8 is ~611m/px. Let's say we hide below zoom 8.
            // But 'resolution' depends on projection. For Web Mercator:
            // Zoom 8 res ~= 611. Zoom 7 res ~= 1222.
            // If we want to hide when zoom < 8, we hide when res > 700 (approx).
            // Better to use map.getView().getZoom() but that might not be available inside style function immediately/reactively?
            // Style function is called on render.
            // Let's rely on layer minZoom property instead for efficiency? 
            // The user wants "Dynamic control". Layer minZoom is efficient.
            // But let's check the requirement: "Zoom < Threshold: Hide".
            // We can set `minZoom: 8` on the layer.
            
            if (size === 1) {
                // Single point style with label
                const originalFeature = feature.get('features')[0];
                const props = originalFeature.getProperties();
                
                return new Style({
                    image: new CircleStyle({
                        radius: 6,
                        fill: new Fill({ color: '#409EFF' }),
                        stroke: new Stroke({ color: '#fff', width: 2 })
                    }),
                    text: new Text({
                        text: props.name,
                        offsetY: -15,
                        fill: new Fill({ color: '#303133' }),
                        stroke: new Stroke({ color: '#fff', width: 3 }),
                        font: '12px sans-serif'
                    })
                });
            } else {
                // Cluster style
                let style = styleCache[size];
                if (!style) {
                    let color = '#409EFF';
                    if (size > 10) color = '#E6A23C';
                    if (size > 50) color = '#F56C6C';
                    
                    style = new Style({
                        image: new CircleStyle({
                            radius: 10 + Math.min(size, 20) * 0.5,
                            stroke: new Stroke({ color: '#fff', width: 2 }),
                            fill: new Fill({ color: color }),
                        }),
                        text: new Text({
                            text: size.toString(),
                            fill: new Fill({ color: '#fff' }),
                            font: 'bold 12px sans-serif'
                        }),
                    });
                    styleCache[size] = style;
                }
                return style;
            }
        },
    });
    
    // Set visibility threshold
    // 8 is a common threshold. 
    clusters.setMinZoom(8); 

    map = new Map({
        target: 'geology-map',
        layers: [
            new TileLayer({
                source: new XYZ({
                    url: 'https://t0.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=ba13e30aae52239f8056f1c7421cae7c',
                }),
                visible: true,
                properties: { title: '天地图矢量', type: 'base' }
            }),
             new TileLayer({
                source: new XYZ({
                    url: "https://t0.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=ba13e30aae52239f8056f1c7421cae7c"
                }),
                visible: true,
                properties: { title: '天地图注记', type: 'overlay' }
            }),
            new TileLayer({
                source: new XYZ({
                    url: 'https://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=ba13e30aae52239f8056f1c7421cae7c',
                }),
                visible: false,
                properties: { title: '天地图影像', type: 'base' }
            }),
            new TileLayer({
                source: new XYZ({
                    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    attributions: '&copy; OpenStreetMap contributors'
                }),
                visible: false,
                properties: { title: 'OpenStreetMap', type: 'base' }
            }),
            clusters,
        ],
        view: new View({
            center: toMapCoords([116.4, 40.2], 4326),
            zoom: 9,
        }),
    });
    
    // Set clusters property for Layer Manager
    clusters.set('title', '地质点聚类');
    clusters.set('type', 'overlay');
    // Ensure clusters are always on top
    clusters.setZIndex(100); 

    // Zoom level listener for smoother transitions or additional logic
    map.getView().on('change:resolution', () => {
        const zoom = map?.getView().getZoom();
        if (zoom && zoom < 8) {
            // Optional: Add a toast or indicator that points are hidden
            // But layer minZoom handles visibility efficiently.
        }
    });

    // Click interaction
    map.on('click', (e) => {
        if (activeTool.value === 'measure' || activeTool.value === 'selection') return; // Disable click select when measuring or selecting
        
        clusters.getFeatures(e.pixel).then((clickedFeatures) => {
            if (clickedFeatures.length) {
                const features = clickedFeatures[0].get('features');
                if (features.length > 1) {
                    const extent = boundingExtent(
                        features.map((r: any) => r.getGeometry().getCoordinates())
                    );
                    map?.getView().fit(extent, { duration: 1000, padding: [50, 50, 50, 50] });
                } else {
                    const feature = features[0];
                    const props = feature.getProperties();
                    // For single click, we set selectedFeatures to [f] AND focusedFeature to f
                    // So we see the detail view immediately
                    const f = {
                        type: "Feature",
                        geometry: { type: "Point", coordinates: [] }, 
                        properties: props
                    } as any;
                    selectedFeatures.value = [f];
                    focusedFeature.value = f;
                }
            } else {
                selectedFeatures.value = [];
                focusedFeature.value = null;
            }
        });
    });
    
    // Pointer cursor
    map.on('pointermove', (e) => {
        if (e.dragging) return;
        const pixel = map?.getEventPixel(e.originalEvent);
        const hit = map?.hasFeatureAtPixel(pixel!);
        map!.getTargetElement().style.cursor = hit ? 'pointer' : '';
    });
    
    selectionManager = new MapSelectionManager<FeatureGeoJSON>({
        map,
        source: vectorSource,
        mapFeatureToItem: (feature) => {
            const props = feature.getProperties();
            return {
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [] },
                properties: props
            } as unknown as FeatureGeoJSON;
        },
        onSelect: (selected) => {
            selectedFeatures.value = selected;
            focusedFeature.value = null;
        },
        onEmpty: () => {
            selectedFeatures.value = [];
            focusedFeature.value = null;
        }
    });

    measureManager = new MeasureManager({ map });
};

const resetView = () => {
    map?.getView().animate({
        center: toMapCoords([116.4, 40.2], 4326),
        zoom: 9,
        duration: 1000
    });
};

const loadFeatures = async () => {
    try {
        geologyStore.pageSize = 1000;
        geologyStore.setFilter('q', searchQuery.value || undefined);
        await geologyStore.fetchFeatures();
        if (vectorSource) {
            vectorSource.clear();
            const features = new GeoJSON().readFeatures(
              { type: 'FeatureCollection', features: storeFeatures.value },
              {
                featureProjection: 'EPSG:3857'
              }
            );
            vectorSource.addFeatures(features);
        }
    } catch (e) {
        console.error("Failed to load features", e);
        ElMessage.error("加载数据失败");
    }
};

const replaceFeatureImageUrl = (nextUrl: string | null) => {
    if (featureImageUrl.value && featureImageUrl.value !== nextUrl) {
        window.URL.revokeObjectURL(featureImageUrl.value);
    }
    featureImageUrl.value = nextUrl;
};

const loadFeatureImage = async (feature: FeatureGeoJSON | null) => {
    featureImageRequestId += 1;
    const requestId = featureImageRequestId;
    replaceFeatureImageUrl(null);
    featureImageLoading.value = false;

    if (!feature?.properties?.id || !feature.properties.image_path) {
        return;
    }

    featureImageLoading.value = true;
    try {
        const blob = await geologyApi.fetchFeatureImageBlob(feature.properties.id);
        if (requestId !== featureImageRequestId) return;
        replaceFeatureImageUrl(window.URL.createObjectURL(blob));
    } catch (error) {
        if (requestId !== featureImageRequestId) return;
        replaceFeatureImageUrl(null);
    } finally {
        if (requestId === featureImageRequestId) {
            featureImageLoading.value = false;
        }
    }
};

const handleSmartSearchResult = (results: any[]) => {
    console.log("Smart search results:", results);
    ElMessage.info("智能搜索结果已加载 (演示)");
};

const toggleFilter = (category: keyof GeologyFilterParams, value: string) => {
    const currentValue = (filters.value as any)[category];
    geologyStore.setFilter(category, currentValue === value ? undefined : value);
    loadFeatures();
};

const handleExport = async (format: 'excel' | 'csv' | 'shapefile' | 'markdown' | 'pdf') => {
    const params: any = { ...filters.value };
    if (searchQuery.value) params.q = searchQuery.value;
    Object.keys(params).forEach(key => {
        if (!params[key]) delete params[key];
    });

    const loading = ElLoading.service({
        lock: true,
        text: '正在生成导出文件...',
    });

    try {
        const blob = await geologyApi.exportData(format, params);
        const url = window.URL.createObjectURL(new Blob([blob]));
        const link = document.createElement('a');
        link.href = url;
        const ext = format === 'excel' ? 'xlsx' : 
                   format === 'shapefile' ? 'zip' : 
                   format === 'markdown' ? 'md' : 
                   format;
        link.setAttribute('download', `geology_full_export_${new Date().getTime()}.${ext}`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success('全量数据导出成功');
    } catch (e: any) {
        ElMessage.error('导出失败，请重试');
    } finally {
        loading.close();
    }
};

const handleBulkExport = () => {
    // Filter selectedFeatures by checkedFeatures
    const targets = selectedFeatures.value.filter(f => checkedFeatures.value.has(f.properties.id));
    
    if (targets.length === 0) {
        ElMessage.warning('请先勾选需要导出的地质点');
        return;
    }
    openExportDialog(targets);
};

const openExportDialog = (features: FeatureGeoJSON[]) => {
    exportTargets.value = features;
    if (features.length === 0) {
        ElMessage.warning('没有可导出的数据');
        return;
    }
    exportDialogVisible.value = true;
};

const confirmExport = async () => {
    if (exportTargets.value.length > 5000) {
        ElMessage.warning('导出数量超过限制 (5000)');
        return;
    }
    
    const loading = ElLoading.service({
        lock: true,
        text: '正在生成文件并准备下载...',
        background: 'rgba(0, 0, 0, 0.7)',
    });

    try {
        const ids = exportTargets.value.map(f => f.properties.id);
        const blob = await geologyApi.exportDataByIds(exportFormat.value, ids, exportSrid.value);
        
        // Handle file download from Blob
        const url = window.URL.createObjectURL(new Blob([blob]));
        const link = document.createElement('a');
        link.href = url;
        
        // Generate filename based on format
        const ext = exportFormat.value === 'excel' ? 'xlsx' : 
                   exportFormat.value === 'shapefile' ? 'zip' : 
                   exportFormat.value === 'markdown' ? 'md' : 
                   exportFormat.value;
        link.setAttribute('download', `geology_export_${new Date().getTime()}.${ext}`);
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        ElMessage.success(`成功导出 ${exportTargets.value.length} 条数据`);
        exportDialogVisible.value = false;
    } catch (e: any) {
        console.error('Export error:', e);
        ElMessage.error(`导出失败: ${e.message || '网络错误'}`);
    } finally {
        loading.close();
    }
};

const highlight = (text: string | undefined, field: string) => {
    if (!text) return '';
    const target = currentFeature.value;
    if (target?.properties.highlights && target.properties.highlights[field]) {
        return target.properties.highlights[field];
    }
    return text;
};

watch(currentFeature, (feature) => {
    void loadFeatureImage(feature);
}, { immediate: true });

const clearSelection = () => {
    if (focusedFeature.value) {
        focusedFeature.value = null;
    } else {
        selectedFeatures.value = [];
        focusedFeature.value = null;
    }
};

const selectSingle = (feature: FeatureGeoJSON) => {
    focusedFeature.value = feature;
};

// --- Selection Logic ---
const toggleSelection = () => {
    if (activeTool.value === 'selection') {
        activeTool.value = '';
        selectionManager?.disableDragBox();
        ElMessage.info('已关闭框选工具');
    } else {
        // If measuring is active, turn it off
        if (activeTool.value === 'measure') {
            measureManager?.stopMeasure();
        }
        activeTool.value = 'selection';
        selectionManager?.enableDragBox();
        ElMessage.success('已开启框选工具 (按住鼠标拖拽)');
    }
};

// --- Measurement Logic ---
const handleShareView = () => {
    if (map) {
        const view = map.getView();
        const center = toLonLat(view.getCenter() || [0, 0]);
        const zoom = view.getZoom();
        mapState.value = { center, zoom };
        showShareDialog.value = true;
    }
};

const toggleMeasure = () => {
    if (activeTool.value === 'measure') {
        activeTool.value = '';
        measureManager?.stopMeasure();
        measureManager?.clearMeasurements();
        ElMessage.info('已关闭测量工具');
    } else {
        if (activeTool.value === 'selection') {
            selectionManager?.disableDragBox();
        }
        activeTool.value = 'measure';
        measureManager?.startLineMeasure();
        ElMessage.success('已开启测量工具 (距离/面积)');
    }
};

</script>

<style scoped>
.geology-hall {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #f5f7fa;
}

.glass-morphism {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.left-panel {
  width: 320px;
  height: calc(100% - 40px); /* Adjust height for padding */
  display: flex;
  flex-direction: column;
  z-index: 20;
  /* border-right: 1px solid #eee; */ /* Removed right border for card look */
  position: absolute;
  left: 20px; /* Floating with margin */
  top: 20px;
  /* transform: translateX(-330px); */ /* Removed hidden transform */
  /* transition: transform 0.3s ease; */
  border-radius: 12px; /* Rounded corners */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Removed transition classes */
/*
.left-panel.sidebar-hidden {
}
.sidebar.sidebar-hidden {
    transform: translateX(-330px);
}
.sidebar:not(.sidebar-hidden) {
    transform: translateX(0);
}
*/

.sidebar-trigger {
    display: none; /* Removed */
}

.sidebar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.user-profile-container {
    position: absolute;
    top: 20px;
    right: 20px;
    z-index: 30;
    padding: 6px 12px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}

.username {
    font-size: 14px;
    color: #606266;
    font-weight: 500;
}

.profile-tab-content {
    display: flex;
    gap: 40px;
    padding: 30px;
}

.avatar-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 150px;
}

.right-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  width: 320px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  z-index: 20;
  border-radius: 8px;
  padding: 16px;
}

/* Transitions for Right Panel */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.filter-tree-container {
  flex: 1;
  padding: 0 16px;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 8px 0 4px;
}

.catalog-entry {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(64, 158, 255, 0.16);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 250, 255, 0.98));
  cursor: pointer;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.catalog-entry:hover {
  transform: translateY(-1px);
  border-color: rgba(64, 158, 255, 0.36);
  box-shadow: 0 10px 18px rgba(31, 78, 121, 0.08);
}

.catalog-entry-main,
.catalog-entry-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.catalog-entry-title {
  font-size: 13px;
  font-weight: 600;
  color: #25324a;
  line-height: 1.4;
}

.catalog-entry-region {
  flex-shrink: 0;
  font-size: 11px;
  color: #5f6f89;
  background: rgba(88, 125, 186, 0.1);
  border-radius: 999px;
  padding: 2px 8px;
}

.catalog-entry-meta {
  margin-top: 8px;
}

.catalog-entry-type,
.catalog-entry-status {
  font-size: 11px;
  color: #6b7280;
}

.catalog-entry-status {
  color: #2d6a4f;
}

.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
}

.filter-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.filter-tag:hover {
  transform: translateY(-2px);
}

.list-summary {
  padding: 12px 20px;
  background: #fff;
  border-top: 1px solid #eee;
  color: #909399;
  font-size: 12px;
  text-align: right;
}

.map-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
}

.map-container {
  width: 100%;
  height: 100%;
}

.top-search-container {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  width: 90%;
  max-width: 600px;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #eee;
}

.panel-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.panel-header h3 {
    margin: 0;
    font-size: 16px;
    color: #303133;
}

.feature-image-card {
    margin-bottom: 14px;
    border-radius: 10px;
    overflow: hidden;
    background: #f5f7fa;
    border: 1px solid #e5e7eb;
}

.feature-image-wrapper {
    width: 100%;
    height: 180px;
    background: linear-gradient(180deg, #eef4ff 0%, #f7fbff 100%);
}

.feature-image {
    width: 100%;
    height: 180px;
    display: block;
}

.feature-image-skeleton {
    padding: 14px;
}

.feature-image-skeleton-box {
    height: 150px;
    border-radius: 8px;
    background: linear-gradient(90deg, #eef2f7 25%, #f7f9fc 50%, #eef2f7 75%);
    background-size: 200% 100%;
    animation: geology-image-loading 1.4s ease infinite;
}

.feature-image-skeleton-line {
    margin-top: 10px;
    height: 10px;
    width: 45%;
    border-radius: 999px;
    background: linear-gradient(90deg, #eef2f7 25%, #f7f9fc 50%, #eef2f7 75%);
    background-size: 200% 100%;
    animation: geology-image-loading 1.4s ease infinite;
}

.feature-image-empty {
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
    font-size: 13px;
}

.desc-text {
    margin-top: 12px;
    color: #606266;
    font-size: 13px;
    line-height: 1.5;
    background: #f5f7fa;
    padding: 8px;
    border-radius: 4px;
}

/* Tooltip Styles */
:deep(.ol-tooltip) {
  position: relative;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
  color: white;
  padding: 4px 8px;
  opacity: 0.7;
  white-space: nowrap;
  font-size: 12px;
  pointer-events: none;
  user-select: none;
}
:deep(.ol-tooltip-measure) {
  opacity: 1;
  font-weight: bold;
}
:deep(.ol-tooltip-static) {
  background-color: #ffcc33;
  color: black;
  border: 1px solid white;
}
:deep(.ol-tooltip-measure:before),
:deep(.ol-tooltip-static:before) {
  border-top: 6px solid rgba(0, 0, 0, 0.5);
  border-right: 6px solid transparent;
  border-left: 6px solid transparent;
  content: "";
  position: absolute;
  bottom: -6px;
  margin-left: -7px;
  left: 50%;
}
:deep(.ol-tooltip-static:before) {
  border-top-color: #ffcc33;
}

/* DragBox Style */
:deep(.ol-dragbox) {
  background-color: rgba(64, 158, 255, 0.2);
  border: 2px solid #409EFF;
}

.feature-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.feature-item {
    padding: 10px;
    background: #fff;
    border: 1px solid #eee;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
}

.feature-item:hover {
    border-color: #409EFF;
    background: #ecf5ff;
}

.feature-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.feature-name {
    font-weight: bold;
    color: #303133;
    font-size: 14px;
}

.feature-item-sub {
    font-size: 12px;
    color: #909399;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes geology-image-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
