<template>
  <div class="upload-panel glass-morphism">
    <div class="panel-header">
      <h3>数据上传</h3>
      <el-button link @click="$emit('close')"><el-icon><Close /></el-icon></el-button>
    </div>
    
    <div class="upload-area">
      <el-upload
        class="upload-dragger"
        drag
        action="#"
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
        multiple
        accept=".shp,.shx,.dbf,.prj,.geojson,.json,.kml,.kmz,.tif,.tiff,.nc"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 Shapefile (需包含 .shp, .shx, .dbf), GeoJSON, KML, GeoTIFF
          </div>
        </template>
      </el-upload>
    </div>

    <div class="upload-actions">
      <el-button type="primary" :loading="uploading" @click="submitUpload" :disabled="fileList.length === 0">
        {{ uploading ? '上传处理中...' : '开始上传' }}
      </el-button>
    </div>

    <!-- Progress / Result -->
    <div v-if="uploadResult" class="upload-result">
       <el-alert
        v-if="uploadResult.message"
        :title="uploadResult.message"
        type="success"
        show-icon
        :closable="false"
      />
      <div v-if="uploadResult.errors && uploadResult.errors.length" class="error-list">
        <p v-for="(err, idx) in uploadResult.errors" :key="idx" class="error-item">{{ err }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Close, UploadFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { geoDataApi } from '@/api/geodata';

const emit = defineEmits(['close', 'upload-success']);

const fileList = ref<any[]>([]);
const uploading = ref(false);
const uploadResult = ref<any>(null);

const handleFileChange = (files: any[]) => {
  fileList.value = files;
};

const handleFileRemove = (files: any[]) => {
  fileList.value = files;
};

const submitUpload = async () => {
  if (fileList.value.length === 0) return;
  
  uploading.value = true;
  uploadResult.value = null;
  
  const formData = new FormData();
  fileList.value.forEach(file => {
    formData.append('files', file.raw);
  });
  
  try {
    const res = await geoDataApi.upload(formData);
    uploadResult.value = res;
    ElMessage.success('上传成功');
    emit('upload-success');
    fileList.value = []; // Clear list on success
  } catch (e: any) {
    console.error(e);
    ElMessage.error(e.response?.data?.detail || '上传失败');
    uploadResult.value = { errors: [e.message] };
  } finally {
    uploading.value = false;
  }
};
</script>

<style scoped>
.upload-panel {
  position: absolute;
  bottom: 100px;
  right: 20px; /* Right side */
  width: 350px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 16px;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.upload-actions {
  margin-top: 16px;
  text-align: right;
}

.error-list {
  margin-top: 10px;
  font-size: 12px;
  color: #F56C6C;
}

.error-item {
  margin: 2px 0;
}
</style>
