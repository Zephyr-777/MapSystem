<template>
  <div class="role-switcher-container glass-morphism">
    <div class="switcher-header">
      <span class="switcher-label">角色切换</span>
    </div>
    <el-radio-group v-model="currentRole" size="small" @change="handleRoleChange">
      <el-radio-button label="admin">管理员</el-radio-button>
      <el-radio-button label="guest">普通用户</el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';

const authStore = useAuthStore();
const currentRole = ref(authStore.user?.role || 'guest');

// Watch for store changes to sync local state if changed elsewhere
watch(() => authStore.user?.role, (newRole) => {
  if (newRole) {
    currentRole.value = newRole;
  }
});

const handleRoleChange = (val: string) => {
  authStore.setRole(val);
  if (val === 'admin') {
    ElMessage.success('当前身份：管理员');
  } else {
    ElMessage.info('当前身份：用户');
  }
};
</script>

<style scoped>
.role-switcher-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 2000; /* High z-index to be above everything */
  padding: 12px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.glass-morphism {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.switcher-header {
  font-size: 12px;
  color: #86868b;
  font-weight: 600;
}

:deep(.el-radio-button__inner) {
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  background: transparent;
  border: none;
  box-shadow: none !important;
}

:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 8px 0 0 8px;
}

:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 8px 8px 0;
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: #0071e3;
  color: white;
  box-shadow: none;
}
</style>
