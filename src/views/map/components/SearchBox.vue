<template>
  <div class="search-container">
    <div class="search-bar glass-pill">
      <!-- Search Icon (Left) -->
      <div class="search-icon-wrapper">
        <el-icon class="search-icon"><Search /></el-icon>
      </div>
      
      <el-autocomplete
        v-model="internalQuery"
        class="custom-search-input"
        :fetch-suggestions="querySearchAsync"
        placeholder="搜索地点、地质数据..."
        :trigger-on-focus="false"
        :debounce="300"
        @select="handleSelectResult"
        highlight-first-item
        popper-class="search-autocomplete-popper"
      >
        <template #default="{ item }">
          <!-- Header Item -->
          <div v-if="item.type === 'header'" class="search-header">
            {{ item.name }}
          </div>
          
          <!-- Empty/Error Item -->
          <div v-else-if="item.type === 'empty'" class="search-empty">
            {{ item.name }}
          </div>

          <!-- Regular Item -->
          <div v-else class="autocomplete-item">
            <div class="item-icon">
              <el-icon v-if="item.type === 'asset'"><Document /></el-icon>
              <el-icon v-else><Location /></el-icon>
            </div>
            <div class="item-content">
              <div class="item-title" v-html="highlightText(item.name)"></div>
              <div class="item-meta">
                <span v-if="item.distance" class="distance-tag">{{ formatDistance(item.distance) }} · </span>
                {{ item.address || (item.type === 'asset' ? '地质数据' : '地理位置') }}
              </div>
            </div>
          </div>
        </template>
        <template #suffix>
          <div v-if="internalQuery" class="clear-icon-wrapper" @click.stop="clearSearch">
            <el-icon class="clear-icon"><CircleCloseFilled /></el-icon>
          </div>
        </template>
      </el-autocomplete>

      <div class="search-divider-vertical"></div>
      
      <div class="action-btn" @click="$emit('upload')" title="上传数据">
        <el-icon :size="18"><UploadFilled /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Search, UploadFilled, Location, Document, CircleCloseFilled } from '@element-plus/icons-vue';
import type { SearchResult } from '@/views/map/types/map';

const props = defineProps<{
  fetchSuggestions: (queryString: string, cb: (results: any[]) => void) => void;
}>();

const emit = defineEmits<{
  (e: 'select-result', item: SearchResult): void;
  (e: 'upload'): void;
}>();

const internalQuery = ref('');

const querySearchAsync = (queryString: string, cb: (results: any[]) => void) => {
  props.fetchSuggestions(queryString, cb);
};

const handleSelectResult = (item: SearchResult) => {
  internalQuery.value = item.name;
  emit('select-result', item);
};

const clearSearch = () => {
  internalQuery.value = '';
};

const highlightText = (text: string) => {
  if (!internalQuery.value) return text;
  const reg = new RegExp(`(${internalQuery.value})`, 'gi');
  return text.replace(reg, '<span class="highlight">$1</span>');
};

const formatDistance = (dist: number) => {
  if (dist < 1000) {
    return `${Math.round(dist)}m`;
  }
  return `${(dist / 1000).toFixed(1)}km`;
};
</script>

<style scoped>
.search-container {
  position: absolute;
  top: 30px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  width: 480px;
  max-width: 90%;
}

.glass-pill {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
  border-radius: 24px;
  padding: 4px 6px;
  height: 48px;
  transition: all 0.3s ease;
}

.glass-pill:hover, .glass-pill:focus-within {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
  transform: translateY(-2px);
}

.search-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 100%;
  color: #86868b;
}

.custom-search-input {
  flex: 1;
}

:deep(.el-input__wrapper) {
  background: transparent !important;
  box-shadow: none !important;
  padding: 0;
}

:deep(.el-input__inner) {
  height: 40px;
  font-size: 16px;
  color: #1d1d1f;
}

.clear-icon-wrapper {
  cursor: pointer;
  display: flex;
  align-items: center;
  color: #86868b;
  transition: color 0.2s;
}

.clear-icon-wrapper:hover {
  color: #1d1d1f;
}

.search-divider-vertical {
  width: 1px;
  height: 24px;
  background-color: rgba(0, 0, 0, 0.1);
  margin: 0 8px;
}

.action-btn {
  width: 40px;
  height: 40px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #0071E3;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(0, 113, 227, 0.1);
}

.autocomplete-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.item-icon {
  margin-right: 12px;
  color: #86868b;
}

.item-content {
  flex: 1;
  overflow: hidden;
}

.item-title {
  font-size: 14px;
  color: #1d1d1f;
  margin-bottom: 2px;
}

.item-meta {
  font-size: 12px;
  color: #86868b;
}

.distance-tag {
  color: #0071E3;
  font-weight: 500;
}

:deep(.highlight) {
  color: #0071E3;
  font-weight: 500;
}

.search-header {
  padding: 8px 4px 4px;
  font-size: 12px;
  color: #86868b;
  font-weight: 600;
  pointer-events: none;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  margin-bottom: 4px;
}

.search-empty {
  padding: 12px;
  text-align: center;
  color: #86868b;
  font-size: 14px;
  pointer-events: none;
}
</style>

<style>
.search-autocomplete-popper.el-popper {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.15) !important;
  border-radius: 16px !important;
}

.search-autocomplete-popper .el-autocomplete-suggestion__wrap {
  padding: 8px !important;
}

.search-autocomplete-popper li {
  padding: 0 12px !important;
  border-radius: 8px;
  margin-bottom: 2px;
}

.search-autocomplete-popper li:hover {
  background: rgba(0, 0, 0, 0.05) !important;
}
</style>

<style>
/* Global styles for popper */
.search-autocomplete-popper .autocomplete-item {
  display: flex;
  align-items: center;
  padding: 8px 4px;
}

.search-autocomplete-popper .item-icon {
  margin-right: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.search-autocomplete-popper .item-content {
  flex: 1;
  overflow: hidden;
}

.search-autocomplete-popper .item-title {
  font-size: 14px;
  color: #303133;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-autocomplete-popper .item-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.search-autocomplete-popper .highlight {
  color: #409EFF;
  font-weight: bold;
}
</style>
