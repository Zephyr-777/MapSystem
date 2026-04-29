import { fromLonLat, toLonLat, transformExtent } from 'ol/proj'
import VectorSource from 'ol/source/Vector'
import VectorLayer from 'ol/layer/Vector'
import { Style, Fill, Stroke, Circle as CircleStyle } from 'ol/style'
import Map from 'ol/Map'
import Feature from 'ol/Feature'
import { Draw, DragBox } from 'ol/interaction'
import Overlay from 'ol/Overlay'
import LineString from 'ol/geom/LineString'
import Polygon from 'ol/geom/Polygon'
import { getArea, getLength } from 'ol/sphere'
import { unByKey } from 'ol/Observable'

export type Coord = [number, number]
export type Extent = [number, number, number, number]

export function toMapCoords(coord: Coord, srid = 4326): Coord {
  if (srid === 3857) return coord
  return fromLonLat(coord) as Coord
}

export function toWGS84(coord: Coord, srid = 3857): Coord {
  if (srid === 4326) return coord
  return toLonLat(coord) as Coord
}

export function extentToWGS84(extent: Extent, sourceSrid = 3857): Extent {
  if (sourceSrid === 4326) return extent
  return transformExtent(extent, `EPSG:${sourceSrid}`, 'EPSG:4326') as Extent
}

export function createHighlightLayer() {
  const source = new VectorSource()
  const layer = new VectorLayer({
    source,
    zIndex: 9999,
    style: new Style({
      image: new CircleStyle({
        radius: 6,
        fill: new Fill({ color: '#FFFF00' }),
        stroke: new Stroke({ color: '#FF0000', width: 2 })
      }),
      zIndex: Infinity
    })
  })

  return { source, layer }
}

export function createBufferLayer() {
  const source = new VectorSource()
  const layer = new VectorLayer({
    source,
    zIndex: 999,
    style: new Style({
      fill: new Fill({
        color: 'rgba(64, 158, 255, 0.2)'
      }),
      stroke: new Stroke({
        color: '#409EFF',
        width: 2,
        lineDash: [10, 10]
      })
    })
  })

  return { source, layer }
}

interface SelectionManagerOptions<T> {
  map: Map
  source: VectorSource
  mapFeatureToItem: (feature: Feature) => T
  onSelect: (items: T[]) => void
  onEmpty?: () => void
}

export class MapSelectionManager<T = any> {
  private map: Map
  private source: VectorSource
  private mapFeatureToItem: (feature: Feature) => T
  private onSelect: (items: T[]) => void
  private onEmpty?: () => void
  private dragBox: DragBox | null = null

  constructor(options: SelectionManagerOptions<T>) {
    this.map = options.map
    this.source = options.source
    this.mapFeatureToItem = options.mapFeatureToItem
    this.onSelect = options.onSelect
    this.onEmpty = options.onEmpty
  }

  enableDragBox() {
    if (this.dragBox) return

    this.dragBox = new DragBox({ className: 'ol-dragbox' })
    this.dragBox.on('boxstart', () => this.onSelect([]))
    this.dragBox.on('boxend', () => {
      const extent = this.dragBox!.getGeometry().getExtent()
      const features = this.source.getFeaturesInExtent(extent)
      const selected = features.map((f) => this.mapFeatureToItem(f))

      if (selected.length > 0) {
        this.onSelect(selected)
      } else if (this.onEmpty) {
        this.onEmpty()
      } else {
        this.onSelect([])
      }
    })

    this.map.addInteraction(this.dragBox)
  }

  disableDragBox() {
    if (!this.dragBox) return
    this.map.removeInteraction(this.dragBox)
    this.dragBox = null
  }

  destroy() {
    this.disableDragBox()
  }
}

interface MeasureManagerOptions {
  map: Map
}

export class MeasureManager {
  private map: Map
  private source: VectorSource
  private layer: VectorLayer<VectorSource>
  private draw: Draw | null = null
  private measureOverlay: Overlay | null = null
  private helpOverlay: Overlay | null = null
  private sketch: Feature | null = null
  private listener: any

  constructor(options: MeasureManagerOptions) {
    this.map = options.map
    this.source = new VectorSource()
    this.layer = new VectorLayer({
      source: this.source,
      style: new Style({
        fill: new Fill({ color: 'rgba(255, 255, 255, 0.2)' }),
        stroke: new Stroke({ color: '#ffcc33', width: 2 }),
        image: new CircleStyle({
          radius: 7,
          fill: new Fill({ color: '#ffcc33' })
        })
      }),
      zIndex: 1000
    })

    this.layer.set('title', '测量绘制')
    this.layer.set('type', 'overlay')
    this.map.addLayer(this.layer)
    this.map.on('pointermove', this.handlePointerMove)
  }

  startLineMeasure() {
    this.startMeasure('LineString')
  }

  startAreaMeasure() {
    this.startMeasure('Polygon')
  }

  stopMeasure() {
    if (this.draw) {
      this.map.removeInteraction(this.draw)
      this.draw = null
    }
    this.disposeOverlays()
    if (this.listener) {
      unByKey(this.listener)
      this.listener = null
    }
    this.sketch = null
  }

  clearMeasurements() {
    this.source.clear()
  }

  destroy() {
    this.stopMeasure()
    this.map.un('pointermove', this.handlePointerMove)
    this.map.removeLayer(this.layer)
  }

  private startMeasure(type: 'LineString' | 'Polygon') {
    this.stopMeasure()
    this.createMeasureOverlay()
    this.createHelpOverlay()

    this.draw = new Draw({
      source: this.source,
      type,
      style: new Style({
        fill: new Fill({ color: 'rgba(255, 255, 255, 0.2)' }),
        stroke: new Stroke({
          color: 'rgba(0, 0, 0, 0.5)',
          lineDash: [10, 10],
          width: 2
        }),
        image: new CircleStyle({
          radius: 5,
          stroke: new Stroke({ color: 'rgba(0, 0, 0, 0.7)' }),
          fill: new Fill({ color: 'rgba(255, 255, 255, 0.2)' })
        })
      })
    })

    this.draw.on('drawstart', (evt) => {
      this.sketch = evt.feature
      let tooltipCoord = (evt as any).coordinate
      this.listener = this.sketch.getGeometry()?.on('change', (changeEvt: any) => {
        const geom = changeEvt.target
        let output = ''
        if (geom instanceof Polygon) {
          output = this.formatArea(geom)
          tooltipCoord = geom.getInteriorPoint().getCoordinates()
        } else if (geom instanceof LineString) {
          output = this.formatLength(geom)
          tooltipCoord = geom.getLastCoordinate()
        }

        if (this.measureOverlay?.getElement()) {
          this.measureOverlay.getElement()!.innerHTML = output
        }
        this.measureOverlay?.setPosition(tooltipCoord)
      })
    })

    this.draw.on('drawend', () => {
      if (this.measureOverlay?.getElement()) {
        this.measureOverlay.getElement()!.className = 'measure-tooltip ol-tooltip ol-tooltip-static'
      }
      this.measureOverlay?.setOffset([0, -7])
      this.sketch = null
      if (this.listener) {
        unByKey(this.listener)
        this.listener = null
      }
      this.createMeasureOverlay()
    })

    this.map.addInteraction(this.draw)
  }

  private handlePointerMove = (evt: any) => {
    if (evt.dragging || !this.helpOverlay?.getElement()) return
    let helpText = '单击开始绘制'
    if (this.sketch) {
      const geom = this.sketch.getGeometry()
      if (geom instanceof Polygon) {
        helpText = '单击继续绘制多边形，双击结束'
      } else if (geom instanceof LineString) {
        helpText = '单击继续绘制线段，双击结束'
      }
    }
    this.helpOverlay.getElement()!.innerHTML = helpText
    this.helpOverlay.setPosition(evt.coordinate)
  }

  private createMeasureOverlay() {
    const el = document.createElement('div')
    el.className = 'measure-tooltip ol-tooltip ol-tooltip-measure'
    this.measureOverlay = new Overlay({
      element: el,
      offset: [0, -15],
      positioning: 'bottom-center',
      stopEvent: false,
      insertFirst: false
    })
    this.map.addOverlay(this.measureOverlay)
  }

  private createHelpOverlay() {
    const el = document.createElement('div')
    el.className = 'measure-tooltip ol-tooltip'
    this.helpOverlay = new Overlay({
      element: el,
      offset: [15, 0],
      positioning: 'center-left'
    })
    this.map.addOverlay(this.helpOverlay)
  }

  private disposeOverlays() {
    if (this.measureOverlay) {
      this.map.removeOverlay(this.measureOverlay)
      this.measureOverlay = null
    }
    if (this.helpOverlay) {
      this.map.removeOverlay(this.helpOverlay)
      this.helpOverlay = null
    }
  }

  private formatLength(line: LineString) {
    const length = getLength(line)
    if (length > 100) return `${Math.round((length / 1000) * 100) / 100} km`
    return `${Math.round(length * 100) / 100} m`
  }

  private formatArea(polygon: Polygon) {
    const area = getArea(polygon)
    if (area > 10000) return `${Math.round((area / 1000000) * 100) / 100} km²`
    return `${Math.round(area * 100) / 100} m²`
  }
}
