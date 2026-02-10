<template>
  <el-dialog
    v-model="visible"
    title="上传地质数据"
    width="500px"
    :close-on-click-modal="false"
    class="upload-dialog glass-panel"
    @closed="handleClosed"
  >
    <div 
      class="upload-area"
      :class="{ 'is-dragover': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input 
        type="file" 
        ref="fileInputRef" 
        multiple 
        style="display: none" 
        @change="handleFileChange"
      >
      <div class="upload-icon">
        <el-icon :size="48"><UploadFilled /></el-icon>
      </div>
      <div class="upload-text">
        <p class="primary-text">点击或拖拽文件到此处上传</p>
        <p class="secondary-text">支持 SHP (及同名文件), ZIP, TIF, CSV 等格式</p>
      </div>
    </div>

    <!-- File List -->
    <div v-if="files.length > 0" class="file-list">
      <div v-for="(file, index) in files" :key="index" class="file-item">
        <el-icon><Document /></el-icon>
        <span class="file-name">{{ file.name }}</span>
        <span class="file-size">{{ formatSize(file.size) }}</span>
        <el-button link type="danger" @click.stop="removeFile(index)" :disabled="uploading">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Progress -->
    <div v-if="uploading" class="progress-area">
      <el-progress :percentage="progress" :status="progressStatus" />
      <p class="status-text">{{ statusText }}</p>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false" :disabled="uploading">取消</el-button>
        <el-button type="primary" @click="startUpload" :loading="uploading" :disabled="files.length === 0">
          开始上传
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { UploadFilled, Document, Close } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { geoDataApi } from '@/api/geodata';

const props = defineProps<{
  modelValue: boolean
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'upload-success', data: any): void
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const isDragOver = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const files = ref<File[]>([]);
const uploading = ref(false);
const progress = ref(0);
const statusText = ref('');

const progressStatus = computed(() => {
  if (progress.value === 100) return 'success';
  if (statusText.value.includes('失败')) return 'exception';
  return '';
});

const triggerFileInput = () => {
  if (uploading.value) return;
  fileInputRef.value?.click();
};

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files) {
    addFiles(Array.from(target.files));
  }
  target.value = ''; // Reset
};

const handleDrop = (e: DragEvent) => {
  isDragOver.value = false;
  if (uploading.value) return;
  if (e.dataTransfer?.files) {
    addFiles(Array.from(e.dataTransfer.files));
  }
};

const addFiles = (newFiles: File[]) => {
  files.value = [...files.value, ...newFiles];
};

const removeFile = (index: number) => {
  files.value.splice(index, 1);
};

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const startUpload = async () => {
  if (files.value.length === 0) return;
  
  uploading.value = true;
  progress.value = 0;
  statusText.value = '正在上传...';

  // Fake progress simulation since axios upload progress is fast but processing takes time
  const progressInterval = setInterval(() => {
    if (progress.value < 90) {
      progress.value += 5;
    }
  }, 200);

  try {
    const res = await geoDataApi.upload(files.value);
    
    clearInterval(progressInterval);
    progress.value = 100;
    statusText.value = '上传成功，正在解析...';
    
    // Check results
    // Access 'data' directly because api wrapper returns response.data
    // Or if the wrapper returns response, we need to check
    // In src/api/geodata.ts: return response (which is the axios response object)
    // Wait, let's check src/api/geodata.ts again.
    // It returns response. 
    // Usually axios response has .data. 
    // And in geodata.ts: return response
    
    const data = (res as any).data || res; 
    
    if (data.errors && data.errors.length > 0) {
       ElMessage.warning(`部分文件处理失败: ${data.errors.join('; ')}`);
    } else {
       ElMessage.success('文件全部上传成功');
    }
    
    // Find the first valid asset to fly to
    if (data.processed && data.processed.length > 0) {
       // Look for one with valid ID
       const firstAsset = data.processed.find((p: any) => p.id);
       if (firstAsset) {
          emit('upload-success', firstAsset);
       }
    }
    
    setTimeout(() => {
      visible.value = false;
    }, 1000);
    
  } catch (e: any) {
    clearInterval(progressInterval);
    progress.value = 0; // Reset or show error status
    statusText.value = '上传失败';
    ElMessage.error(e.message || '上传失败');
    console.error(e);
  } finally {
    uploading.value = false;
  }
};

const handleClosed = () => {
  files.value = [];
  progress.value = 0;
  statusText.value = '';
};
</script>

<style scoped>
.upload-area {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: rgba(245, 247, 250, 0.5);
}

.upload-area:hover, .upload-area.is-dragover {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.upload-icon {
  color: #909399;
  margin-bottom: 16px;
}

.primary-text {
  font-size: 16px;
  color: #303133;
  margin: 0 0 8px;
}

.secondary-text {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.file-list {
  margin-top: 20px;
  max-height: 150px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 8px;
  border-radius: 6px;
  background: #f5f7fa;
  margin-bottom: 8px;
}

.file-item .el-icon {
  margin-right: 8px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: #909399;
  margin: 0 12px;
}

.progress-area {
  margin-top: 20px;
}

.status-text {
  font-size: 12px;
  color: #606266;
  margin-top: 4px;
  text-align: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Glassmorphism for dialog */
:deep(.upload-dialog) {
  border-radius: 16px;
}
</style>
