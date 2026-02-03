import { ref, shallowRef } from 'vue';
import Map from 'ol/Map';
import View from 'ol/View';
import { fromLonLat } from 'ol/proj';
import { ScaleLine, defaults as defaultControls } from 'ol/control';
import type { MapOptions } from '@/views/map/types/map';

const mapInstance = shallowRef<Map | null>(null);

export default function useMapCore() {
  const mapReady = ref(false);

  const initMap = async (target: HTMLElement, options: MapOptions): Promise<Map> => {
    // If there's an existing map instance, we should probably dispose it or at least reset target
    if (mapInstance.value) {
      mapInstance.value.setTarget(undefined);
    }

    return new Promise((resolve, reject) => {
      try {
        const view = new View({
          center: options.center ? fromLonLat(options.center) : fromLonLat([116.3974, 39.9093]),
          zoom: options.zoom || 10,
          maxZoom: options.maxZoom || 18,
          constrainResolution: true,
          smoothResolutionConstraint: true,
        });

        const map = new Map({
          target: target,
          layers: [], 
          controls: defaultControls({
            rotate: true,
            zoom: false,
            attribution: false,
          }).extend([
            new ScaleLine({
              units: 'metric',
              bar: true,
              steps: 4,
              text: true,
              minWidth: 140,
              className: 'custom-scale-line',
            }),
          ]),
          view: view,
        });

        mapInstance.value = map;
        mapReady.value = true;
        resolve(map);
      } catch (e) {
        console.error('Error creating map instance:', e);
        reject(e);
      }
    });
  };

  const getMap = (): Map | null => {
    return mapInstance.value;
  };

  // GCJ02 to WGS84 (Rough approximation for demo, or import a library like coordtransform if strictly needed. 
  // For this task, I'll implement the standard algorithm or a placeholder if complex math is too long, 
  // but standard algorithm is preferred).
  const PI = 3.1415926535897932384626;
  const a = 6378245.0;
  const ee = 0.00669342162296594323;

  const transformLat = (x: number, y: number) => {
    let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
    ret += (20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0 / 3.0;
    ret += (20.0 * Math.sin(y * PI) + 40.0 * Math.sin(y / 3.0 * PI)) * 2.0 / 3.0;
    ret += (160.0 * Math.sin(y / 12.0 * PI) + 320 * Math.sin(y * PI / 30.0)) * 2.0 / 3.0;
    return ret;
  };

  const transformLon = (x: number, y: number) => {
    let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
    ret += (20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0 / 3.0;
    ret += (20.0 * Math.sin(x * PI) + 40.0 * Math.sin(x / 3.0 * PI)) * 2.0 / 3.0;
    ret += (150.0 * Math.sin(x / 12.0 * PI) + 300.0 * Math.sin(x / 30.0 * PI)) * 2.0 / 3.0;
    return ret;
  };

  const transformGCJ02ToWGS84 = (coord: number[]): number[] => {
    const lng = coord[0];
    const lat = coord[1];
    if (outOfChina(lng, lat)) {
      return [lng, lat];
    }
    let dlat = transformLat(lng - 105.0, lat - 35.0);
    let dlng = transformLon(lng - 105.0, lat - 35.0);
    const radlat = lat / 180.0 * PI;
    const magic = Math.sin(radlat);
    const magic2 = 1 - ee * magic * magic;
    const sqrtmagic = Math.sqrt(magic2);
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic2 * sqrtmagic) * PI);
    dlng = (dlng * 180.0) / (a / sqrtmagic * Math.cos(radlat) * PI);
    const mglat = lat + dlat;
    const mglng = lng + dlng;
    return [lng * 2 - mglng, lat * 2 - mglat];
  };

  const transformWGS84ToGCJ02 = (coord: number[]): number[] => {
    const lng = coord[0];
    const lat = coord[1];
    if (outOfChina(lng, lat)) {
      return [lng, lat];
    }
    let dlat = transformLat(lng - 105.0, lat - 35.0);
    let dlng = transformLon(lng - 105.0, lat - 35.0);
    const radlat = lat / 180.0 * PI;
    const magic = Math.sin(radlat);
    const magic2 = 1 - ee * magic * magic;
    const sqrtmagic = Math.sqrt(magic2);
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic2 * sqrtmagic) * PI);
    dlng = (dlng * 180.0) / (a / sqrtmagic * Math.cos(radlat) * PI);
    const mglat = lat + dlat;
    const mglng = lng + dlng;
    return [mglng, mglat];
  };

  const outOfChina = (lng: number, lat: number) => {
    return (lng < 72.004 || lng > 137.8347) || ((lat < 0.8293 || lat > 55.8271) || false);
  };

  return {
    initMap,
    getMap,
    mapReady,
    transformGCJ02ToWGS84,
    transformWGS84ToGCJ02,
  };
}
