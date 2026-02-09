import { ref, onUnmounted } from 'vue';
import { DragBox } from 'ol/interaction';
import { platformModifierKeyOnly } from 'ol/events/condition';
import Overlay from 'ol/Overlay';
import Point from 'ol/geom/Point';
import useMapCore from './useMapCore';
import type { GeoDataItem } from '@/views/map/types/map';

export default function useMapInteractions() {
  const { getMap } = useMapCore();
  
  const isDragBoxActive = ref(false);
  const selectedExtent = ref<[number, number, number, number] | null>(null);
  const selectedItems = ref<GeoDataItem[]>([]);
  
  let dragBoxInteraction: DragBox | null = null;
  let tooltipOverlay: Overlay | null = null;

  const initInteractions = (
    onFeatureSelect: (feature: any) => void,
    onExtentSelect: (extent: [number, number, number, number], geometry: any) => void,
    onBlankClick?: () => void
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
        // No feature hit - blank click
        if (onBlankClick) {
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
      
      if (tooltipOverlay) {
          map.removeOverlay(tooltipOverlay);
          tooltipOverlay = null;
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
      removeInteractions
  };
}
