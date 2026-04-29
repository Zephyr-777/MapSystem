<template>
  <div class="layer-manager glass-morphism">
    <div class="panel-header">
      <h3>图层管理</h3>
      <el-button link @click="$emit('close')"><el-icon><Close /></el-icon></el-button>
    </div>
    
    <div class="layer-list">
      <div class="layer-group-title">基础底图</div>
      
      <div class="layer-item" v-for="layer in baseLayers" :key="layer.id">
        <div class="layer-control">
          <el-checkbox v-model="layer.visible" @change="toggleLayer(layer)">
            {{ layer.name }}
          </el-checkbox>
          <div class="layer-actions">
             <el-slider 
                v-model="layer.opacity" 
                :min="0" :max="1" :step="0.1" 
                size="small"
                style="width: 60px"
                @input="updateOpacity(layer)"
             />
          </div>
        </div>
      </div>

      <div class="layer-group-title" style="margin-top: 15px;">叠加图层</div>
      
      <div class="layer-item" v-for="layer in overlayLayers" :key="layer.id">
        <div class="layer-control">
          <el-checkbox v-model="layer.visible" @change="toggleLayer(layer)">
            {{ layer.name }}
          </el-checkbox>
           <div class="layer-actions">
             <el-slider 
                v-model="layer.opacity" 
                :min="0" :max="1" :step="0.1" 
                size="small"
                style="width: 60px"
                @input="updateOpacity(layer)"
             />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { Close } from '@element-plus/icons-vue';
import Map from 'ol/Map';


const props = defineProps<{
  map: Map | null;
}>();

const emit = defineEmits(['close']);

interface LayerConfig {
  id: string;
  name: string;
  visible: boolean;
  opacity: number;
  type: 'base' | 'overlay';
  olLayer?: any; // Use any to avoid strict BaseLayer mismatch
}

const baseLayers = ref<LayerConfig[]>([]);
const overlayLayers = ref<LayerConfig[]>([]);

const initLayers = () => {
  if (!props.map) return;
  
  const layers = props.map.getLayers().getArray();
  
  baseLayers.value = [];
  overlayLayers.value = [];

  layers.forEach(layer => {
    const title = layer.get('title');
    const type = layer.get('type') || 'overlay';
    
    if (title) {
      const config: LayerConfig = {
        id: title,
        name: title,
        visible: layer.getVisible(),
        opacity: layer.getOpacity(),
        type: type,
        olLayer: layer
      };
      
      if (type === 'base') {
        baseLayers.value.push(config);
      } else {
        overlayLayers.value.push(config);
      }
    }
  });
};

const toggleLayer = (layer: LayerConfig) => {
  if (layer.olLayer) {
    layer.olLayer.setVisible(layer.visible);
  }
};

const updateOpacity = (layer: LayerConfig) => {
  if (layer.olLayer) {
    layer.olLayer.setOpacity(layer.opacity);
  }
};

onMounted(() => {
  initLayers();
});

watch(() => props.map, () => {
  initLayers();
});

</script>

<style scoped>
.layer-manager {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-150%);
  width: 280px;
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

.layer-group-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  font-weight: bold;
}

.layer-item {
  margin-bottom: 8px;
}

.layer-control {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.layer-actions {
    width: 80px;
}
</style>
