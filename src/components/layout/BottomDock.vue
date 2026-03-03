<template>
  <div class="bottom-dock-container">
    <div class="bottom-dock">
      <div class="dock-group">
        <el-tooltip content="回到初始视角" placement="top" :show-after="500">
          <button class="dock-item" @click="$emit('home')">
            <el-icon><HomeFilled /></el-icon>
          </button>
        </el-tooltip>

        <el-tooltip content="图层管理" placement="top" :show-after="500">
          <button 
            class="dock-item" 
            :class="{ active: activeTool === 'layers' }"
            @click="$emit('toggle-layers')"
          >
            <el-icon><Files /></el-icon>
            <span class="indicator" v-if="activeTool === 'layers'"></span>
          </button>
        </el-tooltip>

        <el-tooltip content="距离/面积测量" placement="top" :show-after="500">
          <button 
            class="dock-item"
            :class="{ active: activeTool === 'measure' }"
            @click="$emit('toggle-measure')"
          >
            <el-icon><Ruler /></el-icon>
            <span class="indicator" v-if="activeTool === 'measure'"></span>
          </button>
        </el-tooltip>
      </div>

      <div class="dock-divider"></div>

      <div class="dock-group">
        <el-tooltip content="框选工具" placement="top" :show-after="500">
          <button 
            class="dock-item"
            :class="{ active: activeTool === 'selection' }"
            @click="$emit('toggle-selection')"
          >
            <el-icon><Crop /></el-icon>
            <span class="indicator" v-if="activeTool === 'selection'"></span>
          </button>
        </el-tooltip>

        <el-tooltip content="缓冲区分析" placement="top" :show-after="500">
          <button 
            class="dock-item"
            :class="{ active: activeTool === 'buffer' }"
            @click="$emit('toggle-buffer')"
          >
            <el-icon><Aim /></el-icon>
            <span class="indicator" v-if="activeTool === 'buffer'"></span>
          </button>
        </el-tooltip>

        <el-tooltip content="属性识别" placement="top" :show-after="500">
          <button 
            class="dock-item"
            :class="{ active: activeTool === 'identify' }"
            @click="$emit('toggle-identify')"
          >
            <el-icon><InfoFilled /></el-icon>
            <span class="indicator" v-if="activeTool === 'identify'"></span>
          </button>
        </el-tooltip>
      </div>

      <div class="dock-divider"></div>

      <div class="dock-group">
        <el-tooltip content="共享大厅" placement="top" :show-after="500">
          <button class="dock-item" @click="$emit('open-gallery')">
            <el-icon><Grid /></el-icon>
          </button>
        </el-tooltip>

        <el-tooltip content="分享当前视角" placement="top" :show-after="500">
          <button class="dock-item share-btn" @click="$emit('share-view')">
            <el-icon><ShareIcon /></el-icon>
          </button>
        </el-tooltip>

        <Transition name="fade-scale">
          <el-tooltip content="上传数据" placement="top" :show-after="500" v-if="isAdmin">
            <button class="dock-item upload-btn" @click="$emit('upload')">
              <el-icon><UploadFilled /></el-icon>
            </button>
          </el-tooltip>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
// 显式导入并使用别名，防止与原生 API 或全局组件冲突
import { 
  HomeFilled, 
  Files, 
  ScaleToOriginal as Ruler,
  Crop, 
  Aim, 
  InfoFilled, 
  Grid, 
  Share as ShareIcon, 
  UploadFilled 
} from '@element-plus/icons-vue';

const authStore = useAuthStore();
const isAdmin = computed(() => authStore.user?.role === 'admin');

// 严格的属性定义
interface Props {
  activeTool?: string;
}

const props = withDefaults(defineProps<Props>(), {
  activeTool: ''
});

// 严格的事件定义
const emit = defineEmits<{
  (e: 'home'): void;
  (e: 'toggle-layers'): void;
  (e: 'toggle-measure'): void;
  (e: 'toggle-selection'): void;
  (e: 'toggle-buffer'): void;
  (e: 'toggle-identify'): void;
  (e: 'open-gallery'): void;
  (e: 'share-view'): void;
  (e: 'upload'): void;
}>();
</script>

<style scoped>
/* ... existing styles ... */
.bottom-dock-container {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  justify-content: center;
  pointer-events: none;
}

.bottom-dock {
  pointer-events: auto;
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
  border-radius: 24px;
  gap: 4px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
}

.dock-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dock-divider {
  width: 1px;
  height: 24px;
  background: rgba(0, 0, 0, 0.1);
  margin: 0 10px;
}

.dock-item {
  position: relative;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #1d1d1f;
  font-size: 22px;
  cursor: pointer;
  border-radius: 14px;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  outline: none;
}

/* Apple Dock 核心动画：悬停放大 */
.dock-item:hover {
  transform: scale(1.3) translateY(-10px);
  background: rgba(255, 255, 255, 0.9);
  color: #0071e3;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
}

/* 邻近反馈效果：当 Dock 栏被触发时，其他未悬停的图标略微缩小 */
.bottom-dock:hover .dock-item:not(:hover) {
  transform: scale(0.92);
  opacity: 0.7;
}

.dock-item.active {
  color: #0071e3;
  background: rgba(0, 113, 227, 0.05);
}

.upload-btn, .share-btn {
  color: #0071e3;
}

.indicator {
  position: absolute;
  bottom: 6px;
  width: 4px;
  height: 4px;
  background-color: #0071e3;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(0, 113, 227, 0.4);
}

/* Transition for upload button */
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.5);
  width: 0;
  margin: 0;
}

/* 适配移动端，防止遮挡 */
@media (max-width: 768px) {
  .bottom-dock {
    height: 56px;
    padding: 0 10px;
    gap: 2px;
  }
  .dock-item {
    width: 40px;
    height: 40px;
    font-size: 18px;
  }
}
</style>