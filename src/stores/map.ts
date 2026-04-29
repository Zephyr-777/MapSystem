import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import type Map from 'ol/Map'
import type { LayerConfig } from '@/views/map/types/map'

export const useMapStore = defineStore('map', () => {
  const mapInstance = shallowRef<Map | null>(null)
  const mapReady = ref(false)

  const lastCenter = ref<[number, number]>([116.3974, 39.9093])
  const lastZoom = ref(10)
  const zoomLevel = ref(10)
  const currentBaseMap = ref<'vector' | 'satellite'>('vector')

  const selectedItems = ref<any[]>([])
  const selectedFeatureId = ref<number | null>(null)
  const selectedFeature = ref<any | null>(null)
  const selectedImageUrl = ref<string | null>(null)
  const selectedFullImageUrl = ref<string | null>(null)
  const sidePanelVisible = ref(false)
  const activeTool = ref('')

  const layerConfig = ref<LayerConfig>({})

  const is3DActive = ref(false)

  function setMapInstance(map: Map) {
    mapInstance.value = map
    mapReady.value = true
  }

  function clearMapInstance() {
    if (mapInstance.value) {
      mapInstance.value.setTarget(undefined as any)
    }
    mapInstance.value = null
    mapReady.value = false
  }

  function selectFeature(feature: any, imageUrl?: string | null, fullImageUrl?: string | null) {
    selectedFeatureId.value = feature?.id ?? feature?.properties?.id ?? null
    selectedFeature.value = feature ?? null
    selectedItems.value = feature ? [feature] : []
    selectedImageUrl.value = imageUrl ?? null
    selectedFullImageUrl.value = fullImageUrl ?? imageUrl ?? null
    sidePanelVisible.value = !!feature
  }

  function selectFeatures(features: any[]) {
    selectedItems.value = features
    selectedFeature.value = features.length === 1 ? features[0] : null
    selectedFeatureId.value = features.length === 1
      ? (features[0]?.id ?? features[0]?.properties?.id ?? null)
      : null
    if (features.length !== 1) {
      selectedImageUrl.value = null
      selectedFullImageUrl.value = null
    }
    sidePanelVisible.value = features.length > 0
  }

  function clearSelection() {
    selectedFeatureId.value = null
    selectedFeature.value = null
    selectedItems.value = []
    selectedImageUrl.value = null
    selectedFullImageUrl.value = null
    sidePanelVisible.value = false
  }

  function saveViewState() {
    if (!mapInstance.value) return
    const view = mapInstance.value.getView()
    const center = view.getCenter()
    if (center) {
      const { toLonLat } = require('ol/proj')
      lastCenter.value = toLonLat(center) as [number, number]
    }
    lastZoom.value = view.getZoom() ?? 10
  }

  return {
    mapInstance,
    mapReady,
    lastCenter,
    lastZoom,
    zoomLevel,
    currentBaseMap,
    selectedItems,
    selectedFeatureId,
    selectedFeature,
    selectedImageUrl,
    selectedFullImageUrl,
    sidePanelVisible,
    activeTool,
    layerConfig,
    is3DActive,
    setMapInstance,
    clearMapInstance,
    selectFeature,
    selectFeatures,
    clearSelection,
    saveViewState
  }
})
