<template>
  <el-dialog
    v-model="visible"
    title="上传地质数据"
    width="600px"
    :close-on-click-modal="false"
    class="upload-dialog glass-panel"
    @closed="handleClosed"
  >
    <div 
      class="upload-area breathing-effect"
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
      <div class="upload-icon-wrapper">
        <el-icon :size="64" class="upload-icon"><UploadFilled /></el-icon>
      </div>
      <div class="upload-text">
        <h3 class="primary-text">拖拽文件到这里</h3>
        <p class="secondary-text">支持 SHP (含同名文件), ZIP, TIF, CSV</p>
        <el-button type="primary" round size="small" class="select-btn">或者选择文件</el-button>
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
  border: 3px dashed rgba(64, 158, 255, 0.3);
  border-radius: 20px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 250px;
}

.upload-area:hover, .upload-area.is-dragover {
  border-color: #409eff;
  background: rgba(255, 255, 255, 0.6);
  transform: scale(1.02);
  box-shadow: 0 12px 32px rgba(64, 158, 255, 0.15);
}

.breathing-effect {
  animation: breathe 4s infinite ease-in-out;
}

@keyframes breathe {
  0% { box-shadow: 0 4px 12px rgba(64, 158, 255, 0.05); border-color: rgba(64, 158, 255, 0.3); }
  50% { box-shadow: 0 8px 24px rgba(64, 158, 255, 0.15); border-color: rgba(64, 158, 255, 0.6); }
  100% { box-shadow: 0 4px 12px rgba(64, 158, 255, 0.05); border-color: rgba(64, 158, 255, 0.3); }
}

.upload-icon-wrapper {
  margin-bottom: 20px;
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  width: 100px;
  height: 100px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.upload-area:hover .upload-icon-wrapper {
  background: #409eff;
  color: white;
  transform: translateY(-5px);
}

.primary-text {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px;
}

.secondary-text {
  font-size: 14px;
  color: #86868b;
  margin: 0 0 20px;
}

.select-btn {
  margin-top: 10px;
  padding: 8px 24px;
}

.file-list {
  margin-top: 24px;
  max-height: 180px;
  overflow-y: auto;
  padding-right: 4px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.6);
  margin-bottom: 10px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.file-item:hover {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.file-item .el-icon {
  margin-right: 12px;
  color: #409eff;
  font-size: 18px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: #86868b;
  margin: 0 16px;
}

.progress-area {
  margin-top: 24px;
}

.status-text {
  font-size: 13px;
  color: #86868b;
  margin-top: 8px;
  text-align: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 10px;
}

/* Glassmorphism for dialog */
:deep(.upload-dialog) {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

:deep(.el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

:deep(.el-dialog__title) {
  font-weight: 600;
  font-size: 18px;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 20px 24px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}
</style>
