from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.services.heihe_dataset import ensure_dataset_archive
from app.services.heihe_grassland_dataset import ensure_heihe_grassland_archive
from app.services.forest_carbon_dataset import get_forest_carbon_raster_path, normalize_metric, normalize_year
from app.services.southwest_temperature_dataset import SOUTHWEST_TEMPERATURE_FILE
from app.services.central_asia_desert_dataset import ensure_central_asia_desert_archive
from app.services.badaling_imagery_dataset import ensure_badaling_imagery_archive
from app.services.hepingjie_imagery_dataset import ensure_hepingjie_imagery_archive

router = APIRouter()

@router.get("/zip")
async def download_zip(files: list[str] = Query(...)):
    """
    打包下载指定文件 (示例接口)
    """
    # TODO: 实现文件打包逻辑
    # 这里的 files 可能是文件路径或 ID
    pass


@router.get("/heihe")
async def download_heihe_dataset(current_user=Depends(get_current_user)):
    archive_path = ensure_dataset_archive(settings.TEMP_DIR / "downloads")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )


@router.get("/heihe-grassland")
async def download_heihe_grassland_dataset(current_user=Depends(get_current_user)):
    archive_path = ensure_heihe_grassland_archive(settings.TEMP_DIR / "downloads")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )


@router.get("/forest-carbon/{metric}/{year}")
async def download_forest_carbon_raster(metric: str, year: int, current_user=Depends(get_current_user)):
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
async def download_southwest_temperature_dataset(current_user=Depends(get_current_user)):
    if not SOUTHWEST_TEMPERATURE_FILE.exists():
        raise HTTPException(status_code=404, detail="Southwest temperature dataset not found")

    return FileResponse(
        SOUTHWEST_TEMPERATURE_FILE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=SOUTHWEST_TEMPERATURE_FILE.name,
    )


@router.get("/central-asia-desert")
async def download_central_asia_desert_dataset(current_user=Depends(get_current_user)):
    archive_path = ensure_central_asia_desert_archive(settings.TEMP_DIR / "downloads")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )


@router.get("/badaling-imagery")
async def download_badaling_imagery_dataset(current_user=Depends(get_current_user)):
    archive_path = ensure_badaling_imagery_archive(settings.TEMP_DIR / "downloads")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )


@router.get("/hepingjie-imagery")
async def download_hepingjie_imagery_dataset(current_user=Depends(get_current_user)):
    archive_path = ensure_hepingjie_imagery_archive(settings.TEMP_DIR / "downloads")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )
