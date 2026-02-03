<template>
  <div class="search-container">
    <div class="search-bar">
      <div class="search-logo">
        <span class="logo-text">GeoMap</span>
      </div>
      <div class="search-divider-vertical"></div>
      <input 
        v-model="internalQuery" 
        class="custom-search-input" 
        placeholder="搜索地点、地质数据..." 
        @input="onInput"
        @focus="onFocus"
      />
      <div class="search-icon-btn" @click="handleSearch">
        <el-icon :size="18" color="#606266"><Search /></el-icon>
      </div>
      <div class="search-divider-vertical"></div>
      <div class="upload-btn-icon" @click="$emit('upload')" title="上传数据">
        <el-icon :size="18" color="#409EFF"><UploadFilled /></el-icon>
      </div>
    </div>

    <!-- Search Results List -->
    <transition name="fade">
      <div v-if="showResults && results.length > 0" class="search-results">
        <div 
          v-for="item in results" 
          :key="item.id" 
          class="result-item" 
          @click="handleSelectResult(item)"
        >
          <div class="result-icon">
            <el-icon><Location /></el-icon>
          </div>
          <div class="result-info">
            <div class="result-name">{{ item.name }}</div>
            <div class="result-meta">{{ item.type }} · {{ item.uploadTime }}</div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Search, UploadFilled, Location } from '@element-plus/icons-vue';
import type { SearchResult } from '@/views/map/types/map';

const props = defineProps<{
  results: SearchResult[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  (e: 'search', query: string): void;
  (e: 'select-result', item: SearchResult): void;
  (e: 'upload'): void;
}>();

const internalQuery = ref('');
const showResults = ref(false);
let searchTimeout: any = null;

const onInput = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  
  if (!internalQuery.value) {
    showResults.value = false;
    return;
  }
  
  searchTimeout = setTimeout(() => {
    emit('search', internalQuery.value);
    showResults.value = true;
  }, 300);
};

const onFocus = () => {
  if (internalQuery.value && props.results.length > 0) {
    showResults.value = true;
  }
};

const handleSearch = () => {
  emit('search', internalQuery.value);
  showResults.value = true;
};

const handleSelectResult = (item: SearchResult) => {
  internalQuery.value = item.name;
  showResults.value = false;
  emit('select-result', item);
};

// Watch for external changes if needed, but simplified for now
</script>

<style scoped>
.search-container {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.search-bar {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 4px;
  padding: 0 12px;
  height: 48px;
  width: 360px;
  box-sizing: border-box;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.search-logo {
  display: flex;
  align-items: center;
  margin-right: 4px;
}

.logo-text {
  font-weight: 600;
  color: #409EFF;
  font-size: 16px;
  letter-spacing: 0.5px;
}

.search-divider-vertical {
  width: 1px;
  height: 20px;
  background-color: #e4e7ed;
  margin: 0 12px;
}

.custom-search-input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 14px;
  color: #606266;
  height: 100%;
  min-width: 0;
}

.custom-search-input::placeholder {
  color: #c0c4cc;
}

.search-icon-btn, .upload-btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
  color: #606266;
}

.search-icon-btn:hover, .upload-btn-icon:hover {
  background-color: #f5f7fa;
  color: #409EFF;
}

.search-results {
  width: 360px;
  background: #fff;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.result-item {
  display: flex;
  align-items: flex-start;
  padding: 10px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.result-item:hover {
  background-color: #f5f7fa;
}

.result-icon {
  margin-right: 12px;
  margin-top: 2px;
  color: #909399;
}

.result-info {
  flex: 1;
  min-width: 0;
}

.result-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-meta {
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
</style>
