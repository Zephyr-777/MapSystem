import { ref, onUnmounted } from 'vue';
import { DragBox } from 'ol/interaction';
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
    onExtentSelect: (extent: [number, number, number, number], geometry: any) => void
  ) => {
    const map = getMap();
    if (!map) return;

    // Click Interaction
    map.on('singleclick', (evt) => {
      if (isDragBoxActive.value) return;

      const pixel = map.getEventPixel(evt.originalEvent);
      const hit = map.forEachFeatureAtPixel(pixel, (feature) => feature);

      if (hit) {
        // Check cluster
        const features = hit.get('features');
        if (features) {
            if (features.length === 1) {
                const feature = features[0];
                const props = feature.getProperties();
                // Map properties to GeoDataItem if needed, or pass props
                // Assuming props match GeoDataItem structure approximately
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
      }
    });

    // DragBox Interaction
    dragBoxInteraction = new DragBox({
        className: 'ol-dragbox',
    });

    dragBoxInteraction.on('boxend', () => {
        if (!dragBoxInteraction) return;
        const geometry = dragBoxInteraction.getGeometry();
        const extent = geometry.getExtent();
        selectedExtent.value = extent as [number, number, number, number];
        onExtentSelect(selectedExtent.value, geometry);
    });

    // Initial state: remove dragbox
    map.removeInteraction(dragBoxInteraction);
  };

  const toggleDragBox = () => {
    const map = getMap();
    if (!map || !dragBoxInteraction) return;

    isDragBoxActive.value = !isDragBoxActive.value;
    if (isDragBoxActive.value) {
        map.addInteraction(dragBoxInteraction);
    } else {
        map.removeInteraction(dragBoxInteraction);
    }
  };

  const clearSelection = () => {
    selectedExtent.value = null;
    selectedItems.value = [];
    if (isDragBoxActive.value) {
        toggleDragBox(); // Turn off
    }
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
          // Update content via ref in component
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

  onUnmounted(() => {
      // Cleanup interactions if needed
  });

  return {
      initInteractions,
      toggleDragBox,
      isDragBoxActive,
      selectedExtent,
      selectedItems,
      clearSelection,
      initTooltip,
      flyTo
  };
}
