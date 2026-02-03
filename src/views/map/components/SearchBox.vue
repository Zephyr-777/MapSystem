<template>
  <div class="search-container">
    <div class="search-bar card-shadow">
      <div class="search-logo">
        <span class="logo-text">GeoMap</span>
      </div>
      <div class="search-divider-vertical"></div>
      
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
          <div class="autocomplete-item">
            <div class="item-icon">
              <el-icon v-if="item.type === 'asset'"><Document /></el-icon>
              <el-icon v-else><Location /></el-icon>
            </div>
            <div class="item-content">
              <div class="item-title" v-html="highlightText(item.name)"></div>
              <div class="item-meta">{{ item.address || (item.type === 'asset' ? '地质数据' : '地理位置') }}</div>
            </div>
          </div>
        </template>
        <template #suffix>
          <el-icon v-if="internalQuery" class="clear-icon" @click.stop="clearSearch"><CircleClose /></el-icon>
          <el-icon v-else class="search-icon"><Search /></el-icon>
        </template>
      </el-autocomplete>

      <div class="search-divider-vertical"></div>
      <div class="upload-btn-icon" @click="$emit('upload')" title="上传数据">
        <el-icon :size="18" color="#409EFF"><UploadFilled /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Search, UploadFilled, Location, Document, CircleClose } from '@element-plus/icons-vue';
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
</script>

<style scoped>
.search-container {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 100;
  width: 380px;
}

.search-bar {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 8px;
  padding: 0 12px;
  height: 48px;
  transition: all 0.3s;
}

.card-shadow {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.search-logo {
  display: flex;
  align-items: center;
  margin-right: 12px;
}

.logo-text {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.search-divider-vertical {
  width: 1px;
  height: 24px;
  background-color: #dcdfe6;
  margin: 0 8px;
}

.custom-search-input {
  flex: 1;
  :deep(.el-input__wrapper) {
    box-shadow: none !important;
    padding: 0;
    background: transparent;
  }
  :deep(.el-input__inner) {
    border: none;
    height: 48px;
    font-size: 14px;
  }
}

.upload-btn-icon {
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-btn-icon:hover {
  background: #f5f7fa;
}

.clear-icon {
  cursor: pointer;
  color: #909399;
}

.clear-icon:hover {
  color: #606266;
}

.search-icon {
  color: #909399;
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
