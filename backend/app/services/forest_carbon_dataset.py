from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal


FOREST_CARBON_DATASET_ID = "china-forest-carbon-2002-2021"
FOREST_CARBON_ROOT = (
    Path("/Volumes/固态硬盘/毕设文件")
    / "中国森林地上和地下植被碳储量数据集（2002~2021）"
)
FOREST_CARBON_DATA_DIR = FOREST_CARBON_ROOT / "DATA"
FOREST_CARBON_YEARS = list(range(2002, 2022))
FOREST_CARBON_METRICS = {
    "AGBC": {
        "label": "地上植被碳储量",
        "directory": "AGBC",
        "unit": "tC/ha",
        "description": "Aboveground forest biomass carbon",
    },
    "BGBC": {
        "label": "地下植被碳储量",
        "directory": "BGBC",
        "unit": "tC/ha",
        "description": "Belowground forest biomass carbon",
    },
}


def normalize_metric(metric: str) -> Literal["AGBC", "BGBC"]:
    normalized = (metric or "AGBC").strip().upper()
    if normalized not in FOREST_CARBON_METRICS:
        raise ValueError("metric must be AGBC or BGBC")
    return normalized  # type: ignore[return-value]


def normalize_year(year: int | str) -> int:
    normalized = int(year)
    if normalized not in FOREST_CARBON_YEARS:
        raise ValueError("year must be between 2002 and 2021")
    return normalized


def get_forest_carbon_raster_path(metric: str, year: int | str) -> Path:
    normalized_metric = normalize_metric(metric)
    normalized_year = normalize_year(year)
    metric_info = FOREST_CARBON_METRICS[normalized_metric]
    return FOREST_CARBON_DATA_DIR / metric_info["directory"] / f"{normalized_metric}Y{normalized_year}.tif"


@lru_cache(maxsize=64)
def build_forest_carbon_overlay_response(metric: str = "AGBC", year: int = 2021) -> dict[str, Any]:
    import rasterio

    normalized_metric = normalize_metric(metric)
    normalized_year = normalize_year(year)
    tif_path = get_forest_carbon_raster_path(normalized_metric, normalized_year)
    if not tif_path.exists():
        raise FileNotFoundError(f"Forest carbon raster not found: {tif_path}")

    metric_info = FOREST_CARBON_METRICS[normalized_metric]
    with rasterio.open(tif_path) as src:
        bounds = src.bounds
        stats = src.statistics(1, approx=True, clear_cache=False)
        nodata = float(src.nodata) if src.nodata is not None else None
        srid = src.crs.to_epsg() if src.crs else 4326

    extent = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    return {
        "id": FOREST_CARBON_DATASET_ID,
        "dataset_id": FOREST_CARBON_DATASET_ID,
        "name": f"中国森林{metric_info['label']}（{normalized_year}）",
        "metric": normalized_metric,
        "metric_label": metric_info["label"],
        "year": normalized_year,
        "years": FOREST_CARBON_YEARS,
        "metrics": [
            {
                "id": key,
                "label": value["label"],
                "unit": value["unit"],
                "description": value["description"],
            }
            for key, value in FOREST_CARBON_METRICS.items()
        ],
        "extent": extent,
        "srid": srid or 4326,
        "min_zoom": 4,
        "opacity": 72,
        "center_x": (bounds.left + bounds.right) / 2,
        "center_y": (bounds.bottom + bounds.top) / 2,
        "description": "中国森林地上和地下植被碳储量数据集（2002-2021），GeoTIFF 时间序列栅格。",
        "source_path": str(tif_path),
        "raster_url": f"/api/geodata/forest-carbon-raster/{normalized_metric}/{normalized_year}",
        "download_url": f"/api/download/forest-carbon/{normalized_metric}/{normalized_year}",
        "band_count": 1,
        "dtype": "float32",
        "nodata": nodata,
        "raster_min": float(stats.min),
        "raster_max": float(stats.max),
        "unit": metric_info["unit"],
        "time_range": "2002-2021",
        "metadata": {
            "dataset_name": "中国森林地上和地下植被碳储量数据集（2002-2021）",
            "metric": normalized_metric,
            "metric_label": metric_info["label"],
            "year": normalized_year,
            "unit": metric_info["unit"],
            "time_range": "2002-2021",
            "resolution": "0.01°",
            "forest_mask": str(FOREST_CARBON_DATA_DIR / "FORESTLAND.tif"),
        },
    }
