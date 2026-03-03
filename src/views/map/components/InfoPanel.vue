<template>
  <div class="side-panel-wrapper" :class="{ 'visible': visible }">
    <div class="side-panel glass-morphism">
      <div class="drag-handle-wrapper">
        <div class="drag-handle"></div>
      </div>

      <div class="panel-header">
        <h3 class="panel-title">{{ title }}</h3>
        <span class="role-badge" :class="roleBadgeClass">
           [{{ roleBadge }}]
        </span>
        <div class="close-btn" @click="$emit('close')">
          <el-icon><Close /></el-icon>
        </div>
      </div>
      
      <div class="panel-content custom-scrollbar">
        <!-- Single Feature Mode -->
      <div v-if="feature && !isMultiSelection" class="feature-detail">
        <div class="preview-card" v-if="feature?.type?.includes('TIF')">
          <div class="image-placeholder">
            <el-icon :size="32" color="#86868b"><Picture /></el-icon>
          </div>
        </div>
        
        <div class="info-block-group">
          <div class="info-block">
            <label>名称</label>
            <div class="value" v-if="!isEditing">{{ feature?.name || '未命名' }}</div>
            <el-input v-else v-model="editForm.name" size="small" />
          </div>
          
          <div class="info-block-row">
            <div class="info-block half">
              <label>类型</label>
              <div class="value"><span class="tag">{{ feature?.type }}</span></div>
            </div>
            <div class="info-block half">
               <label>上传时间</label>
               <div class="value">{{ feature?.uploadTime ? feature.uploadTime.split('T')[0] : 'N/A' }}</div>
            </div>
          </div>
          
          <div class="info-block" v-if="feature?.lithology || isEditing">
            <label>岩性</label>
            <div class="value" v-if="!isEditing">{{ feature.lithology }}</div>
            <el-input v-else v-model="editForm.lithology" size="small" />
          </div>
          
          <div class="info-block" v-if="feature?.description || isEditing">
            <label>描述</label>
            <div class="value" v-if="!isEditing">{{ feature.description }}</div>
            <el-input v-else type="textarea" :rows="3" v-model="editForm.description" size="small" />
          </div>
          
          <div class="info-block">
            <label>坐标</label>
            <div class="value monospace">{{ formattedCoordinates }}</div>
          </div>
        </div>

        <!-- NetCDF Metadata Section -->
        <div class="nc-section" v-if="feature?.metadata?.dims">
          <h4>多维数据信息</h4>
          <div class="info-block">
            <label>维度 (Dimensions)</label>
            <div class="tags-container">
              <span v-for="(size, dim) in feature.metadata.dims" :key="dim" class="tag dim-tag">
                {{ dim }}: {{ size }}
              </span>
            </div>
          </div>
          
          <div class="info-block" v-if="feature.metadata.variables && feature.metadata.variables.length">
            <label>变量 (Variables)</label>
            <div class="vars-list">
              <div 
                v-for="v in feature.metadata.variables" 
                :key="v.name" 
                class="var-item"
                @click="handleVisualizeNetCDF(v.name)"
              >
                <div class="var-icon"><el-icon><DataBoard /></el-icon></div>
                <div class="var-info">
                  <span class="var-name">{{ v.name }}</span>
                  <span class="var-desc">{{ v.long_name || v.name }}</span>
                </div>
                <span class="var-unit" v-if="v.units">{{ v.units }}</span>
                <el-icon class="action-icon" v-if="ncSliceLoading"><Loading /></el-icon>
                <el-icon class="action-icon" v-else><ViewIcon /></el-icon>
              </div>
            </div>
          </div>
        </div>

        <div class="reports-section" v-if="feature?.reports && feature.reports.length > 0">
          <h4>关联报告</h4>
          <div v-for="(report, index) in feature.reports" :key="index" class="report-item">
            <div class="report-icon"><el-icon><Document /></el-icon></div>
            <span class="report-title">{{ report.title }}</span>
            <el-button link type="primary" size="small" @click="handlePreviewReport(report)">预览</el-button>
          </div>
        </div>

        <div class="panel-actions">
          <button class="apple-btn primary-btn" @click="handleDownloadClick">
            <el-icon><Download /></el-icon> 下载数据
          </button>
          
          <!-- Admin Actions -->
          <div class="secondary-actions-grid" v-if="isAdmin">
             <button class="apple-btn secondary-btn" @click="$emit('share', feature)">
               <el-icon><Share /></el-icon> 分享链接
             </button>
             <button class="apple-btn secondary-btn" @click="isEditing ? handleSaveClick() : handleEditClick()">
               <el-icon v-if="!isEditing"><Edit /></el-icon>
               <el-icon v-else><Check /></el-icon> 
               {{ isEditing ? '保存修改' : '编辑属性' }}
             </button>
             <button class="apple-btn secondary-btn export-btn" @click="handleExportMarkdown">
               <el-icon><Document /></el-icon> 导出报告
             </button>
          </div>

          <!-- User Actions -->
          <div class="secondary-actions-grid" v-else>
            <button class="apple-btn secondary-btn" @click="$emit('share', feature)">
              <el-icon><Share /></el-icon> 分享链接
            </button>
            <button class="apple-btn secondary-btn request-btn" @click="handleRequestAccess">
              <el-icon><Link /></el-icon> 申请调取
            </button>
            <button class="apple-btn secondary-btn export-btn" @click="handleExportMarkdown">
              <el-icon><Document /></el-icon> 导出报告
            </button>
          </div>
        </div>
      </div>

      <!-- Multi Selection Mode -->
      <div v-else-if="isMultiSelection" class="multi-selection-list">
        <div class="selection-summary">
          <span>已选 {{ selectedItems?.length || 0 }} 个要素</span>
          <div class="batch-actions">
            <el-button type="primary" link size="small" @click="handleBatchDownloadClick">批量下载</el-button>
            <el-button type="primary" link size="small" @click="handleExportMarkdown">生成汇总报告</el-button>
          </div>
        </div>
        <div class="list-container custom-scrollbar">
          <div v-for="item in selectedItems" :key="item.id" class="list-item" @click="$emit('locate', item)">
            <div class="item-icon-circle">
              <el-icon><Location /></el-icon>
            </div>
            <div class="item-info">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-meta">
                {{ item.type }}
                <span v-if="item.distance" class="distance-tag">{{ item.distance.toFixed(0) }}m</span>
              </div>
            </div>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Close, Picture, Download, View as ViewIcon, Location, Document, ArrowRight, Share, DataBoard, Loading, Edit, Check, Link } from '@element-plus/icons-vue';
import type { GeoDataItem } from '@/views/map/types/map';
import { geoDataApi } from '@/api/geodata';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const isAdmin = computed(() => authStore.user?.role === 'admin');
const roleBadge = computed(() => isAdmin.value ? '系统管理员' : '授权研究员');
const roleBadgeClass = computed(() => isAdmin.value ? 'badge-admin' : 'badge-user');

const props = defineProps<{
  visible: boolean;
  title: string;
  feature?: GeoDataItem | null;
  isMultiSelection: boolean;
  selectedItems: GeoDataItem[];
}>();

// Editing state
const isEditing = ref(false);
const editForm = ref<Partial<GeoDataItem>>({});

// Watch feature change to reset edit state
watch(() => props.feature, (newVal) => {
  isEditing.value = false;
  if (newVal) {
    editForm.value = { ...newVal };
  }
}, { immediate: true });

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'download', item: GeoDataItem): void;
  (e: 'locate', item: GeoDataItem): void;
  (e: 'batch-download'): void;
  (e: 'preview-report', report: any): void;
  (e: 'share', item: GeoDataItem): void;
  (e: 'visualize-nc', data: any): void;
  (e: 'edit', item: GeoDataItem): void;
  (e: 'request-access', item: GeoDataItem): void;
  (e: 'update-feature', item: GeoDataItem): void;
}>();

const handleEditClick = () => {
  isEditing.value = true;
};

const handleSaveClick = async () => {
  // Call API to update (mock or real)
  // For now, emit event to parent or just update local state if no API ready
  // Assuming we might have an update API, or just emit to parent to handle
  try {
     // TODO: Implement update API call here
     // await geoDataApi.update(props.feature.id, editForm.value);
     emit('update-feature', { ...props.feature, ...editForm.value } as GeoDataItem);
     isEditing.value = false;
     ElMessage.success('修改已保存');
  } catch (e) {
     ElMessage.error('保存失败');
  }
};

const handleRequestAccess = () => {
  emit('request-access', props.feature!);
  ElMessage.success('已发送数据调取申请，请等待管理员审核');
};


const ncSliceLoading = ref(false);

const handleExportMarkdown = () => {
  try {
    const date = new Date().toLocaleString();
    let md = `# 地质数据报告\n\n`;
    md += `**生成日期**: ${date}\n\n`;

    if (props.isMultiSelection && props.selectedItems.length > 0) {
      // 批量导出逻辑
      md += `## 汇总统计\n`;
      md += `- **要素总数**: ${props.selectedItems.length}\n`;
      md += `- **数据类型**: ${Array.from(new Set(props.selectedItems.map(i => i.type))).join(', ')}\n\n`;
      
      md += `## 要素列表\n\n`;
      md += `| ID | 名称 | 类型 | 上传时间 | 坐标 |\n`;
      md += `| --- | --- | --- | --- | --- |\n`;
      
      props.selectedItems.forEach(f => {
        const coords = (typeof f.center_x === 'number' && typeof f.center_y === 'number') 
          ? `${f.center_x.toFixed(4)}, ${f.center_y.toFixed(4)}` 
          : '未知';
        md += `| ${f.id} | ${f.name || '未命名'} | ${f.type || '-'} | ${f.uploadTime || '-'} | ${coords} |\n`;
      });
      
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      downloadBlob(blob, `geodata_summary_${new Date().getTime()}.md`);
    } else if (props.feature) {
      // 单个导出逻辑
      const f = props.feature;
      md += `## 基本信息\n`;
      md += `- **名称**: ${f.name || '未命名'}\n`;
      md += `- **类型**: ${f.type || '未知'}\n`;
      md += `- **上传时间**: ${f.uploadTime || 'N/A'}\n`;
      md += `- **坐标**: ${formattedCoordinates.value}\n`;
      
      if (f.lithology) md += `- **岩性**: ${f.lithology}\n`;
      if (f.description) md += `\n## 描述\n${f.description}\n`;
      
      if (f.metadata) {
        md += `\n## 元数据\n`;
        if (f.metadata.dims) {
          md += `### 维度\n`;
          for (const [key, val] of Object.entries(f.metadata.dims)) {
            md += `- ${key}: ${val}\n`;
          }
        }
        if (f.metadata.variables) {
          md += `### 变量\n`;
          f.metadata.variables.forEach((v: any) => {
            md += `- ${v.name} (${v.units || '-'}): ${v.long_name || ''}\n`;
          });
        }
      }
      
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      downloadBlob(blob, `${f.name || 'report'}_${new Date().getTime()}.md`);
    } else {
      ElMessage.warning('没有可导出的数据');
      return;
    }
    
    ElMessage.success('报告导出成功');
  } catch (error: any) {
    console.error('Export failed:', error);
    ElMessage.error(`导出失败: ${error.message || '未知错误'}`);
  }
};

const handleVisualizeNetCDF = async (variable: string) => {
  if (!props.feature?.id) return;
  ncSliceLoading.value = true;
  try {
    // 默认取 time=0, depth=0
    const res = await geoDataApi.getNetCDFSlice(props.feature.id, variable);
    emit('visualize-nc', res);
    ElMessage.success(`已加载变量 ${variable} 数据切片`);
  } catch (e: any) {
    ElMessage.error(e?.message || '获取切片数据失败');
  } finally {
    ncSliceLoading.value = false;
  }
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

const handleDownloadClick = async () => {
  if (!props.feature?.id) return;
  try {
    const blob = await geoDataApi.downloadBatch([props.feature.id]);
    downloadBlob(blob, `${props.feature.name || '数据下载'}.zip`);
    emit('download', props.feature);
  } catch (e: any) {
    ElMessage.error(e?.message || '下载失败');
  }
};

const handleBatchDownloadClick = async () => {
  const ids = props.selectedItems.map(i => i.id);
  if (ids.length === 0) return;
  try {
    const blob = await geoDataApi.downloadBatch(ids);
    downloadBlob(blob, `geodata_batch_${ids.length}.zip`);
    emit('batch-download');
  } catch (e: any) {
    ElMessage.error(e?.message || '批量下载失败');
  }
};

const handlePreviewReport = (report: any) => {
  if (report.url) {
    window.open(report.url, '_blank');
    emit('preview-report', report);
  } else {
    ElMessage.warning('报告链接无效');
  }
};

const formattedCoordinates = computed(() => {
  if (props.feature && typeof props.feature.center_x === 'number' && typeof props.feature.center_y === 'number') {
    return `${props.feature.center_x.toFixed(4)}, ${props.feature.center_y.toFixed(4)}`;
  }
  return '坐标未知';
});
</script>

<style scoped>
.side-panel-wrapper {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 350px;
  z-index: 900; /* Below search (100 is search, wait. Search is 100? Map controls 90/100. */
  /* We want panel to be on top of map controls? Or below? */
  /* Side panel usually highest z-index except modal. */
  z-index: 1000;
  pointer-events: none;
  overflow: hidden;
}

.side-panel-wrapper.visible {
  pointer-events: auto;
}

.side-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-left: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: -8px 0 32px 0 rgba(31, 38, 135, 0.15);
  transform: translateX(100%);
  transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.side-panel-wrapper.visible .side-panel {
  transform: translateX(0);
}

.glass-morphism {
  /* Inherited or specific overrides */
}

/* Remove old positioning */
/* .side-panel { position: absolute ... } */

.panel-header {
  padding: 24px 20px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.role-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: auto;
  margin-left: 8px;
  font-weight: 500;
}

.badge-admin {
  background: #e8f2ff;
  color: #0071E3;
}

.badge-user {
  background: #e6f9ed;
  color: #34C759;
}

.request-btn {
  color: #0071E3;
}

/* ... existing styles ... */

.glass-morphism {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
}

.drag-handle-wrapper {
  width: 100%;
  height: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: grab;
}

.drag-handle {
  width: 36px;
  height: 5px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.panel-header {
  padding: 0 20px 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.4px;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 20px 20px;
}

/* NetCDF Styles */
.nc-section {
  margin-bottom: 24px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dim-tag {
  background: #f5f5f7;
  color: #1d1d1f;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.vars-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.var-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.var-item:hover {
  background: rgba(255, 255, 255, 0.8);
  transform: translateX(2px);
}

.var-icon {
  margin-right: 10px;
  color: #0071E3;
}

.var-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.var-name {
  font-size: 13px;
  font-weight: 500;
  color: #1d1d1f;
}

.var-desc {
  font-size: 11px;
  color: #86868b;
}

.var-unit {
  font-size: 11px;
  color: #86868b;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: 8px;
}

.action-icon {
  color: #c7c7cc;
}

.var-item:hover .action-icon {
  color: #0071E3;
}

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
}

/* Info Blocks */
.info-block-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.info-block-row {
  display: flex;
  gap: 12px;
}

.info-block {
  background: rgba(255, 255, 255, 0.5);
  padding: 12px;
  border-radius: 12px;
}

.info-block.half {
  flex: 1;
}

.info-block label {
  display: block;
  font-size: 12px;
  color: #86868b;
  margin-bottom: 4px;
}

.info-block .value {
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
  word-break: break-all;
}

.monospace {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 13px;
}

.tag {
  background: #e8f2ff;
  color: #0071E3;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.preview-card {
  width: 100%;
  height: 140px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  overflow: hidden;
}

.panel-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.secondary-actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.secondary-actions-grid .export-btn {
  grid-column: span 2;
}

.batch-actions {
  display: flex;
  gap: 12px;
}

.apple-btn {
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.primary-btn {
  background: #0071E3;
  color: white;
}

.primary-btn:hover {
  background: #0077ED;
}

.secondary-btn {
  background: rgba(0, 113, 227, 0.1);
  color: #0071E3;
}

.secondary-btn:hover {
  background: rgba(0, 113, 227, 0.15);
}

/* Multi-select List */
.selection-summary {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #86868b;
}

.list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.list-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.list-item:hover {
  background: rgba(255, 255, 255, 0.8);
  transform: scale(1.02);
}

.item-icon-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e8f2ff;
  color: #0071E3;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}

.item-meta {
  font-size: 12px;
  color: #86868b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.distance-tag {
  background: rgba(0, 113, 227, 0.1);
  color: #0071E3;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
}

.arrow-icon {
  color: #c7c7cc;
}

.reports-section {
  margin-top: 16px;
  margin-bottom: 16px;
}

.reports-section h4 {
  font-size: 14px;
  margin-bottom: 10px;
  color: #1d1d1f;
}

.report-item {
  display: flex;
  align-items: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  margin-bottom: 8px;
}

.report-icon {
  margin-right: 8px;
  color: #86868b;
}

.report-title {
  flex: 1;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
