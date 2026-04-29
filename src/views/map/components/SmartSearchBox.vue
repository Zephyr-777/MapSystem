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
        <div class="append-actions">
          <el-button @click="handleSearch" :loading="loading" class="search-btn">
            <el-icon><MagicStick /></el-icon> 智能搜索
          </el-button>
          <el-button class="settings-btn" @click="settingsVisible = true" title="搜索设置">
            <el-icon><Setting /></el-icon>
          </el-button>
        </div>
      </template>
    </el-input>
    
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

    <el-dialog v-model="settingsVisible" title="智能搜索设置" width="520px">
      <el-form :model="searchConfig" label-width="110px">
        <el-form-item label="启用智能模式">
          <el-switch v-model="searchConfig.enabled" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="searchConfig.model" placeholder="glm-4.5-air" />
        </el-form-item>
        <el-form-item label="Provider">
          <el-input v-model="searchConfig.provider" placeholder="zhipu" />
        </el-form-item>
        <el-form-item label="API Base URL">
          <el-input v-model="searchConfig.base_url" placeholder="https://open.bigmodel.cn/api/paas/v4" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="searchConfig.api_key" type="password" show-password placeholder="输入你的模型 API Key" />
        </el-form-item>
      </el-form>
      <div class="settings-tip">
        配置仅保存在当前浏览器。本地留空 API Key 时，系统会优先尝试使用后端默认模型配置。
      </div>
      <template #footer>
        <el-button @click="resetConfig">恢复默认</el-button>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存设置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { Search, MagicStick, Setting } from '@element-plus/icons-vue';
import { geoDataApi, type SmartSearchConfig } from '@/api/geodata';
import { ElMessage } from 'element-plus';

const STORAGE_KEY = 'geomap-smart-search-config';
const DEFAULT_CONFIG: Required<SmartSearchConfig> = {
  provider: 'zhipu',
  model: 'glm-4.5-air',
  api_key: '',
  base_url: 'https://open.bigmodel.cn/api/paas/v4',
  enabled: true,
};

const emit = defineEmits<{
  (e: 'search-result', results: any[]): void;
}>();

const searchQuery = ref('');
const loading = ref(false);
const settingsVisible = ref(false);
const suggestions = ref<string[]>([
  '查找最近一周上传的矢量数据',
  '查询最近一月的 GeoTIFF 栅格数据',
  "查询包含'断层'描述的数据",
  '显示前10条最新的 DEM 地形数据',
]);

const searchConfig = reactive<Required<SmartSearchConfig>>(loadSavedConfig());

function loadSavedConfig(): Required<SmartSearchConfig> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_CONFIG };
    return { ...DEFAULT_CONFIG, ...(JSON.parse(raw) as Partial<SmartSearchConfig>) };
  } catch (_error) {
    return { ...DEFAULT_CONFIG };
  }
}

function saveConfig() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(searchConfig));
  settingsVisible.value = false;
  ElMessage.success('智能搜索设置已保存');
}

function resetConfig() {
  Object.assign(searchConfig, DEFAULT_CONFIG);
}

function getReasonMessage(reason?: string) {
  const reasonMap: Record<string, string> = {
    ai_disabled: '智能模式已关闭，当前使用关键词检索',
    missing_api_key: '未配置 API Key，已自动使用关键词检索',
    ai_unavailable: '模型暂不可用，已自动降级到关键词检索',
    ai_invalid_json: '模型解析异常，已自动降级到关键词检索',
    unsupported_provider: '当前 Provider 不受支持，已自动使用关键词检索',
    fallback_search: '已自动切换到关键词检索',
  };
  return reason ? reasonMap[reason] || '已自动切换到关键词检索' : '已自动切换到关键词检索';
}

async function handleSearch() {
  const query = searchQuery.value.trim();
  if (!query) {
    ElMessage.warning('请输入搜索内容');
    return;
  }
  
  loading.value = true;
  try {
    const response = await geoDataApi.smartSearch(query, { ...searchConfig });
    const results = Array.isArray(response?.data) ? response.data : [];
    
    if (results.length === 0) {
      ElMessage.info(response.mode === 'fallback' ? `${getReasonMessage(response.reason)}，但未找到匹配数据` : '未找到匹配的数据');
      emit('search-result', []);
      return;
    }

    if (response.mode === 'ai') {
      ElMessage.success(`智能检索到 ${results.length} 条数据`);
    } else {
      ElMessage.warning(`${getReasonMessage(response.reason)}，找到 ${results.length} 条数据`);
    }

    emit('search-result', results);
  } catch (error) {
    console.error(error);
    ElMessage.error('智能搜索服务暂不可用');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.smart-search {
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
}

.append-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 20px 0 0 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.search-input :deep(.el-input-group__append) {
  border-radius: 0 20px 20px 0;
  background: linear-gradient(135deg, #0b73e0 0%, #2490ff 100%);
  border: none;
  box-shadow: 0 8px 24px rgba(11, 115, 224, 0.15);
}

.search-btn,
.settings-btn {
  border: none;
  background: transparent;
  color: white;
}

.search-btn:hover,
.settings-btn:hover {
  color: white;
  background: rgba(255, 255, 255, 0.14);
}

.settings-btn {
  padding-inline: 10px;
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
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}

.suggestion-tag:hover {
  background: #0071e3;
  color: white;
  transform: translateY(-2px);
}

.settings-tip {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}
</style>
