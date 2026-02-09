import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import MapView from '../MapView.vue';
import { nextTick } from 'vue';

// Hoist mocks to access them in tests
const mocks = vi.hoisted(() => {
  const mockMapInstance = {
    setTarget: vi.fn(),
    getTargetElement: vi.fn().mockReturnValue(document.createElement('div')),
    getView: vi.fn().mockReturnValue({
      getZoom: vi.fn().mockReturnValue(10),
      setZoom: vi.fn(),
      animate: vi.fn(),
      on: vi.fn()
    }),
    on: vi.fn(),
    addLayer: vi.fn(),
    addInteraction: vi.fn(),
    removeInteraction: vi.fn(),
    getEventPixel: vi.fn(),
    forEachFeatureAtPixel: vi.fn()
  };

  return {
    mockMapInstance,
    mockInitMap: vi.fn().mockResolvedValue(mockMapInstance),
    mockGetMap: vi.fn().mockReturnValue(mockMapInstance),
    mockInitInteractions: vi.fn(),
    mockToggleDragBox: vi.fn(),
    mockClearSelection: vi.fn(),
    mockInitTooltip: vi.fn(),
    mockFlyTo: vi.fn(),
    mockAddOSMLayer: vi.fn(),
    mockAddEsriSatelliteLayer: vi.fn(),
    mockAddTDTLayer: vi.fn(),
    mockAddNavigationLayer: vi.fn(),
    mockAddClusterLayer: vi.fn(),
    mockRemoveLayer: vi.fn(),
    mockClearLayers: vi.fn(),
    mockGetList: vi.fn().mockResolvedValue([
      { id: 1, name: 'Point 1', center_x: 116.4, center_y: 39.9, srid: 4326 },
      { id: 2, name: 'Point 2', center_x: 116.5, center_y: 39.9, srid: 4326 }
    ]),
    mockSearch: vi.fn().mockResolvedValue([])
  };
});

// Mock Pinia Store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: { username: 'test' },
    logout: vi.fn()
  }))
}));

// Mock Router
vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn()
  }))
}));

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  MapLocation: 'MapLocation',
  Files: 'Files',
  Crop: 'Crop',
  Location: 'Location',
  Delete: 'Delete',
  SwitchButton: 'SwitchButton',
  Loading: 'Loading',
  Plus: 'Plus',
  Minus: 'Minus',
  RefreshRight: 'RefreshRight',
  Warning: 'Warning',
  Close: 'Close'
}));

// Mock API
vi.mock('@/api/geodata', () => ({
  geoDataApi: {
    getList: mocks.mockGetList,
    search: mocks.mockSearch
  }
}));

// Mock Composables
vi.mock('@/composables/useMapCore', () => ({
  default: () => ({
    initMap: mocks.mockInitMap,
    mapReady: true,
    getMap: mocks.mockGetMap
  })
}));

vi.mock('@/composables/useMapInteractions', () => ({
  default: () => ({
    initInteractions: mocks.mockInitInteractions,
    toggleDragBox: mocks.mockToggleDragBox,
    isDragBoxActive: false,
    selectedExtent: null,
    selectedItems: { value: [] },
    clearSelection: mocks.mockClearSelection,
    initTooltip: mocks.mockInitTooltip,
    flyTo: mocks.mockFlyTo,
    removeInteractions: vi.fn()
  })
}));

// Mock activeLayerKeys as a simple ref
const mockActiveLayerKeys = { value: [] };
vi.mock('@/composables/useMapLayers', () => ({
  default: () => ({
    addOSMLayer: mocks.mockAddOSMLayer,
    addEsriSatelliteLayer: mocks.mockAddEsriSatelliteLayer,
    addTDTLayer: mocks.mockAddTDTLayer,
    addNavigationLayer: mocks.mockAddNavigationLayer,
    addClusterLayer: mocks.mockAddClusterLayer,
    removeLayer: mocks.mockRemoveLayer,
    clearLayers: mocks.mockClearLayers,
    activeLayerKeys: mockActiveLayerKeys,
    isFallbackActive: false
  })
}));

// Mock OpenLayers classes
vi.mock('ol/Map', () => ({ default: class MockMap {} }));
vi.mock('ol/View', () => ({ default: class MockView {} }));
vi.mock('ol/layer/Vector', () => ({ default: class MockVectorLayer { constructor(_opts: any) {} } }));
vi.mock('ol/source/Vector', () => ({ 
  default: class MockVectorSource { 
    constructor() {} 
    clear() {}
    addFeature() {}
    getFeatures() { return []; }
    getFeaturesInExtent() { return []; }
  } 
}));
vi.mock('ol/Feature', () => ({ default: class MockFeature { constructor(_geom: any) {} } }));
vi.mock('ol/geom/Point', () => ({ default: class MockPoint { constructor(_coords: any) {} } }));
vi.mock('ol/style', () => ({
  Style: class {},
  Fill: class {},
  Stroke: class {},
  Circle: class {}
}));
vi.mock('ol/proj', () => ({
  fromLonLat: (coord: number[]) => coord,
  toLonLat: (coord: number[]) => coord
}));

describe('MapView.vue', () => {
  let wrapper: any;

  beforeEach(() => {
    vi.clearAllMocks();
    wrapper = mount(MapView, {
      global: {
        stubs: {
          MapContainer: {
            template: '<div class="map-container"><slot /></div>',
            methods: {
              getMapElement: () => document.createElement('div')
            }
          },
          InfoPanel: true,
          LayerControl: true,
          SearchBox: true,
          StatsPanel: true,
          ErrorBoundary: { template: '<div><slot /></div>' },
          'el-icon': true,
          'el-slider': true,
          'el-button': true,
          'el-tooltip': {
            template: '<div><slot /></div>'
          },
          'el-empty': true,
          'el-dialog': true
        }
      }
    });
  });

  it('initializes map on mount', async () => {
    await flushPromises();
    expect(mocks.mockInitMap).toHaveBeenCalled();
    expect(mocks.mockAddOSMLayer).toHaveBeenCalled();
    expect(mocks.mockInitInteractions).toHaveBeenCalled();
  });

  it('loads geo data on mount', async () => {
    await flushPromises();
    expect(mocks.mockGetList).toHaveBeenCalled();
  });

  it('toggles drag box interaction', async () => {
    await flushPromises();
    // Wait for Suspense to resolve
    await nextTick();
    await nextTick();
    
    const toolbar = wrapper.find('.floating-toolbar');
    expect(toolbar.exists()).toBe(true);
    
    // Find buttons by finding el-button-stub since we stubbed it
    const buttons = toolbar.findAll('el-button-stub');
    
    // 0: BaseMap, 1: LayerControl, 2: DragBox, 3: Locate, 4: Clear, 5: Logout
    expect(buttons.length).toBeGreaterThan(2);
    const toggleBtn = buttons[2]; 
    
    await toggleBtn.trigger('click');
    expect(mocks.mockToggleDragBox).toHaveBeenCalled();
  });

  it('handles zoom controls', async () => {
    await flushPromises();
    const zoomInBtn = wrapper.find('.zoom-btn:first-child');
    await zoomInBtn.trigger('click');
    expect(mocks.mockMapInstance.getView().animate).toHaveBeenCalled();
  });
});
