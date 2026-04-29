from __future__ import annotations

import json
import math
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import fiona
from shapely.geometry import mapping, shape


CENTRAL_ASIA_DESERT_DATASET_ID = "central-asia-desert-urban-2012-2016"
CENTRAL_ASIA_DESERT_ARCHIVE_NAME = "central_asia_desert_urban_2012_2016_raw_dataset.zip"
CENTRAL_ASIA_DESERT_ROOT_CANDIDATES = (
    Path("/Volumes/固态硬盘/毕设文件/中亚沙漠油气田与城镇分布（2012-2016）"),
    Path("/Volumes/固态硬盘/中亚沙漠油气田与城镇分布（2012-2016）"),
)
CENTRAL_ASIA_DESERT_ROOT = next(
    (path for path in CENTRAL_ASIA_DESERT_ROOT_CANDIDATES if path.exists()),
    CENTRAL_ASIA_DESERT_ROOT_CANDIDATES[0],
)
CENTRAL_ASIA_COUNTRIES_SHP = CENTRAL_ASIA_DESERT_ROOT / "countries.shp"
CENTRAL_ASIA_URBAN_SHP = CENTRAL_ASIA_DESERT_ROOT / "midasi_urban.shp"
CENTRAL_ASIA_DATASET_NAME = "中亚沙漠油气田与城镇分布（2012-2016）"


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


@lru_cache(maxsize=1)
def _get_urban_metadata() -> dict[str, Any]:
    if not CENTRAL_ASIA_URBAN_SHP.exists():
        raise FileNotFoundError(f"Central Asia urban shapefile not found: {CENTRAL_ASIA_URBAN_SHP}")

    with fiona.open(CENTRAL_ASIA_URBAN_SHP) as src:
        bbox = tuple(float(v) for v in src.bounds)
        return {
            "dataset_id": CENTRAL_ASIA_DESERT_DATASET_ID,
            "dataset_name": CENTRAL_ASIA_DATASET_NAME,
            "time_range": "2012-2016",
            "source_format": "Shapefile",
            "record_count": len(src),
            "crs": src.crs.to_string() if src.crs else "EPSG:4326",
            "bbox": list(bbox),
            "layers": ["countries", "urban"],
        }


@lru_cache(maxsize=1)
def _get_country_features() -> tuple[list[dict[str, Any]], tuple[float, float, float, float], list[str]]:
    if not CENTRAL_ASIA_COUNTRIES_SHP.exists():
        raise FileNotFoundError(f"Central Asia countries shapefile not found: {CENTRAL_ASIA_COUNTRIES_SHP}")

    features: list[dict[str, Any]] = []
    country_names: list[str] = []
    with fiona.open(CENTRAL_ASIA_COUNTRIES_SHP) as src:
        bbox = tuple(float(v) for v in src.bounds)
        for index, feature in enumerate(src, start=1):
            geometry = feature.get("geometry")
            if not geometry:
                continue

            properties = {key: _json_safe(value) for key, value in dict(feature["properties"]).items()}
            geom = shape(geometry)
            minx, miny, maxx, maxy = geom.bounds
            center = geom.representative_point()
            name = str(properties.get("FIRST_OWNE") or f"国家边界 {index}")
            country_names.append(name)
            features.append(
                {
                    "type": "Feature",
                    "id": index,
                    "geometry": json.loads(json.dumps(mapping(geom))),
                    "properties": {
                        **properties,
                        "id": index,
                        "dataset_id": CENTRAL_ASIA_DESERT_DATASET_ID,
                        "name": name,
                        "site_name": name,
                        "type": "中亚国家边界",
                        "sub_type": "CentralAsiaCountryBoundary",
                        "asset_family": "vector",
                        "render_mode": "map-overlay",
                        "source": "central-asia-desert",
                        "downloadable": True,
                        "download_url": "/api/download/central-asia-desert",
                        "uploadTime": "2012-2016",
                        "center_x": center.x,
                        "center_y": center.y,
                        "extent": [minx, miny, maxx, maxy],
                        "bbox": [minx, miny, maxx, maxy],
                        "srid": 4326,
                        "description": f"{name} 边界范围，用于中亚专题区域定位。",
                        "metadata": {
                            "dataset_name": CENTRAL_ASIA_DATASET_NAME,
                            "time_range": "2012-2016",
                            "layer_name": "国家边界",
                            "feature_name": name,
                        },
                    },
                }
            )

    return features, bbox, country_names


def _iter_urban_features(
    bbox: tuple[float, float, float, float] | None = None,
) -> Iterable[dict[str, Any]]:
    if not CENTRAL_ASIA_URBAN_SHP.exists():
        raise FileNotFoundError(f"Central Asia urban shapefile not found: {CENTRAL_ASIA_URBAN_SHP}")

    with fiona.open(CENTRAL_ASIA_URBAN_SHP) as src:
        iterator = src.filter(bbox=bbox) if bbox else src
        for index, feature in enumerate(iterator, start=1):
            geometry = feature.get("geometry")
            if not geometry:
                continue

            properties = {key: _json_safe(value) for key, value in dict(feature["properties"]).items()}
            geom = shape(geometry)
            minx, miny, maxx, maxy = geom.bounds
            center = geom.representative_point()
            feature_id = properties.get("Id") or index
            try:
                feature_id = int(feature_id)
            except (TypeError, ValueError):
                feature_id = index

            yield {
                "id": feature_id,
                "geometry": geom,
                "point_geometry": center,
                "properties": {
                    **properties,
                    "id": feature_id,
                    "dataset_id": CENTRAL_ASIA_DESERT_DATASET_ID,
                    "name": f"中亚城镇斑块 #{feature_id}",
                    "site_name": f"中亚城镇斑块 #{feature_id}",
                    "type": "中亚城镇分布",
                    "asset_family": "vector",
                    "render_mode": "map-overlay",
                    "source": "central-asia-desert",
                    "downloadable": True,
                    "download_url": "/api/download/central-asia-desert",
                    "uploadTime": "2012-2016",
                    "center_x": center.x,
                    "center_y": center.y,
                    "extent": [minx, miny, maxx, maxy],
                    "bbox": [minx, miny, maxx, maxy],
                    "srid": 4326,
                    "description": "中亚地区城镇/聚落面数据，可在放大后查看面分布与索引点。",
                    "metadata": {
                        "dataset_name": CENTRAL_ASIA_DATASET_NAME,
                        "time_range": "2012-2016",
                        "layer_name": "城镇分布",
                        "source_layer": "midasi_urban",
                        "gridcode": properties.get("gridcode"),
                    },
                },
            }


def build_central_asia_desert_geojson(
    mode: str = "urban-points",
    bbox: tuple[float, float, float, float] | None = None,
) -> dict[str, Any]:
    normalized_mode = (mode or "urban-points").strip().lower()
    valid_modes = {"countries", "urban-polygons", "urban-points"}
    if normalized_mode not in valid_modes:
        raise ValueError("mode must be one of countries, urban-polygons, urban-points")

    urban_metadata = _get_urban_metadata()

    if normalized_mode == "countries":
        country_features, country_bbox, country_names = _get_country_features()
        metadata = {
            **urban_metadata,
            "layer_name": "国家边界",
            "country_names": country_names,
            "country_count": len(country_features),
            "returned_count": len(country_features),
        }
        return {
            "type": "FeatureCollection",
            "dataset_id": CENTRAL_ASIA_DESERT_DATASET_ID,
            "mode": normalized_mode,
            "bbox": list(country_bbox),
            "metadata": metadata,
            "features": country_features,
        }

    features = []
    returned_count = 0
    for item in _iter_urban_features(bbox=bbox):
        returned_count += 1
        if normalized_mode == "urban-points":
            geometry = mapping(item["point_geometry"])
            properties = {
                **item["properties"],
                "sub_type": "CentralAsiaUrbanIndexPoint",
                "type": "中亚城镇索引点",
            }
        else:
            geometry = mapping(item["geometry"])
            properties = {
                **item["properties"],
                "sub_type": "CentralAsiaUrbanPolygon",
            }

        features.append(
            {
                "type": "Feature",
                "id": item["id"],
                "geometry": json.loads(json.dumps(geometry)),
                "properties": properties,
            }
        )

    metadata = {
        **urban_metadata,
        "layer_name": "城镇分布",
        "returned_count": returned_count,
        "bbox_filter_applied": bbox is not None,
        "bbox_filter": list(bbox) if bbox else None,
        "country_count": len(_get_country_features()[0]),
    }

    return {
        "type": "FeatureCollection",
        "dataset_id": CENTRAL_ASIA_DESERT_DATASET_ID,
        "mode": normalized_mode,
        "bbox": urban_metadata["bbox"],
        "metadata": metadata,
        "features": features,
    }


def estimate_point_density_bucket(returned_count: int) -> str:
    if returned_count >= 20000:
        return "very-dense"
    if returned_count >= 5000:
        return "dense"
    if returned_count >= 1000:
        return "moderate"
    return "sparse"


def normalize_bbox_for_cache_key(
    bbox: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    return tuple(math.floor(value * 1000) / 1000 for value in bbox)


def ensure_central_asia_desert_archive(output_dir: Path) -> Path:
    if not CENTRAL_ASIA_DESERT_ROOT.exists():
        raise FileNotFoundError(f"Central Asia dataset root not found: {CENTRAL_ASIA_DESERT_ROOT}")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / CENTRAL_ASIA_DESERT_ARCHIVE_NAME
    latest_source_mtime = max(path.stat().st_mtime for path in CENTRAL_ASIA_DESERT_ROOT.rglob("*") if path.is_file())

    if archive_path.exists() and archive_path.stat().st_mtime >= latest_source_mtime:
        return archive_path

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in CENTRAL_ASIA_DESERT_ROOT.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(CENTRAL_ASIA_DESERT_ROOT.parent))

    return archive_path
