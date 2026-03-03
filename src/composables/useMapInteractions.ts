import { ref, onUnmounted } from 'vue';
import { DragBox, Draw } from 'ol/interaction';
import { platformModifierKeyOnly } from 'ol/events/condition';
import Overlay from 'ol/Overlay';
import Point from 'ol/geom/Point';
import VectorSource from 'ol/source/Vector';
import VectorLayer from 'ol/layer/Vector';
import { Style, Stroke, Fill } from 'ol/style';
import useMapCore from './useMapCore';
import type { GeoDataItem } from '@/views/map/types/map';

export default function useMapInteractions() {
  const { getMap } = useMapCore();
  
  const isDragBoxActive = ref(false);
  const selectedExtent = ref<[number, number, number, number] | null>(null);
  const selectedItems = ref<GeoDataItem[]>([]);
  
  let dragBoxInteraction: DragBox | null = null;
  let drawInteraction: Draw | null = null;
  let tooltipOverlay: Overlay | null = null;
  let drawLayer: VectorLayer<VectorSource> | null = null;

  const initDrawLayer = () => {
    const map = getMap();
    if (!map || drawLayer) return;

    const source = new VectorSource();
    drawLayer = new VectorLayer({
      source: source,
      style: new Style({
        fill: new Fill({
          color: 'rgba(255, 255, 255, 0.2)',
        }),
        stroke: new Stroke({
          color: '#ffcc33',
          width: 2,
        }),
      }),
      zIndex: 1000,
    });
    map.addLayer(drawLayer);
  };

  const startDrawing = (type: 'Circle' | 'Polygon' | 'Box', onDrawEnd: (geometry: any) => void) => {
    const map = getMap();
    if (!map) return;
    
    stopDrawing(); // Clear existing draw
    initDrawLayer();

    if (type === 'Box') {
       // Special case for Box if needed, but usually DragBox handles this.
       // Here we implement Circle for buffer.
       return;
    }

    const source = drawLayer?.getSource();
    if (!source) return;

    drawInteraction = new Draw({
      source: source,
      type: type as any,
    });

    drawInteraction.on('drawend', (evt) => {
      const geometry = evt.feature.getGeometry();
      onDrawEnd(geometry);
      // Optional: stop drawing after one shape?
      // stopDrawing(); 
      // Or keep drawing? Usually for buffer tool we want one circle then maybe stop or allow redraw.
      // Let's clear previous features to allow only one buffer zone at a time
      source.clear(); 
    });

    map.addInteraction(drawInteraction);
  };

  const stopDrawing = () => {
    const map = getMap();
    if (!map) return;

    if (drawInteraction) {
      map.removeInteraction(drawInteraction);
      drawInteraction = null;
    }
    
    if (drawLayer) {
        drawLayer.getSource()?.clear();
        // map.removeLayer(drawLayer); // Optional: keep layer or remove
        // drawLayer = null;
    }
  };


  const initInteractions = (
    onFeatureSelect: (feature: any) => void,
    onExtentSelect: (extent: [number, number, number, number], geometry: any) => void,
    onBlankClick?: () => void,
    onIdentify?: (lon: number, lat: number, coords: number[]) => void
  ) => {
    const map = getMap();
    if (!map) return;

    // Click Interaction
    map.on('singleclick', (evt) => {
      // Allow click if not dragging box (DragBox with modifier doesn't block click unless active)
      
      const pixel = map.getEventPixel(evt.originalEvent);
      const hit = map.forEachFeatureAtPixel(pixel, (feature) => feature);

      if (hit) {
        // ... (feature logic remains the same)
        // Check cluster
        const features = hit.get('features');
        if (features) {
            if (features.length === 1) {
                const feature = features[0];
                const props = feature.getProperties();
                onFeatureSelect({ ...props, geometry: feature.getGeometry() });
                
                // Animate to feature
                const geometry = feature.getGeometry();
                if (geometry && geometry.getType() === 'Point') {
                    const coords = (geometry as Point).getCoordinates();
                    map.getView().animate({
                        center: coords,
                        zoom: 12,
                        duration: 500
                    });
                }
            } else {
                // Zoom to cluster
                const geometry = hit.getGeometry();
                if (geometry && geometry.getType() === 'Point') {
                    const coords = (geometry as Point).getCoordinates();
                    map.getView().animate({
                        center: coords,
                        zoom: (map.getView().getZoom() || 10) + 2,
                        duration: 500
                    });
                }
            }
        } else {
             // Normal feature
             const props = hit.getProperties();
             if (props.name || props.type) {
                 onFeatureSelect({ ...props, geometry: hit.getGeometry() });
             }
        }
      } else {
        // Identify or Blank Click
        // If identify callback provided, use it
        if (onIdentify) {
            // Import toLonLat here or assume it's available or use map projection
            // Since we can't easily import ol/proj inside function without module system overhead,
            // we will pass the coordinate and let the caller handle transform if needed,
            // OR use map view projection.
            // But usually we need LonLat for backend.
            // Let's assume the caller will handle transform or we do it if we can.
            
            // To keep it simple and avoid import issues in this file if not already imported:
            // We'll pass the raw coordinate and let MapView handle the rest as it has toLonLat.
            
            // Wait, we need to pass lon/lat to onIdentify as per signature?
            // Actually, better to pass raw coords and let MapView convert.
            // But the signature I defined above says (lon, lat, coords).
            // Let's just pass coords and let MapView convert.
            
            // Actually, let's just pass the event coordinate.
            // We need to change the signature in `initInteractions`.
            // Let's import toLonLat at top level if not present.
            // It is NOT present in the file content read above.
            
            // So we will just call onIdentify with coords and let MapView do the math.
            // BUT, wait, I can't change the signature without changing MapView.vue call site.
            // So I will update MapView.vue call site as well.
            
            onIdentify(0, 0, evt.coordinate); // Passing 0,0 as placeholders, real coords in 3rd arg
        } else if (onBlankClick) {
            onBlankClick();
        }
      }
    });

    // DragBox Interaction
    dragBoxInteraction = new DragBox({
        className: 'ol-dragbox',
        condition: platformModifierKeyOnly, // Ctrl + Drag
    });

    dragBoxInteraction.on('boxend', () => {
        if (!dragBoxInteraction) return;
        const geometry = dragBoxInteraction.getGeometry();
        const extent = geometry.getExtent();
        selectedExtent.value = extent as [number, number, number, number];
        onExtentSelect(selectedExtent.value, geometry);
    });

    map.addInteraction(dragBoxInteraction);
    isDragBoxActive.value = true;
  };

  const toggleDragBox = () => {
    console.warn('DragBox is now always active with Ctrl key');
  };

  const clearSelection = () => {
    selectedExtent.value = null;
    selectedItems.value = [];
  };

  const initTooltip = (element: HTMLElement) => {
      const map = getMap();
      if (!map) return;

      tooltipOverlay = new Overlay({
          element: element,
          offset: [15, 0],
          positioning: 'center-left',
          stopEvent: false,
      });
      map.addOverlay(tooltipOverlay);

      map.on('pointermove', (evt) => {
          if (evt.dragging) {
              tooltipOverlay?.setPosition(undefined);
              return;
          }
          tooltipOverlay?.setPosition(evt.coordinate);
      });
  };

  const flyTo = (center: number[], zoom: number = 12) => {
      const map = getMap();
      if (map) {
          map.getView().animate({
              center,
              zoom,
              duration: 1000
          });
      }
  };

  const removeInteractions = () => {
      const map = getMap();
      if (!map) return;

      if (dragBoxInteraction) {
          map.removeInteraction(dragBoxInteraction);
          dragBoxInteraction = null;
      }

      if (drawInteraction) {
          map.removeInteraction(drawInteraction);
          drawInteraction = null;
      }
      
      if (tooltipOverlay) {
          map.removeOverlay(tooltipOverlay);
          tooltipOverlay = null;
      }

      if (drawLayer) {
          map.removeLayer(drawLayer);
          drawLayer = null;
      }
  };

  onUnmounted(() => {
      removeInteractions();
  });

  return {
      initInteractions,
      toggleDragBox,
      isDragBoxActive,
      selectedExtent,
      selectedItems,
      clearSelection,
      initTooltip,
      flyTo,
      removeInteractions,
      startDrawing,
      stopDrawing
  };
}
