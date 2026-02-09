<template>
  <div v-if="visible" class="side-panel glass-morphism">
    <div class="drag-handle-wrapper">
      <div class="drag-handle"></div>
    </div>
    
    <div class="panel-header">
      <h3 class="panel-title">{{ title }}</h3>
      <div class="close-btn" @click="$emit('close')">
        <el-icon><Close /></el-icon>
      </div>
    </div>
    
    <div class="panel-content custom-scrollbar">
      <!-- Single Feature Mode -->
      <div v-if="feature && !isMultiSelection" class="feature-detail">
        <div class="preview-card" v-if="feature.type && feature.type.includes('TIF')">
          <div class="image-placeholder">
            <el-icon :size="32" color="#86868b"><Picture /></el-icon>
          </div>
        </div>
        
        <div class="info-block-group">
          <div class="info-block">
            <label>名称</label>
            <div class="value">{{ feature.name }}</div>
          </div>
          
          <div class="info-block-row">
            <div class="info-block half">
              <label>类型</label>
              <div class="value"><span class="tag">{{ feature.type }}</span></div>
            </div>
            <div class="info-block half">
               <label>上传时间</label>
               <div class="value">{{ feature.uploadTime ? feature.uploadTime.split('T')[0] : 'N/A' }}</div>
            </div>
          </div>
          
          <div class="info-block" v-if="feature.lithology">
            <label>岩性</label>
            <div class="value">{{ feature.lithology }}</div>
          </div>
          
          <div class="info-block" v-if="feature.description">
            <label>描述</label>
            <div class="value">{{ feature.description }}</div>
          </div>
          
          <div class="info-block">
            <label>坐标</label>
            <div class="value monospace">{{ coordinates }}</div>
          </div>
        </div>

        <div class="reports-section" v-if="feature.reports && feature.reports.length">
          <h4>关联报告</h4>
          <div v-for="(report, index) in feature.reports" :key="index" class="report-item">
            <div class="report-icon"><el-icon><Document /></el-icon></div>
            <span class="report-title">{{ report.title }}</span>
            <el-button link type="primary" size="small" @click="$emit('preview-report', report)">预览</el-button>
          </div>
        </div>

        <div class="panel-actions">
          <button class="apple-btn primary-btn" @click="handleDownloadClick">
            <el-icon><Download /></el-icon> 下载数据
          </button>
          <button class="apple-btn secondary-btn" @click="$emit('preview', feature)">
            <el-icon><ViewIcon /></el-icon> 定位预览
          </button>
        </div>
      </div>

      <!-- Multi Selection Mode -->
      <div v-else-if="isMultiSelection" class="multi-selection-list">
        <div class="selection-summary">
          <span>已选 {{ selectedItems.length }} 个要素</span>
          <el-button type="primary" link size="small" @click="handleBatchDownloadClick">批量下载</el-button>
        </div>
        <div class="list-container custom-scrollbar">
          <div v-for="item in selectedItems" :key="item.id" class="list-item" @click="$emit('locate-item', item)">
            <div class="item-icon-circle">
              <el-icon><Location /></el-icon>
            </div>
            <div class="item-info">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-meta">{{ item.type }}</div>
            </div>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Close, Picture, Download, View as ViewIcon, Location, Document, ArrowRight } from '@element-plus/icons-vue';
import type { GeoDataItem } from '@/views/map/types/map';
import { geoDataApi } from '@/api/geodata';
import { ElMessage } from 'element-plus';

const props = defineProps<{
  visible: boolean;
  title: string;
  feature?: GeoDataItem | null;
  isMultiSelection: boolean;
  selectedItems: GeoDataItem[];
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'download', item: GeoDataItem): void;
  (e: 'preview', item: GeoDataItem): void;
  (e: 'batch-download'): void;
  (e: 'locate-item', item: GeoDataItem): void;
  (e: 'preview-report', report: any): void;
}>();

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
  if (!props.feature) return;
  try {
    const blob = await geoDataApi.downloadBatch([props.feature.id]);
    downloadBlob(blob, `${props.feature.name || 'geodata'}.zip`);
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

const coordinates = computed(() => {
  if (props.feature && props.feature.center_x !== undefined && props.feature.center_y !== undefined) {
    return `${props.feature.center_x.toFixed(2)}, ${props.feature.center_y.toFixed(2)}`;
  }
  return 'N/A';
});
</script>

<style scoped>
.side-panel {
  position: absolute;
  top: 100px;
  left: 20px;
  bottom: 40px;
  width: 320px;
  z-index: 99;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
}

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
  gap: 10px;
  margin-top: 10px;
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
