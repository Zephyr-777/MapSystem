<template>
  <div ref="mapEl" class="map-container" :class="{ 'has-map': !!mapInstance }">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue';
import type Map from 'ol/Map';

const props = defineProps<{
  mapInstance: Map | null;
}>();

const emit = defineEmits<{
  (e: 'map-ready', map: Map): void;
}>();

const mapEl = ref<HTMLDivElement | null>(null);

defineExpose({
  getMapElement: () => mapEl.value
});

onMounted(() => {
  console.log('MapContainer mounted, mapEl exists:', !!mapEl.value);
  if (props.mapInstance && mapEl.value) {
    props.mapInstance.setTarget(mapEl.value);
    setTimeout(() => {
      props.mapInstance?.updateSize();
    }, 100);
    emit('map-ready', props.mapInstance);
  }
});

watch(() => props.mapInstance, (newMap) => {
  if (newMap && mapEl.value) {
    console.log('MapContainer: mapInstance updated, setting target');
    newMap.setTarget(mapEl.value);
    setTimeout(() => {
      newMap.updateSize();
    }, 100);
    emit('map-ready', newMap);
  }
});

onUnmounted(() => {
  if (props.mapInstance) {
    props.mapInstance.setTarget(undefined);
  }
});
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  background-color: #f5f7fa;
  transition: background-color 0.3s;
}

.map-container.has-map {
  background-color: transparent;
}
</style>
