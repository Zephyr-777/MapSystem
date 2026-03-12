<template>
  <div class="smart-search">
    <el-input
      v-model="searchQuery"
      placeholder="用自然语言描述您要找的数据..."
      @keyup.enter="handleSearch"
      class="search-input"
      :prefix-icon="Search"
      clearable
    >
      <template #append>
        <el-button @click="handleSearch" :loading="loading">
           <el-icon><MagicStick /></el-icon> 智能搜索
        </el-button>
      </template>
    </el-input>
    
    <!-- 搜索建议/历史 (Optional) -->
    <div v-if="suggestions.length" class="search-suggestions">
      <el-tag
        v-for="sug in suggestions"
        :key="sug"
        size="small"
        class="suggestion-tag"
        @click="searchQuery = sug; handleSearch()"
      >
        {{ sug }}
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Search, MagicStick } from '@element-plus/icons-vue';
import { geoDataApi } from '@/api/geodata';
import { ElMessage } from 'element-plus';

const emit = defineEmits<{
  (e: 'search-result', results: any[]): void;
}>();

const searchQuery = ref('');
const loading = ref(false);
const suggestions = ref<string[]>([
  "查找最近一周上传的矢量数据",
  "显示北京附近的DEM数据",
  "查询包含'断层'描述的地质点"
]);

const handleSearch = async () => {
  if (!searchQuery.value.trim()) return;
  
  loading.value = true;
  try {
    const response = await geoDataApi.smartSearch(searchQuery.value);
    const results = Array.isArray(response) ? response : (response as any).data || [];
    
    if (results.length === 0) {
      ElMessage.info('未找到匹配的数据');
    } else {
      ElMessage.success(`智能检索到 ${results.length} 条数据`);
      emit('search-result', results);
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('智能搜索服务暂不可用');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.smart-search {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 20px 0 0 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.search-input :deep(.el-input-group__append) {
  border-radius: 0 20px 20px 0;
  background-color: #0071E3;
  color: white;
  border: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.search-input :deep(.el-input-group__append button) {
  color: white;
}

.search-suggestions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.suggestion-tag {
  cursor: pointer;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}

.suggestion-tag:hover {
  background: #0071E3;
  color: white;
  transform: translateY(-2px);
}
</style>
