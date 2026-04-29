<template>
  <el-dialog 
    v-model="isVisible" 
    title="分享当前视角" 
    width="400px"
  >
    <div class="share-content">
      <div class="qr-code-container" v-if="qrCodeUrl">
        <img :src="qrCodeUrl" alt="QR Code" class="qr-image" />
        <p class="qr-tip">扫码查看</p>
      </div>
      
      <div class="link-section">
        <el-input v-model="shareUrl" readonly>
          <template #append>
            <el-button @click="copyLink">复制</el-button>
          </template>
        </el-input>
      </div>
      
      <div class="validity-section">
        <span>有效期：</span>
        <el-radio-group v-model="validity" size="small">
          <el-radio label="24h">24小时</el-radio>
          <el-radio label="7d">7天</el-radio>
          <el-radio label="forever">永久</el-radio>
        </el-radio-group>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import QRCode from 'qrcode';
import { ElMessage } from 'element-plus';

const props = defineProps<{
  visible: boolean;
  mapState: any; // Center, zoom, layers
}>();

const emit = defineEmits(['update:visible']);

const shareUrl = ref('');
const qrCodeUrl = ref('');
const validity = ref('24h');

const isVisible = computed({
  get: () => props.visible,
  set: (val: boolean) => emit('update:visible', val)
});

const generateLink = async () => {
  // Construct URL with query params
  // Base URL
  const baseUrl = window.location.origin + window.location.pathname;
  
  // Params
  const params = new URLSearchParams();
  if (props.mapState) {
      if (props.mapState.center) {
          params.append('lon', props.mapState.center[0].toFixed(6));
          params.append('lat', props.mapState.center[1].toFixed(6));
      }
      if (props.mapState.zoom) {
          params.append('z', props.mapState.zoom.toFixed(2));
      }
      // Add more params like layers if needed
  }
  
  shareUrl.value = `${baseUrl}?${params.toString()}`;
  
  try {
    qrCodeUrl.value = await QRCode.toDataURL(shareUrl.value, { width: 200, margin: 2 });
  } catch (err) {
    console.error(err);
  }
};

watch(() => props.visible, (val) => {
  if (val) {
    generateLink();
  }
});

const copyLink = () => {
  navigator.clipboard.writeText(shareUrl.value).then(() => {
    ElMessage.success('链接已复制到剪贴板');
  });
};
</script>

<style scoped>
.share-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.qr-image {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 8px;
}

.qr-tip {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.link-section {
  width: 100%;
}

.validity-section {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #606266;
}
</style>
