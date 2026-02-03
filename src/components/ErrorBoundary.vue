<template>
  <div v-if="error" class="error-boundary">
    <el-result
      icon="error"
      title="组件渲染出错"
      :sub-title="error.message || '系统发生未知错误，请尝试刷新页面'"
    >
      <template #extra>
        <el-button type="primary" @click="handleRetry">重试</el-button>
        <el-button @click="handleRefresh">刷新页面</el-button>
      </template>
    </el-result>
  </div>
  <slot v-else></slot>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue';

const error = ref<Error | null>(null);

onErrorCaptured((err) => {
  console.error('Captured error in boundary:', err);
  error.value = err as Error;
  return false;
});

const handleRetry = () => {
  error.value = null;
};

const handleRefresh = () => {
  window.location.reload();
};
</script>

<style scoped>
.error-boundary {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
  background: #fff;
  z-index: 1000;
  position: absolute;
  top: 0;
  left: 0;
}
</style>
