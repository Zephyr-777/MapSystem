import { describe, it, expect, vi } from 'vitest';
import useMapLayers from '../useMapLayers';

// Mock OpenLayers
vi.mock('ol/layer/Tile', () => ({
  default: class MockTileLayer {
    constructor(options: any) {
      this.visible = options.visible;
      this.props = {};
    }
    visible = false;
    props: Record<string, any>;
    set = vi.fn((key, val) => { this.props[key] = val; });
    get = vi.fn((key) => this.props[key]);
    setVisible = vi.fn((val) => { this.visible = val; });
  }
}));

vi.mock('ol/source/XYZ', () => ({
  default: class MockXYZ {
    on = vi.fn(); 
  }
}));

// Mock useMapCore
vi.mock('../useMapCore', () => ({
  default: () => ({
    getMap: () => ({
      addLayer: vi.fn(),
      removeLayer: vi.fn(),
    })
  })
}));

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    warning: vi.fn(),
    error: vi.fn(),
  }
}));

describe('useMapLayers', () => {
  it('should add TDT layer', () => {
    const { addTDTLayer, activeLayerKeys } = useMapLayers();
    activeLayerKeys.value = ['tdt-vec']; // Activate it
    
    const layer = addTDTLayer('vec');
    expect(layer).toBeDefined();
    // Since we mocked TileLayer, we can check its properties if needed
  });

  // Note: Testing the fallback logic (event listener callback) is tricky because 
  // we mocked XYZ and its 'on' method. We would need to capture the callback 
  // passed to 'on' and invoke it manually.
  
  it('should remove layer correctly', () => {
    const { addTDTLayer, removeLayer, layers } = useMapLayers();
    
    // Reset layers for test
    layers.value = [];

    // Add layer first
    addTDTLayer('img');
    expect(layers.value.length).toBe(1);
    expect(layers.value[0].get('id')).toBe('tdt-img');

    // Remove layer
    removeLayer('tdt-img');
    expect(layers.value.length).toBe(0);
  });
});
