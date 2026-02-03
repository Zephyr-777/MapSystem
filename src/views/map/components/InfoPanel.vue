<template>
  <transition name="slide-fade">
    <div v-if="visible" class="side-panel">
      <div class="panel-header">
        <h3>{{ title }}</h3>
        <el-button link :icon="Close" @click="$emit('close')" />
      </div>
      
      <div class="panel-content">
        <!-- Single Feature Mode -->
        <div v-if="feature && !isMultiSelection" class="feature-detail">
          <div class="preview-image" v-if="feature.type && feature.type.includes('TIF')">
            <div class="image-placeholder">
              <el-icon :size="40"><Picture /></el-icon>
            </div>
          </div>
          
          <el-descriptions :column="1" border size="small" class="detail-desc">
            <el-descriptions-item label="名称">{{ feature.name }}</el-descriptions-item>
            <el-descriptions-item label="类型">
              <el-tag size="small">{{ feature.type }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="上传时间" v-if="feature.uploadTime">{{ feature.uploadTime }}</el-descriptions-item>
            <el-descriptions-item label="岩性" v-if="feature.lithology">{{ feature.lithology }}</el-descriptions-item>
            <el-descriptions-item label="描述" v-if="feature.description">{{ feature.description }}</el-descriptions-item>
            <el-descriptions-item label="坐标">
              {{ coordinates }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="reports-section" v-if="feature.reports && feature.reports.length">
            <h4>关联报告</h4>
            <div v-for="(report, index) in feature.reports" :key="index" class="report-item">
              <span>{{ report.title }}</span>
              <el-button link type="primary" size="small" @click="$emit('preview-report', report)">预览</el-button>
            </div>
          </div>

          <div class="panel-actions">
            <el-button type="primary" block @click="$emit('download', feature)">
              <el-icon><Download /></el-icon> 下载数据
            </el-button>
            <el-button type="success" plain block @click="$emit('preview', feature)">
              <el-icon><ViewIcon /></el-icon> 定位预览
            </el-button>
          </div>
        </div>

        <!-- Multi Selection Mode -->
        <div v-else-if="isMultiSelection" class="multi-selection-list">
          <div class="selection-summary">
            <span>已选 {{ selectedItems.length }} 个要素</span>
            <el-button type="primary" link size="small" @click="$emit('batch-download')">批量下载</el-button>
          </div>
          <el-scrollbar height="400px">
            <div v-for="item in selectedItems" :key="item.id" class="list-item" @click="$emit('locate-item', item)">
              <div class="item-icon">
                <el-icon><Location /></el-icon>
              </div>
              <div class="item-info">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-meta">{{ item.type }}</div>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Close, Picture, Download, View as ViewIcon, Location } from '@element-plus/icons-vue';
import type { GeoDataItem } from '@/views/map/types/map';

const props = defineProps<{
  visible: boolean;
  title: string;
  feature?: GeoDataItem;
  isMultiSelection: boolean;
  selectedItems: GeoDataItem[];
}>();

defineEmits<{
  (e: 'close'): void;
  (e: 'download', item: GeoDataItem): void;
  (e: 'preview', item: GeoDataItem): void;
  (e: 'batch-download'): void;
  (e: 'locate-item', item: GeoDataItem): void;
  (e: 'preview-report', report: any): void;
}>();

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
  top: 80px;
  left: 20px;
  bottom: 40px;
  width: 360px;
  background: #fff;
  z-index: 99;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.panel-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease-out;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(-20px);
  opacity: 0;
}

.feature-detail .preview-image {
  width: 100%;
  height: 150px;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  border-radius: 4px;
  color: #909399;
}

.panel-actions {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
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

.list-item {
  display: flex;
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.list-item:hover {
  background: #f5f7fa;
}

.item-icon {
  margin-right: 12px;
  color: #409eff;
  display: flex;
  align-items: center;
  font-size: 18px;
}

.item-info .item-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.item-info .item-meta {
  font-size: 12px;
  color: #909399;
}

.selection-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
  margin-bottom: 10px;
}
</style>
