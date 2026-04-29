import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import MapView from '../MapView.vue'

const mocks = vi.hoisted(() => {
  const animate = vi.fn()
  const mockView = {
    getZoom: vi.fn().mockReturnValue(10),
    setZoom: vi.fn(),
    animate,
    on: vi.fn(),
    getCenter: vi.fn().mockReturnValue([116.4, 39.9]),
    calculateExtent: vi.fn().mockReturnValue([116, 39, 117, 40]),
    fit: vi.fn(),
  }

  const mockMapInstance = {
    setTarget: vi.fn(),
    getTargetElement: vi.fn().mockReturnValue(document.createElement('div')),
    getView: vi.fn().mockReturnValue(mockView),
    on: vi.fn(),
    addLayer: vi.fn(),
    addInteraction: vi.fn(),
    removeInteraction: vi.fn(),
    addOverlay: vi.fn(),
    removeOverlay: vi.fn(),
    render: vi.fn(),
    getSize: vi.fn().mockReturnValue([1280, 720]),
    getEventPixel: vi.fn(),
    forEachFeatureAtPixel: vi.fn(),
  }

  return {
    animate,
    mockMapInstance,
    mockInitMap: vi.fn().mockResolvedValue(mockMapInstance),
    mockInitInteractions: vi.fn(),
    mockToggleDragBox: vi.fn(),
    mockInitTooltip: vi.fn(),
    mockFlyTo: vi.fn(),
    mockAddOSMLayer: vi.fn(),
    mockAddEsriSatelliteLayer: vi.fn(),
    mockAddTDTLayer: vi.fn(),
    mockAddNavigationLayer: vi.fn(),
    mockAddClusterLayer: vi.fn(),
    mockAddHeatmapLayer: vi.fn(),
    mockRemoveLayer: vi.fn(),
    mockClearLayers: vi.fn(),
    mockStartDrawing: vi.fn(),
    mockStopDrawing: vi.fn(),
    mockGetList: vi.fn().mockResolvedValue({
      data: [
        { id: 1, name: 'Point 1', center_x: 116.4, center_y: 39.9, srid: 4326, uploadTime: '' },
        { id: 2, name: 'Point 2', center_x: 116.5, center_y: 39.9, srid: 4326, uploadTime: '' },
      ],
      total: 2,
    }),
    mockSearch: vi.fn().mockResolvedValue({ data: [], total: 0 }),
    mockBufferQuery: vi.fn().mockResolvedValue({ data: [], total: 0 }),
    mockFetchList: vi.fn(),
    mockLogout: vi.fn(),
    mockRouterPush: vi.fn(),
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: { username: 'test' },
    logout: mocks.mockLogout,
  })),
}))

vi.mock('@/stores/geodata', () => ({
  useGeodataStore: vi.fn(() => {
    const store = {
      items: [
        { id: 1, name: 'Point 1', center_x: 116.4, center_y: 39.9, srid: 4326, uploadTime: '' },
        { id: 2, name: 'Point 2', center_x: 116.5, center_y: 39.9, srid: 4326, uploadTime: '' },
      ],
      error: null as string | null,
      fetchList: mocks.mockFetchList.mockImplementation(async () => store.items),
    }
    return store
  }),
}))

vi.mock('@/stores/map', () => ({
  useMapStore: vi.fn(() => ({
    selectFeature: vi.fn(),
    selectFeatures: vi.fn(),
    clearSelection: vi.fn(),
    selectedImageUrl: null,
    selectedFullImageUrl: null,
  })),
}))

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: mocks.mockRouterPush,
  })),
  useRoute: vi.fn(() => ({
    query: {},
  })),
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    info: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
  ElNotification: vi.fn(),
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue(true),
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  Location: { template: '<span />' },
  Loading: { template: '<span />' },
  Plus: { template: '<span />' },
  Minus: { template: '<span />' },
  RefreshRight: { template: '<span />' },
  Close: { template: '<span />' },
  LocationInformation: { template: '<span />' },
  SwitchButton: { template: '<span />' },
  Monitor: { template: '<span />' },
}))

vi.mock('@/api/geodata', () => ({
  geoDataApi: {
    getList: mocks.mockGetList,
    search: mocks.mockSearch,
    bufferQuery: mocks.mockBufferQuery,
    getPreviewUrl: vi.fn((id: number, fullSize = false) => `/api/geodata/preview/${id}${fullSize ? '?full_size=true' : ''}`),
  },
}))

vi.mock('@/composables/useMapCore', () => ({
  default: () => ({
    initMap: mocks.mockInitMap,
    mapReady: ref(true),
  }),
}))

vi.mock('@/composables/useMapInteractions', () => ({
  default: () => ({
    initInteractions: mocks.mockInitInteractions,
    toggleDragBox: mocks.mockToggleDragBox,
    isDragBoxActive: ref(false),
    initTooltip: mocks.mockInitTooltip,
    flyTo: mocks.mockFlyTo,
    removeInteractions: vi.fn(),
    selectedItems: ref([]),
    startDrawing: mocks.mockStartDrawing,
    stopDrawing: mocks.mockStopDrawing,
  }),
}))

vi.mock('@/composables/useMapLayers', () => ({
  default: () => ({
    addOSMLayer: mocks.mockAddOSMLayer,
    addEsriSatelliteLayer: mocks.mockAddEsriSatelliteLayer,
    addTDTLayer: mocks.mockAddTDTLayer,
    addNavigationLayer: mocks.mockAddNavigationLayer,
    addClusterLayer: mocks.mockAddClusterLayer,
    addHeatmapLayer: mocks.mockAddHeatmapLayer,
    removeLayer: mocks.mockRemoveLayer,
    clearLayers: mocks.mockClearLayers,
    activeLayerKeys: ref([]),
    layers: ref([]),
  }),
}))

vi.mock('ol/source/Vector', () => ({
  default: class MockVectorSource {
    clear() {}
    addFeature() {}
    getFeatures() {
      return []
    }
    getFeaturesInExtent() {
      return []
    }
  },
}))

vi.mock('ol/Feature', () => ({
  default: class MockFeature {
    constructor(_options?: unknown) {}
  },
}))

vi.mock('ol/geom/Point', () => ({
  default: class MockPoint {
    constructor(_coords?: unknown) {}
  },
}))

vi.mock('ol/Overlay', () => ({
  default: class MockOverlay {
    setPosition = vi.fn()
  },
}))

vi.mock('ol/proj', () => ({
  fromLonLat: (coord: number[]) => coord,
  toLonLat: (coord: number[]) => coord,
}))

vi.mock('@/services/mapInteraction', () => ({
  toMapCoords: (coord: number[]) => coord,
  createHighlightLayer: () => ({
    source: { clear: vi.fn(), addFeature: vi.fn() },
    layer: { set: vi.fn() },
  }),
  createBufferLayer: () => ({
    source: { clear: vi.fn(), addFeature: vi.fn() },
    layer: { set: vi.fn() },
  }),
  extentToWGS84: (extent: number[]) => extent,
}))

describe('MapView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function mountView() {
    return mount(MapView, {
      global: {
        stubs: {
          ErrorBoundary: { template: '<div><slot /></div>' },
          MapContainer: {
            template: '<div class="map-container"><slot /></div>',
            methods: {
              getMapElement: () => document.createElement('div'),
            },
          },
          SmartSearchBox: true,
          LayerControl: true,
          InfoPanel: true,
          StatsPanel: true,
          UploadDialog: true,
          CesiumContainer: true,
          BottomDock: {
            template: '<div class="bottom-dock-stub"></div>',
          },
          Transition: false,
          'el-icon': { template: '<i><slot /></i>' },
          'el-slider': true,
          'el-button': { template: '<button><slot /></button>' },
          'el-tooltip': { template: '<div><slot /></div>' },
          'el-empty': { template: '<div><slot name="description" /></div>' },
        },
      },
    })
  }

  it('initializes map and interactions on mount', async () => {
    mountView()
    await flushPromises()

    expect(mocks.mockInitMap).toHaveBeenCalled()
    expect(mocks.mockAddOSMLayer).toHaveBeenCalled()
    expect(mocks.mockInitInteractions).toHaveBeenCalled()
  })

  it('loads geo data on mount', async () => {
    mountView()
    await flushPromises()

    expect(mocks.mockFetchList).toHaveBeenCalled()
    expect(mocks.mockAddClusterLayer).toHaveBeenCalled()
  })

  it('handles zoom controls', async () => {
    const wrapper = mountView()
    await flushPromises()

    const zoomButtons = wrapper.findAll('.zoom-btn')
    expect(zoomButtons).toHaveLength(2)

    await zoomButtons[0].trigger('click')
    await nextTick()

    expect(mocks.animate).toHaveBeenCalled()
  })

  it('triggers logout flow from control button', async () => {
    const wrapper = mountView()
    await flushPromises()

    const logoutButton = wrapper.find('.logout-btn')
    await logoutButton.trigger('click')
    await flushPromises()

    expect(mocks.mockLogout).toHaveBeenCalled()
  })
})
