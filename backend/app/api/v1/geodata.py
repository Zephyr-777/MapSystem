from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Union, Optional
import shutil
from pathlib import Path
from urllib.parse import quote
import io
import zipfile
import mimetypes
import json
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.security import role_checker
from app.api.v1.auth import get_current_user
from app.models.geo_asset import GeoAsset
from app.services.spatial_service import SpatialService
from app.services.parser_service import ParserService
from app.services.netcdf_processor import NetCDFProcessor
from app.services.ai_classifier import AIGeodataClassifier
from app.services.smart_search import CatalogSearchItem, SemanticSearchEngine
from app.schemas import (
    GeoDataListResponse,
    GeoDataItem,
    LocalRasterOverlayResponse,
    SmartSearchRequest,
    SmartSearchResponse,
)
from utils.optimize_tif import create_web_preview, optimize_asset_preview
from app.services.heihe_dataset import (
    HEIHE_DATASET_ID,
    HEIHE_DEVICE_NAME,
    HEIHE_TABLE_NAME,
    format_time_range,
)
from app.services.heihe_grassland_dataset import build_heihe_grassland_geojson
from app.services.forest_carbon_dataset import (
    build_forest_carbon_overlay_response,
    get_forest_carbon_raster_path,
    normalize_metric,
    normalize_year,
)
from app.services.southwest_temperature_dataset import build_southwest_temperature_dataset_response
from app.services.central_asia_desert_dataset import (
    build_central_asia_desert_geojson,
    estimate_point_density_bucket,
)
from app.services.badaling_imagery_dataset import (
    build_badaling_imagery_dataset_response,
    get_badaling_tile_path,
)
from app.services.hepingjie_imagery_dataset import (
    build_hepingjie_imagery_dataset_response,
    get_hepingjie_tile_path,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def build_extent(asset: GeoAsset) -> Optional[list[float]]:
    if asset.extent_min_x is None:
        return None
    return [asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y]


def parse_bbox(bbox: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    if not bbox:
        return None
    try:
        min_x, min_y, max_x, max_y = [float(part.strip()) for part in bbox.split(",")]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid bbox format: {exc}")

    if min_x >= max_x or min_y >= max_y:
        raise HTTPException(status_code=400, detail="Invalid bbox bounds")
    return min_x, min_y, max_x, max_y


def apply_bbox_filter(query, bbox: Optional[tuple[float, float, float, float]]):
    if not bbox:
        return query

    min_x, min_y, max_x, max_y = bbox
    return query.filter(
        GeoAsset.is_sidecar == False,
        (
            (
                GeoAsset.extent_min_x.isnot(None)
            ) &
            (GeoAsset.extent_max_x >= min_x) &
            (GeoAsset.extent_min_x <= max_x) &
            (GeoAsset.extent_max_y >= min_y) &
            (GeoAsset.extent_min_y <= max_y)
        ) |
        (
            GeoAsset.center_x.isnot(None) &
            GeoAsset.center_y.isnot(None) &
            (GeoAsset.center_x >= min_x) &
            (GeoAsset.center_x <= max_x) &
            (GeoAsset.center_y >= min_y) &
            (GeoAsset.center_y <= max_y)
        )
    )


def infer_asset_indexing(asset: GeoAsset) -> dict:
    file_type = (asset.file_type or "").lower()
    sub_type = (asset.sub_type or "").lower()
    file_path = (asset.file_path or "").lower()

    if "shp" in sub_type or file_path.endswith(".shp") or "矢量" in file_type:
        return {
            "asset_family": "vector",
            "render_mode": "map-overlay",
            "overlay_supported": True,
            "index_point_enabled": True,
            "downloadable": True,
        }

    if "geotiff" in sub_type or file_path.endswith(".tif") or file_path.endswith(".tiff"):
        return {
            "asset_family": "raster",
            "render_mode": "map-overlay",
            "overlay_supported": True,
            "index_point_enabled": True,
            "downloadable": True,
        }

    if "netcdf" in sub_type or file_path.endswith(".nc") or file_path.endswith(".nc4"):
        return {
            "asset_family": "raster",
            "render_mode": "map-overlay",
            "overlay_supported": True,
            "index_point_enabled": True,
            "downloadable": True,
        }

    if file_path.endswith(".xlsx") or file_path.endswith(".xls") or file_path.endswith(".csv") or "表格" in sub_type:
        return {
            "asset_family": "table",
            "render_mode": "point-index",
            "overlay_supported": False,
            "index_point_enabled": True,
            "downloadable": True,
        }

    if "文档" in file_type or file_path.endswith(".pdf") or file_path.endswith(".doc") or file_path.endswith(".docx"):
        return {
            "asset_family": "document",
            "render_mode": "download-only",
            "overlay_supported": False,
            "index_point_enabled": False,
            "downloadable": True,
        }

    return {
        "asset_family": "unknown",
        "render_mode": "point-index",
        "overlay_supported": False,
        "index_point_enabled": True,
        "downloadable": True,
    }


def build_geo_data_item(asset: GeoAsset, *, distance: Optional[float] = None) -> GeoDataItem:
    full_path = settings.STORAGE_DIR / asset.file_path
    extent = build_extent(asset)
    indexing = infer_asset_indexing(asset)

    center_x = asset.center_x
    center_y = asset.center_y
    if center_x is None and extent:
        center_x = (extent[0] + extent[2]) / 2
        center_y = (extent[1] + extent[3]) / 2

    return GeoDataItem(
        id=asset.id,
        name=asset.name,
        type=asset.file_type,
        uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
        extent=extent,
        srid=asset.srid,
        exists=full_path.exists(),
        center_x=center_x,
        center_y=center_y,
        distance=distance,
        description=asset.description,
        image_path=asset.image_path,
        asset_family=indexing["asset_family"],
        render_mode=indexing["render_mode"],
        overlay_supported=indexing["overlay_supported"],
        index_point_enabled=indexing["index_point_enabled"],
        downloadable=indexing["downloadable"],
        source="internal",
    )


def build_catalog_geo_data_item(item: CatalogSearchItem) -> GeoDataItem:
    return GeoDataItem(
        id=item.id,
        name=item.name,
        type=item.file_type,
        sub_type=item.sub_type,
        uploadTime=item.time_range or "",
        extent=item.extent,
        bbox=item.extent,
        srid=item.srid,
        exists=True,
        center_x=item.center_x,
        center_y=item.center_y,
        description=item.description,
        asset_family=item.asset_family,
        render_mode=item.render_mode,
        overlay_supported=item.overlay_supported,
        index_point_enabled=item.index_point_enabled,
        downloadable=item.downloadable,
        overlay_id=item.overlay_id,
        source=item.source,
        dataset_id=item.dataset_id,
        time_range=item.time_range,
        download_url=item.download_url,
    )


def extract_primary_image_path(image_path: Optional[str]) -> Optional[str]:
    if not image_path:
        return None
    for part in image_path.split(","):
        cleaned = part.strip()
        if cleaned and not cleaned.startswith("thumb:"):
            return cleaned
    return None


def resolve_asset_preview_file(asset: GeoAsset, *, full_size: bool = False) -> Path:
    relative_path = asset.file_path if full_size else extract_primary_image_path(asset.image_path) or asset.file_path
    return settings.STORAGE_DIR / relative_path


LOCAL_RASTER_OVERLAY_CATALOG = {
    "himalaya-topography-2018": {
        "name": "喜马拉雅山区 1:25万地形影像（2018）",
        "path": Path.home() / "Downloads" / "喜马拉雅山区流域1:25万地形数据（2018）" / "喜马拉雅山区1：25万地形数据.tif",
        "min_zoom": 3,
        "opacity": 92,
        "description": "源文件位于本机 Downloads，达到指定缩放级别后叠加显示，可按区域边界识别为地质影像数据。",
    }
}
LOCAL_RASTER_PREVIEW_SIZE = (8192, 8192)


def get_local_raster_overlay_definition(overlay_id: str) -> dict:
    overlay = LOCAL_RASTER_OVERLAY_CATALOG.get(overlay_id)
    if not overlay:
        raise HTTPException(status_code=404, detail="Local raster overlay not found")
    return overlay


def build_local_raster_overlay_response(overlay_id: str, overlay: dict, tif_path: Path) -> LocalRasterOverlayResponse:
    import rasterio

    with rasterio.open(tif_path) as src:
        bounds = src.bounds
        srid = src.crs.to_epsg() if src.crs else None
        band_count = src.count
        dtype = src.dtypes[0] if src.dtypes else None
        nodata = float(src.nodata) if src.nodata is not None else None
        band_tags = src.tags(1) if band_count else {}
        raster_min = band_tags.get("STATISTICS_MINIMUM")
        raster_max = band_tags.get("STATISTICS_MAXIMUM")
        if raster_min is None or raster_max is None:
            stats = src.statistics(1, approx=True, clear_cache=False)
            raster_min = stats.min
            raster_max = stats.max

    raster_min_value = float(raster_min) if raster_min is not None else None
    raster_max_value = float(raster_max) if raster_max is not None else None

    extent = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    return LocalRasterOverlayResponse(
        id=overlay_id,
        name=overlay["name"],
        extent=extent,
        srid=srid or 4326,
        min_zoom=overlay.get("min_zoom", 8),
        opacity=overlay.get("opacity", 75),
        center_x=(bounds.left + bounds.right) / 2,
        center_y=(bounds.bottom + bounds.top) / 2,
        description=overlay.get("description"),
        source_path=str(tif_path),
        raster_url=f"/api/geodata/local-raster-download/{overlay_id}",
        band_count=band_count,
        dtype=dtype,
        nodata=nodata,
        raster_min=raster_min_value,
        raster_max=raster_max_value,
    )


def ensure_local_raster_preview(overlay_id: str, tif_path: Path) -> Optional[Path]:
    preview_dir = settings.STORAGE_DIR / "previews" / "local_rasters" / overlay_id
    preview_path = preview_dir / f"{tif_path.stem}_preview.jpg"
    if preview_path.exists():
        return preview_path

    generated_preview = create_web_preview(
        tif_path,
        preview_dir,
        target_size=LOCAL_RASTER_PREVIEW_SIZE,
    )
    if not generated_preview:
        return None
    return Path(generated_preview)


def _load_heihe_bbox(db: Session, site_key: Optional[str] = None) -> Optional[list[float]]:
    params: dict[str, object] = {}
    where_clause = ""
    if site_key:
        where_clause = "WHERE site_key = :site_key"
        params["site_key"] = site_key

    bbox_row = db.execute(
        text(
            f"""
            SELECT
                MIN(lon) AS min_lon,
                MIN(lat) AS min_lat,
                MAX(lon) AS max_lon,
                MAX(lat) AS max_lat
            FROM {HEIHE_TABLE_NAME}
            {where_clause}
            """
        ),
        params,
    ).mappings().first()

    if not bbox_row or bbox_row["min_lon"] is None:
        return None

    return [
        float(bbox_row["min_lon"]),
        float(bbox_row["min_lat"]),
        float(bbox_row["max_lon"]),
        float(bbox_row["max_lat"]),
    ]


def _build_heihe_geojson_feature_collection(
    db: Session,
    *,
    mode: str,
    site_key: Optional[str] = None,
) -> dict:
    if mode == "observations":
        if not site_key:
            raise HTTPException(status_code=400, detail="site_key is required when mode=observations")

        rows = db.execute(
            text(
                f"""
                SELECT
                    id,
                    site_key,
                    site_name,
                    ring_code,
                    observed_at,
                    soil_respiration_rate,
                    linear_flux,
                    fit_status,
                    source_file_name,
                    location_precision,
                    lon,
                    lat,
                    raw_metadata,
                    ST_AsGeoJSON(geom) AS geometry
                FROM {HEIHE_TABLE_NAME}
                WHERE site_key = :site_key
                ORDER BY observed_at ASC
                """
            ),
            {"site_key": site_key},
        ).mappings().all()

        bbox = _load_heihe_bbox(db, site_key=site_key)
        features = []
        for row in rows:
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(row["geometry"]),
                    "properties": {
                        "dataset_id": HEIHE_DATASET_ID,
                        "name": row["site_name"],
                        "site_key": row["site_key"],
                        "site_name": row["site_name"],
                        "ring_code": row["ring_code"],
                        "observed_at": row["observed_at"].isoformat() if row["observed_at"] else None,
                        "soil_respiration_rate": row["soil_respiration_rate"],
                        "linear_flux": row["linear_flux"],
                        "fit_status": row["fit_status"],
                        "source_file_name": row["source_file_name"],
                        "device_name": HEIHE_DEVICE_NAME,
                        "type": "黑河土壤呼吸观测点",
                        "sub_type": "HeiheObservation",
                        "source": "heihe-dataset",
                        "downloadable": True,
                        "download_url": "/api/download/heihe",
                        "location_precision": row["location_precision"],
                        "uploadTime": row["observed_at"].strftime("%Y-%m-%d %H:%M:%S") if row["observed_at"] else "",
                        "center_x": row["lon"],
                        "center_y": row["lat"],
                        "metadata": {
                            "dataset_name": "黑河下游土壤呼吸数据集",
                            "time_range": row["observed_at"].strftime("%Y-%m-%d") if row["observed_at"] else None,
                            "device_name": HEIHE_DEVICE_NAME,
                            "record_count": 1,
                            "source_file_name": row["source_file_name"],
                            "soil_respiration_rate": row["soil_respiration_rate"],
                            "linear_flux": row["linear_flux"],
                            "fit_status": row["fit_status"],
                            "raw_metadata": row["raw_metadata"],
                        },
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "dataset_id": HEIHE_DATASET_ID,
            "mode": mode,
            "bbox": bbox,
            "features": features,
        }

    rows = db.execute(
        text(
            f"""
            SELECT
                site_key,
                MAX(site_name) AS site_name,
                MIN(observed_at) AS min_observed_at,
                MAX(observed_at) AS max_observed_at,
                COUNT(*) AS record_count,
                AVG(soil_respiration_rate) AS avg_soil_respiration_rate,
                MIN(soil_respiration_rate) AS min_soil_respiration_rate,
                MAX(soil_respiration_rate) AS max_soil_respiration_rate,
                MIN(lon) AS min_lon,
                MIN(lat) AS min_lat,
                MAX(lon) AS max_lon,
                MAX(lat) AS max_lat,
                ST_AsGeoJSON(ST_Centroid(ST_Collect(geom))) AS geometry
            FROM {HEIHE_TABLE_NAME}
            GROUP BY site_key
            ORDER BY site_key ASC
            """
        )
    ).mappings().all()

    bbox = _load_heihe_bbox(db)
    meta_row = db.execute(
        text(
            f"""
            SELECT
                MIN(observed_at) AS min_observed_at,
                MAX(observed_at) AS max_observed_at,
                COUNT(*) AS record_count,
                COUNT(DISTINCT site_key) AS site_count
            FROM {HEIHE_TABLE_NAME}
            """
        )
    ).mappings().first()

    features = []
    for index, row in enumerate(rows, start=1):
        feature_bbox = [
            float(row["min_lon"]),
            float(row["min_lat"]),
            float(row["max_lon"]),
            float(row["max_lat"]),
        ]
        time_range = format_time_range(row["min_observed_at"], row["max_observed_at"])
        avg_flux = float(row["avg_soil_respiration_rate"]) if row["avg_soil_respiration_rate"] is not None else None
        min_flux = float(row["min_soil_respiration_rate"]) if row["min_soil_respiration_rate"] is not None else None
        max_flux = float(row["max_soil_respiration_rate"]) if row["max_soil_respiration_rate"] is not None else None
        geometry = json.loads(row["geometry"])
        center_x, center_y = geometry["coordinates"]

        features.append(
            {
                "type": "Feature",
                "id": index,
                "geometry": geometry,
                "properties": {
                    "dataset_id": HEIHE_DATASET_ID,
                    "name": row["site_name"],
                    "site_name": row["site_name"],
                    "site_key": row["site_key"],
                    "time_range": time_range,
                    "record_count": int(row["record_count"]),
                    "device_name": HEIHE_DEVICE_NAME,
                    "avg_soil_respiration_rate": avg_flux,
                    "min_soil_respiration_rate": min_flux,
                    "max_soil_respiration_rate": max_flux,
                    "type": "黑河土壤呼吸站点",
                    "sub_type": "HeiheSite",
                    "source": "heihe-dataset",
                    "downloadable": True,
                    "download_url": "/api/download/heihe",
                    "uploadTime": row["max_observed_at"].strftime("%Y-%m-%d %H:%M:%S") if row["max_observed_at"] else "",
                    "center_x": center_x,
                    "center_y": center_y,
                    "extent": feature_bbox,
                    "bbox": feature_bbox,
                    "metadata": {
                        "dataset_name": "黑河下游土壤呼吸数据集",
                        "time_range": time_range,
                        "device_name": HEIHE_DEVICE_NAME,
                        "record_count": int(row["record_count"]),
                        "avg_soil_respiration_rate": avg_flux,
                        "min_soil_respiration_rate": min_flux,
                        "max_soil_respiration_rate": max_flux,
                    },
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "dataset_id": HEIHE_DATASET_ID,
        "mode": mode,
        "bbox": bbox,
        "metadata": {
            "dataset_name": "黑河下游土壤呼吸数据集",
            "device_name": HEIHE_DEVICE_NAME,
            "record_count": int(meta_row["record_count"]) if meta_row and meta_row["record_count"] is not None else 0,
            "site_count": int(meta_row["site_count"]) if meta_row and meta_row["site_count"] is not None else 0,
            "time_range": format_time_range(
                meta_row["min_observed_at"] if meta_row else None,
                meta_row["max_observed_at"] if meta_row else None,
            ),
        },
        "features": features,
    }


@router.get("/local-raster-overlays", response_model=list[LocalRasterOverlayResponse])
async def get_local_raster_overlays(current_user=Depends(get_current_user)):
    overlays: list[LocalRasterOverlayResponse] = []

    for overlay_id, overlay in LOCAL_RASTER_OVERLAY_CATALOG.items():
        tif_path = Path(overlay["path"])
        if not tif_path.exists():
            logger.info("Skipped missing local raster overlay: %s", tif_path)
            continue
        overlays.append(
            await run_in_threadpool(build_local_raster_overlay_response, overlay_id, overlay, tif_path)
        )

    return overlays


@router.get("/local-raster-preview/{overlay_id}")
async def get_local_raster_preview(
    overlay_id: str,
    current_user=Depends(get_current_user),
):
    overlay = get_local_raster_overlay_definition(overlay_id)
    tif_path = Path(overlay["path"])
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail="Local raster file not found")

    preview_path = await run_in_threadpool(ensure_local_raster_preview, overlay_id, tif_path)
    if not preview_path:
        raise HTTPException(status_code=500, detail="Failed to create local raster preview")

    return FileResponse(preview_path, media_type="image/jpeg")


@router.get("/local-raster-download/{overlay_id}")
async def download_local_raster(
    overlay_id: str,
    current_user=Depends(get_current_user),
):
    overlay = get_local_raster_overlay_definition(overlay_id)
    tif_path = Path(overlay["path"])
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail="Local raster file not found")

    media_type, _ = mimetypes.guess_type(str(tif_path))
    return FileResponse(
        tif_path,
        media_type=media_type or "image/tiff",
        filename=tif_path.name,
    )


@router.get("/heihe")
async def get_heihe_geojson(
    mode: str = "sites",
    site_key: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    normalized_mode = (mode or "sites").strip().lower()
    if normalized_mode not in {"sites", "observations"}:
        raise HTTPException(status_code=400, detail="mode must be either 'sites' or 'observations'")

    try:
        return _build_heihe_geojson_feature_collection(
            db,
            mode=normalized_mode,
            site_key=site_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load Heihe soil respiration dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load Heihe dataset: {exc}")


@router.get("/heihe-grassland")
async def get_heihe_grassland_geojson(
    mode: str = "polygons",
    current_user=Depends(get_current_user),
):
    try:
        return await run_in_threadpool(build_heihe_grassland_geojson, mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load Heihe grassland dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load Heihe grassland dataset: {exc}")


@router.get("/forest-carbon")
async def get_forest_carbon_overlay(
    metric: str = "AGBC",
    year: int = 2021,
    current_user=Depends(get_current_user),
):
    try:
        return await run_in_threadpool(build_forest_carbon_overlay_response, metric, year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load forest carbon dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load forest carbon dataset: {exc}")


@router.get("/forest-carbon-raster/{metric}/{year}")
async def download_forest_carbon_raster_for_map(
    metric: str,
    year: int,
    current_user=Depends(get_current_user),
):
    try:
        normalized_metric = normalize_metric(metric)
        normalized_year = normalize_year(year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    tif_path = get_forest_carbon_raster_path(normalized_metric, normalized_year)
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail="Forest carbon raster not found")

    return FileResponse(
        tif_path,
        media_type="image/tiff",
        filename=tif_path.name,
    )


@router.get("/southwest-temperature")
async def get_southwest_temperature_dataset(current_user=Depends(get_current_user)):
    try:
        return await run_in_threadpool(build_southwest_temperature_dataset_response)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load southwest temperature dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load southwest temperature dataset: {exc}")


@router.get("/central-asia-desert")
async def get_central_asia_desert_dataset(
    mode: str = "urban-points",
    bbox: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    parsed_bbox = parse_bbox(bbox)
    normalized_mode = (mode or "urban-points").strip().lower()
    if normalized_mode != "countries" and not parsed_bbox:
        raise HTTPException(status_code=400, detail="bbox is required for urban layers")
    try:
        response = await run_in_threadpool(build_central_asia_desert_geojson, normalized_mode, parsed_bbox)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load central Asia desert dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load central Asia desert dataset: {exc}")

    metadata = response.setdefault("metadata", {})
    returned_count = int(metadata.get("returned_count") or len(response.get("features", [])))
    metadata["density_bucket"] = estimate_point_density_bucket(returned_count)
    return response


@router.get("/badaling-imagery")
async def get_badaling_imagery_dataset(current_user=Depends(get_current_user)):
    try:
        return await run_in_threadpool(build_badaling_imagery_dataset_response)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load Badaling imagery dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load Badaling imagery dataset: {exc}")


@router.get("/badaling-imagery-raster/{level}/{tile_id}")
async def download_badaling_imagery_tile(level: int, tile_id: str, current_user=Depends(get_current_user)):
    try:
        tif_path = get_badaling_tile_path(level, tile_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return FileResponse(
        tif_path,
        media_type="image/tiff",
        filename=tif_path.name,
    )


@router.get("/hepingjie-imagery")
async def get_hepingjie_imagery_dataset(current_user=Depends(get_current_user)):
    try:
        return await run_in_threadpool(build_hepingjie_imagery_dataset_response)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load Hepingjie imagery dataset")
        raise HTTPException(status_code=500, detail=f"Failed to load Hepingjie imagery dataset: {exc}")


@router.get("/hepingjie-imagery-raster/{level}/{tile_id}")
async def download_hepingjie_imagery_tile(level: int, tile_id: str, current_user=Depends(get_current_user)):
    try:
        tif_path = get_hepingjie_tile_path(level, tile_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return FileResponse(
        tif_path,
        media_type="image/tiff",
        filename=tif_path.name,
    )

@router.get("/summary")
async def get_stats_summary(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取统计摘要"""
    try:
        type_counts = db.query(
            GeoAsset.file_type, 
            func.count(GeoAsset.id)
        ).filter(
            GeoAsset.is_sidecar == False
        ).group_by(GeoAsset.file_type).all()
        
        pie_data = []
        for t in type_counts:
            name = t[0] or "未知"
            if name == "栅格":
                 nc_count = db.query(func.count(GeoAsset.id)).filter(
                     GeoAsset.is_sidecar == False,
                     GeoAsset.sub_type == 'NetCDF'
                 ).scalar()
                 
                 tif_count = t[1] - (nc_count or 0)
                 if nc_count > 0:
                     pie_data.append({"name": "NetCDF", "value": nc_count})
                 if tif_count > 0:
                     pie_data.append({"name": "GeoTIFF", "value": tif_count})
            else:
                 pie_data.append({"name": name, "value": t[1]})

        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        
        daily_counts = db.query(
            func.date(GeoAsset.created_at).label('date'),
            func.count(GeoAsset.id)
        ).filter(
            GeoAsset.is_sidecar == False,
            GeoAsset.created_at >= start_date
        ).group_by(
            func.date(GeoAsset.created_at)
        ).all()
        
        date_map = {str(t[0]): t[1] for t in daily_counts if t[0]}
        
        bar_categories = []
        bar_values = []
        
        for i in range(7):
            d = start_date + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            bar_categories.append(d.strftime("%m-%d"))
            bar_values.append(date_map.get(d_str, 0))
            
        return {
            "pie": pie_data,
            "bar": {
                "categories": bar_categories,
                "values": bar_values
            }
        }
    except Exception as e:
        print(f"Stats summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_geodata_stats(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取数据统计信息"""
    type_counts = db.query(
        GeoAsset.file_type, 
        func.count(GeoAsset.id)
    ).filter(
        GeoAsset.is_sidecar == False
    ).group_by(GeoAsset.file_type).all()
    
    pie_data = [{"name": t[0] or "未知", "value": t[1]} for t in type_counts]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=6)
    
    daily_counts = db.query(
        func.date(GeoAsset.updated_at).label('date'),
        func.count(GeoAsset.id)
    ).filter(
        GeoAsset.is_sidecar == False,
        GeoAsset.updated_at >= start_date
    ).group_by(
        func.date(GeoAsset.updated_at)
    ).all()
    
    date_map = {str(t[0]): t[1] for t in daily_counts if t[0]}
    
    bar_categories = []
    bar_values = []
    
    for i in range(7):
        d = start_date + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        bar_categories.append(d.strftime("%m-%d"))
        bar_values.append(date_map.get(d_str, 0))
        
    return {
        "pie": pie_data,
        "bar": {
            "categories": bar_categories,
            "values": bar_values
        }
    }

@router.get("/detail/{id}")
async def get_geodata_detail(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取地质数据详情及元数据"""
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="GeoAsset not found")
        
    full_path = settings.STORAGE_DIR / asset.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="GeoAsset file not found on disk")
    
    metadata = {}
    if asset.sub_type == 'NetCDF':
         try:
             metadata = NetCDFProcessor.extract_metadata(full_path)
         except Exception as e:
             logger.warning("Extract NetCDF metadata failed for asset %s: %s", asset.id, e)
    else:
        metadata = SpatialService.extract_metadata(full_path)
    
    return {
        "id": asset.id,
        "name": asset.name,
        "file_path": asset.file_path,
        "image_path": asset.image_path,
        "type": asset.file_type,
        "sub_type": asset.sub_type,
        "srid": asset.srid,
        "upload_time": asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
        "metadata": metadata
    }



@router.get("/list", response_model=GeoDataListResponse)
async def get_geodata_list(
    bbox: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取数据列表"""
    parsed_bbox = parse_bbox(bbox)
    query = db.query(GeoAsset).filter(GeoAsset.is_sidecar == False)
    query = apply_bbox_filter(query, parsed_bbox)
    assets = query.order_by(GeoAsset.updated_at.desc()).all()
    data_list = [build_geo_data_item(asset) for asset in assets]
    return GeoDataListResponse(data=data_list, total=len(data_list))

@router.get("/search", response_model=GeoDataListResponse)
async def search_geodata(
    q: str = None, 
    lat: float = None, 
    lon: float = None,
    bbox: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """搜索地质数据 (关键字/附近)"""
    if not q and (lat is None or lon is None):
        return GeoDataListResponse(data=[], total=0)
    
    parsed_bbox = parse_bbox(bbox)
    base_query = db.query(GeoAsset).filter(GeoAsset.is_sidecar == False)
    base_query = apply_bbox_filter(base_query, parsed_bbox)
    
    # 智能搜索接入点：如果 q 看起来像自然语言且不是坐标，可以考虑在这里也接入 smart search
    # 但为了保持兼容性，我们新增 smart-search 接口
    
    import re
    coord_match = re.match(r'^(-?\d+(\.\d+)?),\s*(-?\d+(\.\d+)?)$', q if q else "")
    
    if coord_match:
        search_lon = float(coord_match.group(1))
        search_lat = float(coord_match.group(3))
        
        pt_search = func.ST_SetSRID(func.ST_MakePoint(search_lon, search_lat), 4326)
        distance_expr = func.ST_Distance(
            func.geography(func.ST_SetSRID(func.ST_MakePoint(GeoAsset.center_x, GeoAsset.center_y), 4326)),
            func.geography(pt_search)
        )
        
        query = db.query(GeoAsset, distance_expr.label('distance')).filter(
            GeoAsset.is_sidecar == False,
            GeoAsset.center_x.isnot(None),
            GeoAsset.center_y.isnot(None)
        )
        query = apply_bbox_filter(query, parsed_bbox).order_by(distance_expr).limit(5)
        
        results = query.all()
        data_list = [build_geo_data_item(asset, distance=dist) for asset, dist in results]
        return GeoDataListResponse(data=data_list, total=len(data_list))

    if q:
        base_query = base_query.filter(
            (GeoAsset.name.ilike(f"%{q}%")) | 
            (GeoAsset.file_path.ilike(f"%{q}%")) |
            (GeoAsset.description.ilike(f"%{q}%"))
        )
    
    if lat is not None and lon is not None:
        pt_asset = func.ST_SetSRID(func.ST_MakePoint(GeoAsset.center_x, GeoAsset.center_y), 4326)
        pt_view = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        distance_expr = func.ST_Distance(func.geography(pt_asset), func.geography(pt_view))
        
        query = db.query(GeoAsset, distance_expr.label('distance')).filter(
            GeoAsset.is_sidecar == False,
            GeoAsset.center_x.isnot(None),
            GeoAsset.center_y.isnot(None)
        )
        query = apply_bbox_filter(query, parsed_bbox)
        if q:
            query = query.filter((GeoAsset.name.ilike(f"%{q}%")) | (GeoAsset.description.ilike(f"%{q}%")))
            
        results = query.order_by(distance_expr).limit(50).all()
        data_list = [build_geo_data_item(asset, distance=dist) for asset, dist in results]
        return GeoDataListResponse(data=data_list, total=len(data_list))
            
    else:
        assets = base_query.order_by(GeoAsset.updated_at.desc()).all()
        data_list = [build_geo_data_item(asset) for asset in assets]
        return GeoDataListResponse(data=data_list, total=len(data_list))
    
    return GeoDataListResponse(data=[], total=0)

@router.post("/smart-search", response_model=SmartSearchResponse)
async def smart_search(
    payload: SmartSearchRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    基于自然语言的智能搜索
    """
    if not payload.query.strip():
        return SmartSearchResponse(data=[], total=0, mode="fallback", reason="empty_query")
    
    engine = SemanticSearchEngine(db)
    assets, mode, reason = await engine.search(payload.query, payload.config.model_dump() if payload.config else None)
    
    data_list = [
        build_catalog_geo_data_item(asset) if isinstance(asset, CatalogSearchItem) else build_geo_data_item(asset)
        for asset in assets
    ]
    return SmartSearchResponse(data=data_list, total=len(data_list), mode=mode, reason=reason)

@router.post("/upload")
async def upload_files(
    files: Union[List[UploadFile], UploadFile] = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if isinstance(files, UploadFile):
        files = [files]
        
    if not files:
        raise HTTPException(status_code=422, detail="No files provided.")

    allowed_extensions = {
        ".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".xml", ".geojson", ".json", ".kml", ".gpx",
        ".tif", ".tiff", ".tfw", ".img", ".nc", ".nc4", ".csv", ".txt", ".xlsx", ".xls",
        ".jpg", ".jpeg", ".png", ".webp", ".pdf", ".doc", ".docx", ".zip",
    }
    shapefile_sidecar_exts = {".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".xml"}
    ignored_names = {".ds_store", "thumbs.db"}
    
    batch_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    upload_dir = settings.TEMP_DIR / batch_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_file_paths: list[Path] = []
    processed_assets = []
    errors: list[str] = []
    zip_results = {}

    classifier = AIGeodataClassifier()

    def clean_filename(filename: str | None) -> str:
        raw = Path(filename or "unnamed").name
        return raw or f"unnamed_{uuid.uuid4().hex[:8]}"

    def unique_asset_name(base_name: str) -> str:
        candidate = base_name.strip() or f"未命名资源_{uuid.uuid4().hex[:8]}"
        if not db.query(GeoAsset).filter(GeoAsset.name == candidate).first():
            return candidate

        stem = Path(candidate).stem or candidate
        suffix = Path(candidate).suffix
        for index in range(1, 1000):
            next_candidate = f"{stem}_{index}{suffix}"
            if not db.query(GeoAsset).filter(GeoAsset.name == next_candidate).first():
                return next_candidate
        return f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"

    def safe_target_path(directory: Path, filename: str) -> Path:
        target = directory / clean_filename(filename)
        if not target.exists():
            return target
        return directory / f"{target.stem}_{uuid.uuid4().hex[:8]}{target.suffix}"

    def append_description(*parts: Optional[str]) -> Optional[str]:
        text_parts = [part.strip() for part in parts if part and part.strip()]
        return "\n".join(text_parts) if text_parts else None

    def update_extent_geometry(asset: GeoAsset) -> None:
        if None in (asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y):
            return
        try:
            db.execute(
                text(
                    """
                    UPDATE geo_assets
                    SET extent = ST_SetSRID(ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326), 4326)
                    WHERE id = :id
                    """
                ),
                {
                    "minx": asset.extent_min_x,
                    "miny": asset.extent_min_y,
                    "maxx": asset.extent_max_x,
                    "maxy": asset.extent_max_y,
                    "id": asset.id,
                },
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to update GeoAsset extent geometry for %s: %s", asset.name, exc)

    def store_asset(asset: GeoAsset) -> GeoAsset:
        asset.name = unique_asset_name(asset.name)
        db.add(asset)
        db.commit()
        db.refresh(asset)
        update_extent_geometry(asset)
        return asset

    def append_processed(asset: GeoAsset, detected_type: str, details: Optional[dict] = None) -> None:
        processed_assets.append({
            "id": asset.id,
            "name": asset.name,
            "type": detected_type,
            "file_type": asset.file_type,
            "sub_type": asset.sub_type,
            "center_x": asset.center_x,
            "center_y": asset.center_y,
            "srid": asset.srid,
            "extent": build_extent(asset),
            "image_path": asset.image_path,
            "details": details or {},
        })

    async def post_process_asset(asset: GeoAsset, original_path: Path) -> None:
        try:
            ai_result = await classifier.classify_upload(
                original_path,
                {"name": asset.name, "type": asset.file_type, "sub_type": asset.sub_type},
            )
            if ai_result:
                tags = ai_result.get("suggested_tags", [])
                desc = ai_result.get("auto_description", "")
                ai_text = f"[AI Analysis]\nDescription: {desc}\nTags: {', '.join(tags)}".strip()
                asset.description = append_description(asset.description, ai_text)
                db.commit()
        except Exception as exc:
            logger.info("AI classification skipped for %s: %s", asset.name, exc)

    def save_upload_to_temp(file: UploadFile) -> Optional[Path]:
        filename = clean_filename(file.filename)
        if filename.lower() in ignored_names:
            return None
        ext = Path(filename).suffix.lower()
        if ext not in allowed_extensions:
            errors.append(f"文件 {filename} 格式不支持")
            return None
        file_path = safe_target_path(upload_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if file_path.stat().st_size == 0:
            errors.append(f"文件 {filename} 为空文件")
            file_path.unlink(missing_ok=True)
            return None
        return file_path

    def expand_zip(zip_path: Path) -> list[Path]:
        extract_dir = upload_dir / f"{zip_path.stem}_extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        extracted: list[Path] = []
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    member_name = Path(member.filename).name
                    if not member_name or member_name.lower() in ignored_names:
                        continue
                    ext = Path(member_name).suffix.lower()
                    if ext not in allowed_extensions or ext == ".zip":
                        errors.append(f"压缩包 {zip_path.name} 内文件 {member_name} 格式不支持")
                        continue
                    target = safe_target_path(extract_dir, member_name)
                    with archive.open(member) as source, open(target, "wb") as output:
                        shutil.copyfileobj(source, output)
                    if target.stat().st_size == 0:
                        errors.append(f"压缩包 {zip_path.name} 内文件 {member_name} 为空文件")
                        target.unlink(missing_ok=True)
                        continue
                    extracted.append(target)
            zip_results[zip_path.name] = {"extracted": len(extracted)}
        except zipfile.BadZipFile:
            errors.append(f"压缩包 {zip_path.name} 无法解压")
        return extracted

    def move_related_files(stem: str, paths: list[Path], target_dir: Path) -> dict[str, Path]:
        related: dict[str, Path] = {}
        for source in list(paths):
            if source.stem != stem:
                continue
            target = safe_target_path(target_dir, source.name)
            shutil.move(str(source), str(target))
            related[source.suffix.lower()] = target
        return related

    async def process_shapefile(shp_path: Path, all_paths: list[Path]) -> None:
        stem = shp_path.stem
        same_stem_exts = {path.suffix.lower() for path in all_paths if path.stem == stem}
        missing = {".shx", ".dbf"} - same_stem_exts
        if missing:
            errors.append(f"Shapefile {shp_path.name} 缺少必要附属文件: {', '.join(sorted(missing))}")
            return

        target_dir = settings.VECTOR_DIR / batch_id / stem
        target_dir.mkdir(parents=True, exist_ok=True)
        related = move_related_files(stem, all_paths, target_dir)
        target_shp = related.get(".shp")
        if not target_shp:
            errors.append(f"Shapefile {shp_path.name} 保存失败")
            return

        try:
            gdf = ParserService.parse_vector_file(target_shp, target_crs="EPSG:4326")
            bounds = gdf.total_bounds
            extent_min_x, extent_min_y, extent_max_x, extent_max_y = map(float, bounds)
            center_x = (extent_min_x + extent_max_x) / 2
            center_y = (extent_min_y + extent_max_y) / 2
            srid = ParserService.parse_prj_file(related[".prj"]) if ".prj" in related else 4326
            details = {"feature_count": int(len(gdf)), "columns": [str(col) for col in gdf.columns if str(col) != "geometry"]}
        except Exception as exc:
            errors.append(f"Shapefile {shp_path.name} 解析失败: {exc}")
            return

        asset = store_asset(GeoAsset(
            name=stem,
            file_path=str(target_shp.relative_to(settings.STORAGE_DIR)),
            file_type="矢量",
            sub_type="Shapefile",
            srid=srid,
            extent_min_x=extent_min_x,
            extent_min_y=extent_min_y,
            extent_max_x=extent_max_x,
            extent_max_y=extent_max_y,
            center_x=center_x,
            center_y=center_y,
            description=append_description(description, f"Shapefile 矢量数据，共 {details['feature_count']} 个要素。"),
            is_sidecar=False,
        ))

        for ext, sidecar_path in related.items():
            if ext == ".shp" or ext not in shapefile_sidecar_exts:
                continue
            db.add(GeoAsset(
                name=unique_asset_name(sidecar_path.name),
                file_path=str(sidecar_path.relative_to(settings.STORAGE_DIR)),
                file_type="附属文件",
                sub_type=ext[1:].upper(),
                is_sidecar=True,
                parent_id=asset.id,
            ))
        db.commit()
        await post_process_asset(asset, target_shp)
        append_processed(asset, "shp", details)

    async def process_vector_file(vector_path: Path, all_paths: list[Path]) -> None:
        target_dir = settings.VECTOR_DIR / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_vector = safe_target_path(target_dir, vector_path.name)
        shutil.move(str(vector_path), str(target_vector))

        try:
            gdf = ParserService.parse_vector_file(target_vector, target_crs="EPSG:4326")
            bounds = gdf.total_bounds
            extent_min_x, extent_min_y, extent_max_x, extent_max_y = map(float, bounds)
            center_x = (extent_min_x + extent_max_x) / 2
            center_y = (extent_min_y + extent_max_y) / 2
            details = {
                "feature_count": int(len(gdf)),
                "columns": [str(col) for col in gdf.columns if str(col) != "geometry"],
            }
        except Exception as exc:
            errors.append(f"矢量文件 {vector_path.name} 解析失败: {exc}")
            return

        subtype_map = {
            ".geojson": "GeoJSON",
            ".json": "GeoJSON",
            ".kml": "KML",
            ".gpx": "GPX",
        }
        asset = store_asset(GeoAsset(
            name=vector_path.stem,
            file_path=str(target_vector.relative_to(settings.STORAGE_DIR)),
            file_type="矢量",
            sub_type=subtype_map.get(vector_path.suffix.lower(), vector_path.suffix.lstrip(".").upper()),
            srid=4326,
            extent_min_x=extent_min_x,
            extent_min_y=extent_min_y,
            extent_max_x=extent_max_x,
            extent_max_y=extent_max_y,
            center_x=center_x,
            center_y=center_y,
            description=append_description(description, f"矢量数据，共 {details['feature_count']} 个要素。"),
            is_sidecar=False,
        ))
        await post_process_asset(asset, target_vector)
        append_processed(asset, "vector", details)

    async def process_geotiff(tif_path: Path, all_paths: list[Path]) -> None:
        target_dir = settings.RASTER_DIR / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)
        related = move_related_files(tif_path.stem, all_paths, target_dir)
        target_tif = related.get(tif_path.suffix.lower())
        if not target_tif:
            errors.append(f"GeoTIFF {tif_path.name} 保存失败")
            return

        try:
            import rasterio
            from rasterio.warp import transform_bounds

            with rasterio.open(str(target_tif)) as src:
                width = src.width
                height = src.height
                srid = src.crs.to_epsg() if src.crs else 4326
                bounds = src.bounds
                if src.crs and srid != 4326:
                    left, bottom, right, top = transform_bounds(src.crs, "EPSG:4326", *bounds, densify_pts=21)
                else:
                    left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top
                details = {
                    "width": width,
                    "height": height,
                    "band_count": src.count,
                    "crs": src.crs.to_string() if src.crs else "EPSG:4326",
                    "driver": src.driver,
                    "nodata": src.nodata,
                }
        except Exception as exc:
            errors.append(f"GeoTIFF {tif_path.name} 读取失败: {exc}")
            return

        center_x = (float(left) + float(right)) / 2
        center_y = (float(bottom) + float(top)) / 2
        asset = store_asset(GeoAsset(
            name=tif_path.stem,
            file_path=str(target_tif.relative_to(settings.STORAGE_DIR)),
            file_type="栅格",
            sub_type="GeoTIFF",
            srid=4326,
            width=width,
            height=height,
            extent_min_x=float(left),
            extent_min_y=float(bottom),
            extent_max_x=float(right),
            extent_max_y=float(top),
            center_x=center_x,
            center_y=center_y,
            description=append_description(description, f"GeoTIFF 栅格影像，{width}×{height}，{details['band_count']} 个波段。"),
            is_sidecar=False,
        ))

        preview_path = optimize_asset_preview(target_tif, settings.STORAGE_DIR, asset.id)
        if preview_path:
            asset.image_path = preview_path
            db.commit()
            db.refresh(asset)
        await post_process_asset(asset, target_tif)
        append_processed(asset, "tif", details)

    async def process_netcdf(nc_path: Path, all_paths: list[Path]) -> None:
        target_dir = settings.RASTER_DIR / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_nc = safe_target_path(target_dir, nc_path.name)
        shutil.move(str(nc_path), str(target_nc))

        details: dict[str, object] = {}
        left = bottom = right = top = center_x = center_y = None
        try:
            import xarray as xr
            ds = xr.open_dataset(target_nc)
            try:
                details = {
                    "dims": {name: int(size) for name, size in ds.sizes.items()},
                    "variables": list(ds.data_vars.keys())[:30],
                }
                lon_name = next((name for name in ds.coords if name.lower() in {"lon", "longitude", "x"}), None)
                lat_name = next((name for name in ds.coords if name.lower() in {"lat", "latitude", "y"}), None)
                if lon_name and lat_name:
                    lon_values = ds[lon_name].values
                    lat_values = ds[lat_name].values
                    left = float(lon_values.min())
                    right = float(lon_values.max())
                    bottom = float(lat_values.min())
                    top = float(lat_values.max())
                    center_x = (left + right) / 2
                    center_y = (bottom + top) / 2
            finally:
                ds.close()
        except Exception as exc:
            details = {"metadata_warning": str(exc)}

        asset = store_asset(GeoAsset(
            name=nc_path.stem,
            file_path=str(target_nc.relative_to(settings.STORAGE_DIR)),
            file_type="栅格",
            sub_type="NetCDF",
            srid=4326,
            extent_min_x=left,
            extent_min_y=bottom,
            extent_max_x=right,
            extent_max_y=top,
            center_x=center_x,
            center_y=center_y,
            description=append_description(description, f"NetCDF 多维科学数据。变量: {', '.join(details.get('variables', [])[:8]) if isinstance(details.get('variables'), list) else '未知'}"),
            is_sidecar=False,
        ))
        await post_process_asset(asset, target_nc)
        append_processed(asset, "nc", details)

    async def process_table(table_path: Path, all_paths: list[Path]) -> None:
        target_dir = settings.DOC_DIR / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_table = safe_target_path(target_dir, table_path.name)
        shutil.move(str(table_path), str(target_table))

        details: dict[str, object] = {}
        center_x = center_y = None
        try:
            import pandas as pd
            if target_table.suffix.lower() == ".csv":
                df = pd.read_csv(target_table)
            elif target_table.suffix.lower() in {".xlsx", ".xls"}:
                df = pd.read_excel(target_table)
            else:
                df = pd.read_csv(target_table, sep=None, engine="python")

            details = {"rows": int(len(df)), "columns": [str(col) for col in df.columns]}
            lower_columns = {str(col).lower(): col for col in df.columns}
            lon_col = next((lower_columns[key] for key in lower_columns if key in {"lon", "lng", "longitude", "经度", "x"}), None)
            lat_col = next((lower_columns[key] for key in lower_columns if key in {"lat", "latitude", "纬度", "y"}), None)
            if lon_col is not None and lat_col is not None and len(df) > 0:
                lon_series = pd.to_numeric(df[lon_col], errors="coerce").dropna()
                lat_series = pd.to_numeric(df[lat_col], errors="coerce").dropna()
                if not lon_series.empty and not lat_series.empty:
                    center_x = float(lon_series.mean())
                    center_y = float(lat_series.mean())
        except Exception as exc:
            details = {"metadata_warning": str(exc)}

        asset = store_asset(GeoAsset(
            name=table_path.stem,
            file_path=str(target_table.relative_to(settings.STORAGE_DIR)),
            file_type="文档",
            sub_type="表格",
            srid=4326,
            center_x=center_x,
            center_y=center_y,
            description=append_description(description, f"表格数据。字段: {', '.join(details.get('columns', [])[:8]) if isinstance(details.get('columns'), list) else '未知'}"),
            is_sidecar=False,
        ))
        await post_process_asset(asset, target_table)
        append_processed(asset, "table", details)

    async def process_document(doc_path: Path, all_paths: list[Path]) -> None:
        ext = doc_path.suffix.lower()
        target_dir = settings.DOC_DIR / batch_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_doc = safe_target_path(target_dir, doc_path.name)
        shutil.move(str(doc_path), str(target_doc))

        is_image = ext in {".jpg", ".jpeg", ".png", ".webp"}
        asset = store_asset(GeoAsset(
            name=doc_path.stem,
            file_path=str(target_doc.relative_to(settings.STORAGE_DIR)),
            file_type="图片" if is_image else "文档",
            sub_type="Image" if is_image else ext.lstrip(".").upper(),
            description=append_description(description, "普通图片资源。" if is_image else "普通文档资源。"),
            image_path=str(target_doc.relative_to(settings.STORAGE_DIR)) if is_image else None,
            is_sidecar=False,
        ))
        await post_process_asset(asset, target_doc)
        append_processed(asset, "image" if is_image else "document", {"size": target_doc.stat().st_size})

    try:
        for file in files:
            saved = save_upload_to_temp(file)
            if saved:
                uploaded_file_paths.append(saved)

        expanded_paths: list[Path] = []
        for zip_path in [path for path in uploaded_file_paths if path.suffix.lower() == ".zip"]:
            expanded_paths.extend(expand_zip(zip_path))

        candidate_paths = [
            path for path in [*uploaded_file_paths, *expanded_paths]
            if path.exists() and path.suffix.lower() != ".zip"
        ]

        if not candidate_paths and errors:
            raise HTTPException(status_code=400, detail=f"上传失败: {'; '.join(errors)}")

        processed_path_keys: set[str] = set()

        for shp_path in [path for path in candidate_paths if path.suffix.lower() == ".shp"]:
            await process_shapefile(shp_path, candidate_paths)
            processed_path_keys.update(str(path) for path in candidate_paths if path.stem == shp_path.stem)

        for vector_path in [path for path in candidate_paths if path.suffix.lower() in {".geojson", ".json", ".kml", ".gpx"} and str(path) not in processed_path_keys]:
            await process_vector_file(vector_path, candidate_paths)
            processed_path_keys.add(str(vector_path))

        for tif_path in [path for path in candidate_paths if path.suffix.lower() in {".tif", ".tiff"} and str(path) not in processed_path_keys]:
            await process_geotiff(tif_path, candidate_paths)
            processed_path_keys.update(str(path) for path in candidate_paths if path.stem == tif_path.stem and path.suffix.lower() in {".tif", ".tiff", ".tfw", ".prj", ".xml"})

        for nc_path in [path for path in candidate_paths if path.suffix.lower() in {".nc", ".nc4"} and str(path) not in processed_path_keys]:
            await process_netcdf(nc_path, candidate_paths)
            processed_path_keys.add(str(nc_path))

        for table_path in [path for path in candidate_paths if path.suffix.lower() in {".csv", ".txt", ".xlsx", ".xls"} and str(path) not in processed_path_keys]:
            await process_table(table_path, candidate_paths)
            processed_path_keys.add(str(table_path))

        for doc_path in [path for path in candidate_paths if path.exists() and str(path) not in processed_path_keys and path.suffix.lower() not in shapefile_sidecar_exts]:
            await process_document(doc_path, candidate_paths)
            processed_path_keys.add(str(doc_path))

        if not processed_assets:
            message = "; ".join(errors) if errors else "未找到可处理的主数据文件，请上传 GeoTIFF、Shapefile、NetCDF、CSV、GeoJSON 或 ZIP 数据包"
            raise HTTPException(status_code=400, detail=message)

        shutil.rmtree(upload_dir, ignore_errors=True)
        
        return JSONResponse(status_code=200, content={
            "message": f"处理完成: 成功 {len(processed_assets)} 个",
            "processed": processed_assets,
            "errors": errors,
            "zip_results": zip_results
        })
        
    except HTTPException:
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise
    except Exception as e:
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"上传错误: {str(e)}")


@router.get("/preview/{id}")
async def preview_geodata(
    id: int,
    full_size: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="GeoAsset not found")

    file_path = resolve_asset_preview_file(asset, full_size=full_size)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Preview file not found")

    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=media_type or "application/octet-stream")


@router.get("/download/{id}")
async def download_geodata(
    id: int,
    preview: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="GeoAsset not found")

    file_path = resolve_asset_preview_file(asset, full_size=not preview)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    media_type, _ = mimetypes.guess_type(str(file_path))
    filename = file_path.name if preview else f"{asset.name}{file_path.suffix}"
    return FileResponse(
        file_path,
        media_type=media_type or "application/octet-stream",
        filename=filename,
    )

@router.delete("/delete/{id}", dependencies=[Depends(role_checker)])
async def delete_geodata(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="GeoAsset not found")
    try:
        file_path = settings.STORAGE_DIR / asset.file_path
        if file_path.exists():
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
        db.delete(asset)
        db.commit()
        return {"message": "Data deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download/batch")
async def download_batch_files(
    file_ids: List[int],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """批量下载文件"""
    assets = db.query(GeoAsset).filter(GeoAsset.id.in_(file_ids)).all()
    if not assets:
        raise HTTPException(status_code=404, detail="No files found")
        
    # Create a zip stream
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for asset in assets:
            full_path = settings.STORAGE_DIR / asset.file_path
            if full_path.exists():
                if full_path.is_dir():
                    for f in full_path.glob("**/*"):
                        if f.is_file():
                            zip_file.write(f, arcname=f"{asset.name}/{f.relative_to(full_path)}")
                else:
                    zip_file.write(full_path, arcname=asset.name + full_path.suffix)
            
            # Include sidecars if shapefile
            if asset.sub_type == 'Shapefile':
                # Logic to include sidecars if they are stored separately or just assume they are in the same dir?
                # In our upload logic, we put them in a folder. If not, we might miss them.
                pass

    zip_buffer.seek(0)
    
    filename = f"geodata_batch_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
