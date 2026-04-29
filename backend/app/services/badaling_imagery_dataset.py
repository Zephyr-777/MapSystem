from __future__ import annotations

import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import rasterio


BADALING_IMAGERY_DATASET_ID = "badaling-town-imagery"
BADALING_IMAGERY_ARCHIVE_NAME = "badaling_town_imagery_raw_dataset.zip"
BADALING_IMAGERY_ROOT = Path("/Volumes/固态硬盘/毕设文件/八达岭镇")
BADALING_TILE_IDS = ("11_842_142", "11_843_142")
BADALING_LEVELS = (11, 12, 13, 14, 15, 16)
BADALING_DATASET_NAME = "八达岭镇分级遥感影像"
BADALING_TIME_RANGE = "原始影像"


def _level_zoom_range(level: int) -> tuple[float, float | None]:
    level_index = BADALING_LEVELS.index(level)
    min_zoom = 8 + level_index
    if level == BADALING_LEVELS[-1]:
        return float(min_zoom), None
    return float(min_zoom), float(min_zoom + 1)


def get_badaling_tile_path(level: int, tile_id: str) -> Path:
    if level not in BADALING_LEVELS:
        raise ValueError(f"Unsupported Badaling level: {level}")
    if tile_id not in BADALING_TILE_IDS:
        raise ValueError(f"Unsupported Badaling tile: {tile_id}")

    tile_path = BADALING_IMAGERY_ROOT / f"{tile_id}_大图" / f"L{level}" / f"{tile_id}.tif"
    if not tile_path.exists():
        raise FileNotFoundError(f"Badaling tile not found: {tile_path}")
    return tile_path


def _tile_metadata(level: int, tile_id: str) -> dict[str, Any]:
    tile_path = get_badaling_tile_path(level, tile_id)
    with rasterio.open(tile_path) as src:
        bounds = src.bounds
        srid = src.crs.to_epsg() if src.crs else 4326
        min_zoom, max_zoom = _level_zoom_range(level)
        return {
            "tile_id": tile_id,
            "level": level,
            "name": f"{tile_id} L{level}",
            "path": str(tile_path),
            "extent": [float(bounds.left), float(bounds.bottom), float(bounds.right), float(bounds.top)],
            "center_x": float((bounds.left + bounds.right) / 2),
            "center_y": float((bounds.bottom + bounds.top) / 2),
            "srid": srid or 4326,
            "band_count": src.count,
            "dtype": src.dtypes[0] if src.dtypes else None,
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "raster_url": f"/api/geodata/badaling-imagery-raster/{level}/{tile_id}",
        }


@lru_cache(maxsize=1)
def build_badaling_imagery_dataset_response() -> dict[str, Any]:
    tiles_by_level: list[dict[str, Any]] = []
    overall_bbox: list[float] | None = None

    for level in BADALING_LEVELS:
        level_tiles = [_tile_metadata(level, tile_id) for tile_id in BADALING_TILE_IDS]
        level_bbox = [
            min(tile["extent"][0] for tile in level_tiles),
            min(tile["extent"][1] for tile in level_tiles),
            max(tile["extent"][2] for tile in level_tiles),
            max(tile["extent"][3] for tile in level_tiles),
        ]
        min_zoom, max_zoom = _level_zoom_range(level)
        tiles_by_level.append(
            {
                "level": level,
                "min_zoom": min_zoom,
                "max_zoom": max_zoom,
                "bbox": level_bbox,
                "tiles": level_tiles,
            }
        )

        if overall_bbox is None:
            overall_bbox = level_bbox
        else:
            overall_bbox = [
                min(overall_bbox[0], level_bbox[0]),
                min(overall_bbox[1], level_bbox[1]),
                max(overall_bbox[2], level_bbox[2]),
                max(overall_bbox[3], level_bbox[3]),
            ]

    if overall_bbox is None:
        raise FileNotFoundError("Badaling imagery dataset is empty")

    return {
        "dataset_id": BADALING_IMAGERY_DATASET_ID,
        "name": BADALING_DATASET_NAME,
        "description": "八达岭镇双分幅 RGB GeoTIFF 影像，按 L11-L16 多级分辨率随地图缩放自动切换显示。",
        "time_range": BADALING_TIME_RANGE,
        "srid": 4326,
        "bbox": overall_bbox,
        "center_x": (overall_bbox[0] + overall_bbox[2]) / 2,
        "center_y": (overall_bbox[1] + overall_bbox[3]) / 2,
        "min_zoom": tiles_by_level[0]["min_zoom"],
        "max_zoom": tiles_by_level[-1]["max_zoom"],
        "levels": tiles_by_level,
        "tile_count": len(BADALING_TILE_IDS),
        "download_url": "/api/download/badaling-imagery",
        "metadata": {
            "dataset_name": BADALING_DATASET_NAME,
            "time_range": BADALING_TIME_RANGE,
            "format": "GeoTIFF Pyramid",
            "level_range": "L11-L16",
            "tile_ids": list(BADALING_TILE_IDS),
            "tile_count": len(BADALING_TILE_IDS),
            "level_count": len(BADALING_LEVELS),
        },
    }


def ensure_badaling_imagery_archive(output_dir: Path) -> Path:
    if not BADALING_IMAGERY_ROOT.exists():
        raise FileNotFoundError(f"Badaling imagery dataset root not found: {BADALING_IMAGERY_ROOT}")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / BADALING_IMAGERY_ARCHIVE_NAME
    latest_source_mtime = max(path.stat().st_mtime for path in BADALING_IMAGERY_ROOT.rglob("*") if path.is_file())

    if archive_path.exists() and archive_path.stat().st_mtime >= latest_source_mtime:
        return archive_path

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in BADALING_IMAGERY_ROOT.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(BADALING_IMAGERY_ROOT.parent))

    return archive_path
