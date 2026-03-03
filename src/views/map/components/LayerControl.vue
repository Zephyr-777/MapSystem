<template>
  <div v-if="visible" class="layer-control-panel card-shadow">
    <div class="panel-header">
      <h3>图层管理</h3>
      <el-button link :icon="Close" @click="$emit('close')" />
    </div>
    <div class="panel-content">
      <div v-for="(config, key) in layerConfig" :key="key" class="layer-item">
        <div class="layer-header">
          <el-checkbox 
            :model-value="config.visible"
            @update:model-value="(val: boolean) => $emit('update:visibility', { key: String(key), visible: val })"
          >
            {{ config.name }}
          </el-checkbox>
        </div>
        <div class="layer-opacity" v-if="config.visible">
          <span class="opacity-label">透明度</span>
          <el-slider 
            :model-value="config.opacity"
            :min="0"
            :max="100"
            size="small"
            @update:model-value="(val: number) => $emit('update:opacity', { key: String(key), opacity: val })"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue';
import type { LayerConfig } from '@/views/map/types/map';

defineProps<{
  visible: boolean;
  layerConfig: LayerConfig;
}>();

defineEmits<{
  (e: 'close'): void;
  (e: 'update:visibility', payload: { key: string, visible: boolean }): void;
  (e: 'update:opacity', payload: { key: string, opacity: number }): void;
}>();
</script>

<style scoped>
.layer-control-panel {
  position: absolute;
  bottom: 90px;
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
  z-index: 100;
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.panel-content {
  padding: 16px;
}

.layer-item {
  margin-bottom: 16px;
}

.layer-item:last-child {
  margin-bottom: 0;
}

.layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.layer-opacity {
  padding-left: 24px;
  padding-right: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.opacity-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}
</style>
