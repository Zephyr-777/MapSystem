<template>
  <div class="cesium-container" ref="cesiumContainer" v-show="visible"></div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, toRaw } from 'vue';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

const props = defineProps<{
  visible: boolean;
  viewState: {
    center: [number, number]; // [lon, lat]
    zoom: number;
    extent?: [number, number, number, number]; // [minX, minY, maxX, maxY] (LonLat)
  };
  features: any[]; // GeoJSON features or custom objects
}>();

const cesiumContainer = ref<HTMLDivElement | null>(null);
let viewer: Cesium.Viewer | null = null;
let dataSource: Cesium.CustomDataSource | null = null;

onMounted(() => {
  if (cesiumContainer.value) {
    initCesium();
  }
});

onUnmounted(() => {
  if (viewer) {
    viewer.destroy();
    viewer = null;
  }
});

const initCesium = () => {
  // Use local or default token. If no token, some imagery might be watermarked or fail.
  // Cesium.Ion.defaultAccessToken = 'YOUR_TOKEN'; 
  
  // Use OpenStreetMap (OSM) as requested
  const osmImagery = new Cesium.OpenStreetMapImageryProvider({
      url : 'https://a.tile.openstreetmap.org/'
  });

  viewer = new Cesium.Viewer(cesiumContainer.value!, {
    animation: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: true,
    sceneModePicker: false, 
    selectionIndicator: true,
    timeline: false,
    navigationHelpButton: false,
    navigationInstructionsInitiallyVisible: false,
    // Removed scene3DOnly to prevent initialization conflicts if any, though sceneModePicker: false usually fixes it.
    // But user requested to remove scene3DOnly.
    // scene3DOnly: true, 
    imageryProvider: osmImagery
  } as any);

  // Optimize: disable render loop when not visible (controlled by watch)
  viewer.useDefaultRenderLoop = false;

  // Hide credit (strictly speaking requires attribution, usually overlay)
  // (viewer.cesiumWidget.creditContainer as HTMLElement).style.display = 'none';

  dataSource = new Cesium.CustomDataSource('geo-data');
  viewer.dataSources.add(dataSource);
  
  // Initial sync if visible
  if (props.visible) {
    viewer.useDefaultRenderLoop = true;
    syncCamera();
    // Use loadDataToCesium instead of updateFeatures
    loadDataToCesium();
  }
};

const loadDataToCesium = async () => {
  if (!viewer) return;

  // Clear existing
  viewer.dataSources.removeAll();
  
  // Assuming props.features is already the data we need (GeoJSON features array)
  // But Cesium.GeoJsonDataSource.load expects a GeoJSON object or URL.
  // We construct a FeatureCollection from props.features
  const geoJsonData = {
      type: "FeatureCollection",
      features: props.features
  };
  
  try {
      // Use GeoJsonDataSource
      const dataSource = await Cesium.GeoJsonDataSource.load(geoJsonData, {
          stroke: Cesium.Color.WHITE,
          fill: Cesium.Color.fromCssColorString('#0071E3'),
          strokeWidth: 2,
          markerSymbol: '?' // Default marker
      });
      
      // Clustering
      dataSource.clustering.enabled = true;
      dataSource.clustering.pixelRange = 15;
      dataSource.clustering.minimumClusterSize = 3;

      await viewer.dataSources.add(dataSource);
      
      // Fly to East China Cenozoic region (110-123E, 28-40N)
      // This overrides syncCamera.
      const eastChinaRect = Cesium.Rectangle.fromDegrees(110.0, 28.0, 123.0, 40.0);
      viewer.camera.flyTo({
          destination: eastChinaRect,
          duration: 2.0
      });
      
  } catch (error) {
      console.error('Failed to load GeoJSON to Cesium:', error);
  }
};

// Sync Camera
const syncCamera = () => {
  if (!viewer || !props.viewState) return;

  const { center, zoom, extent } = props.viewState;
  
  // Convert Zoom to Height (Smooth transition)
  // 10000000 / 2^zoom is a good heuristic for Cesium
  const height = 10000000 / Math.pow(2, zoom); 

  // Use flyTo for smooth transition
  viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(center[0], center[1], height),
      duration: 1.5, // 1.5s flight duration
      easingFunction: Cesium.EasingFunction.QUINTIC_IN_OUT
  });
};

// Update Features
const updateFeatures = () => {
  if (!viewer || !dataSource) return;
  
  dataSource.entities.removeAll();
  
  const features = props.features;
  if (!features || features.length === 0) return;
  
  features.forEach((f: any) => {
      // Expecting f to be GeoDataItem or GeoJSON feature
      // If GeoDataItem: center_x, center_y, name, etc.
      let lon, lat, name, description;
      
      if (f.center_x && f.center_y) {
          lon = f.center_x;
          lat = f.center_y;
          name = f.name;
          description = f.description || `Type: ${f.type}`;
      } else if (f.geometry && f.geometry.coordinates) {
          // GeoJSON
          lon = f.geometry.coordinates[0];
          lat = f.geometry.coordinates[1];
          name = f.properties?.name;
          description = f.properties?.description;
      }
      
      if (lon !== undefined && lat !== undefined) {
          dataSource!.entities.add({
              name: name || 'Unknown',
              description: description,
              position: Cesium.Cartesian3.fromDegrees(lon, lat),
              point: {
                  pixelSize: 10,
                  color: Cesium.Color.fromCssColorString('#0071E3'),
                  outlineColor: Cesium.Color.WHITE,
                  outlineWidth: 2,
                  heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
              },
              label: {
                  text: name,
                  font: '12px sans-serif',
                  style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                  fillColor: Cesium.Color.WHITE,
                  outlineColor: Cesium.Color.BLACK,
                  outlineWidth: 2,
                  verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                  pixelOffset: new Cesium.Cartesian2(0, -15),
                  heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
              }
          });
      }
  });
};

watch(() => props.visible, (val) => {
  if (viewer) {
      if (val) {
      // Enable render loop
      viewer.useDefaultRenderLoop = true;
      viewer.resize();
      
      // Load data & Fly to region
      loadDataToCesium();
      
      // Sync Camera (Optional: if we want to sync OL view instead of flying to East China)
      // The requirement says "Auto flyTo East China region when toggling to 3D".
      // So we prioritize loadDataToCesium's flyTo logic.
      // But maybe we should sync camera first then fly? 
      // loadDataToCesium includes a flyTo.
  } else {
          // Disable render loop to save resources
          viewer.useDefaultRenderLoop = false;
      }
  }
});

watch(() => props.viewState, () => {
  if (props.visible) {
      syncCamera();
  }
}, { deep: true });

watch(() => props.features, () => {
    if (props.visible) {
        updateFeatures();
    }
}, { deep: true });
</script>

<style scoped>
.cesium-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10; /* Above OL map (OL is z-index 0 usually, but check MapView) */
  background: black;
}

/* Override Cesium widgets style if needed */
:deep(.cesium-viewer-bottom) {
    display: none; /* Hide credits for cleaner view (dev only) */
}
</style>
