import { defineStore } from 'pinia'
import { ref } from 'vue'
import { geologyApi, type FeatureGeoJSON, type GeologyStats, type GeologyFilterParams } from '@/api/geology'

export const useGeologyStore = defineStore('geology', () => {
  const features = ref<FeatureGeoJSON[]>([])
  const stats = ref<GeologyStats>({
    eras: {},
    lithologies: {},
    structures: {},
    minerals: {}
  })
  const loading = ref(false)
  const error = ref<string | null>(null)
  const totalCount = ref(0)

  const filters = ref<GeologyFilterParams>({})
  const currentPage = ref(1)
  const pageSize = ref(100)

  async function fetchFeatures() {
    loading.value = true
    error.value = null
    try {
      const res = await geologyApi.getFeatures({
        ...filters.value,
        page: currentPage.value,
        page_size: pageSize.value
      })
      features.value = res.features || []
      totalCount.value = res.total || 0
    } catch (e: any) {
      error.value = e.message || '加载地质要素失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await geologyApi.getStats()
    } catch (e) {
      console.error('Failed to load geology stats', e)
    }
  }

  function setFilter(key: keyof GeologyFilterParams, value: string | number | undefined) {
    if (value !== undefined && value !== '') {
      (filters.value as any)[key] = value
    } else {
      delete (filters.value as any)[key]
    }
    currentPage.value = 1
  }

  function clearFilters() {
    filters.value = {}
    currentPage.value = 1
  }

  return {
    features,
    stats,
    loading,
    error,
    totalCount,
    filters,
    currentPage,
    pageSize,
    fetchFeatures,
    fetchStats,
    setFilter,
    clearFilters
  }
})
