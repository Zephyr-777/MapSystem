from __future__ import annotations

import json
import zipfile
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import fiona
from shapely.geometry import mapping, shape


HEIHE_GRASSLAND_DATASET_ID = "heihe-grassland-1988"
HEIHE_GRASSLAND_ARCHIVE_NAME = "heihe_grassland_1988_raw_dataset.zip"
HEIHE_GRASSLAND_ROOT = (
    Path("/Volumes/固态硬盘/毕设文件")
    / "黑河流域1:100万草场分布数据集（1988）"
)
HEIHE_GRASSLAND_SHP = (
    HEIHE_GRASSLAND_ROOT
    / "Heihe_Grassland"
    / "Geographic"
    / "Heihe_Grass_Distribution.shp"
)


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@lru_cache(maxsize=1)
def _load_features() -> tuple[list[dict[str, Any]], tuple[float, float, float, float], dict[str, Any]]:
    if not HEIHE_GRASSLAND_SHP.exists():
        raise FileNotFoundError(f"Heihe grassland shapefile not found: {HEIHE_GRASSLAND_SHP}")

    features: list[dict[str, Any]] = []
    type_counts: dict[str, int] = {}

    with fiona.open(HEIHE_GRASSLAND_SHP) as src:
        bbox = tuple(float(v) for v in src.bounds)
        metadata = {
            "dataset_id": HEIHE_GRASSLAND_DATASET_ID,
            "dataset_name": "黑河流域1:100万草场分布数据集（1988）",
            "time_range": "1988",
            "scale": "1:100万",
            "source_format": "Shapefile",
            "record_count": len(src),
            "crs": src.crs.to_string() if src.crs else "EPSG:4326",
        }

        for index, feature in enumerate(src, start=1):
            geometry = feature.get("geometry")
            if not geometry:
                continue

            properties = {key: _json_safe(value) for key, value in dict(feature["properties"]).items()}
            grass_type = properties.get("TYPE") or "未分类"
            main_type = properties.get("MAINTYPE") or "草场分布"
            type_counts[str(grass_type)] = type_counts.get(str(grass_type), 0) + 1

            geom = shape(geometry)
            minx, miny, maxx, maxy = geom.bounds
            point = geom.representative_point()
            feature_id = properties.get("GRASSF_ID") or properties.get("POLY_") or index
            feature_name = f"{grass_type} #{feature_id}"

            features.append(
                {
                    "id": str(feature_id),
                    "geometry": mapping(geom),
                    "point_geometry": mapping(point),
                    "properties": {
                        **properties,
                        "id": feature_id,
                        "dataset_id": HEIHE_GRASSLAND_DATASET_ID,
                        "name": feature_name,
                        "site_name": feature_name,
                        "type": "黑河草场分布",
                        "sub_type": "HeiheGrassland",
                        "asset_family": "vector",
                        "render_mode": "map-overlay",
                        "source": "heihe-grassland",
                        "downloadable": True,
                        "download_url": "/api/download/heihe-grassland",
                        "uploadTime": "1988",
                        "center_x": point.x,
                        "center_y": point.y,
                        "extent": [minx, miny, maxx, maxy],
                        "bbox": [minx, miny, maxx, maxy],
                        "srid": 4326,
                        "description": f"{main_type}，类型：{grass_type}",
                        "metadata": {
                            "dataset_name": metadata["dataset_name"],
                            "time_range": metadata["time_range"],
                            "scale": metadata["scale"],
                            "main_type": main_type,
                            "grass_type": grass_type,
                            "subtype": properties.get("SUBTYPE"),
                            "geocode": properties.get("GEOCODE"),
                            "class": properties.get("CLASS"),
                            "area": properties.get("AREA"),
                            "perimeter": properties.get("PERIMETER"),
                        },
                    },
                }
            )

    metadata["type_counts"] = type_counts
    return features, bbox, metadata


def build_heihe_grassland_geojson(mode: str = "polygons") -> dict[str, Any]:
    normalized_mode = (mode or "polygons").strip().lower()
    if normalized_mode not in {"polygons", "points"}:
        raise ValueError("mode must be either 'polygons' or 'points'")

    features, bbox, metadata = _load_features()
    geojson_features = []
    for feature in features:
        properties = feature["properties"]
        if normalized_mode == "points":
            geometry = feature["point_geometry"]
            properties = {
                **properties,
                "sub_type": "HeiheGrasslandIndexPoint",
                "type": "黑河草场分布索引点",
            }
        else:
            geometry = feature["geometry"]

        geojson_features.append(
            {
                "type": "Feature",
                "id": feature["id"],
                "geometry": json.loads(json.dumps(geometry)),
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "dataset_id": HEIHE_GRASSLAND_DATASET_ID,
        "mode": normalized_mode,
        "bbox": list(bbox),
        "metadata": metadata,
        "features": geojson_features,
    }


def ensure_heihe_grassland_archive(output_dir: Path) -> Path:
    if not HEIHE_GRASSLAND_ROOT.exists():
        raise FileNotFoundError(f"Heihe grassland dataset root not found: {HEIHE_GRASSLAND_ROOT}")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / HEIHE_GRASSLAND_ARCHIVE_NAME
    latest_source_mtime = max(path.stat().st_mtime for path in HEIHE_GRASSLAND_ROOT.rglob("*") if path.is_file())

    if archive_path.exists() and archive_path.stat().st_mtime >= latest_source_mtime:
        return archive_path

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in HEIHE_GRASSLAND_ROOT.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(HEIHE_GRASSLAND_ROOT.parent))

    return archive_path
