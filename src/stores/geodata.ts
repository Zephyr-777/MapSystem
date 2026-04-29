import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { geoDataApi, type GeoDataItem } from '@/api/geodata'

export const useGeodataStore = defineStore('geodata', () => {
  const items = ref<GeoDataItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const itemCount = computed(() => items.value.length)

  async function fetchList(bbox?: [number, number, number, number]) {
    loading.value = true
    error.value = null
    try {
      const res = await geoDataApi.getList({ bbox })
      items.value = Array.isArray(res?.data) ? res.data : []
    } catch (e: any) {
      error.value = e.message || '加载数据失败'
    } finally {
      loading.value = false
    }
  }

  function updateItem(id: number, patch: Partial<GeoDataItem>) {
    const idx = items.value.findIndex(i => i.id === id)
    if (idx > -1) Object.assign(items.value[idx], patch)
  }

  function removeItem(id: number) {
    items.value = items.value.filter(i => i.id !== id)
  }

  return {
    items,
    loading,
    error,
    itemCount,
    fetchList,
    updateItem,
    removeItem
  }
})
