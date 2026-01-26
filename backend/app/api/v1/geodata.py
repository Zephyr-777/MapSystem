from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import shutil
from pathlib import Path
from urllib.parse import quote

from database import get_db
from app.core.config import settings
from app.models.geo_asset import GeoAsset
from app.services.spatial_service import SpatialService
from schemas import GeoDataListResponse, GeoDataItem

router = APIRouter()

@router.get("/list", response_model=GeoDataListResponse)
async def get_geodata_list(db: Session = Depends(get_db)):
    """获取数据列表"""
    assets = db.query(GeoAsset).order_by(GeoAsset.updated_at.desc()).all()
    data_list = []
    
    for asset in assets:
        # 检查文件是否存在
        full_path = settings.STORAGE_DIR / asset.file_path
        exists = full_path.exists()
        
        extent = None
        if asset.extent_min_x is not None:
            extent = [asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y]
            
        data_list.append(GeoDataItem(
            id=asset.id,
            name=asset.name,
            type=asset.file_type, # 这里可以改为 sub_type
            uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
            extent=extent,
            srid=asset.srid,
            exists=exists
        ))
        
    return GeoDataListResponse(data=data_list, total=len(data_list))

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    uploaded_files = []
    tif_to_process = None
    vector_to_process = None
    tabular_to_process = None
    
    try:
        for file in files:
            filename = file.filename
            ext = Path(filename).suffix.lower()
            
            # 分类存储
            target_dir = settings.STORAGE_DIR # 默认
            if ext in ['.tif', '.tiff', '.tfw']:
                target_dir = settings.RASTER_DIR
            elif ext in ['.shp', '.shx', '.dbf', '.geojson', '.json', '.prj']:
                target_dir = settings.VECTOR_DIR
            elif ext in ['.pdf', '.doc', '.docx', '.txt', '.csv']:
                target_dir = settings.DOC_DIR
                
            file_path = target_dir / filename
            
            # 保存文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            uploaded_files.append(filename)
            
            if ext == '.tif':
                tif_to_process = file_path
            elif ext in ['.shp', '.geojson']:
                vector_to_process = file_path
            elif ext in ['.csv', '.txt']:
                tabular_to_process = file_path
        
        # 处理 TIF (入库)
        asset_info = {}
        if tif_to_process:
            try:
                asset = SpatialService.process_and_save_geo_file(tif_to_process, settings.STORAGE_DIR, db)
                asset_info = {"id": asset.id, "name": asset.name}
                asset.sub_type = "影像"
                db.commit()
            except Exception as e:
                return JSONResponse(status_code=200, content={
                    "message": f"上传成功但解析影像失败: {str(e)}", 
                    "uploaded": uploaded_files
                })

        # 处理矢量 (入库)
        import_count = 0
        if vector_to_process:
            try:
                import_count = SpatialService.process_and_import_vector(vector_to_process, db)
            except Exception as e:
                print(f"矢量导入失败: {e}")
                # 不中断，继续
        
        # 处理表格 (文本挖掘)
        tabular_count = 0
        if tabular_to_process:
            try:
                tabular_count = SpatialService.process_and_import_tabular(tabular_to_process, db)
            except Exception as e:
                print(f"表格导入失败: {e}")

        return JSONResponse(status_code=200, content={
            "message": "上传处理完成",
            "files": uploaded_files,
            "asset": asset_info,
            "vector_imported": import_count,
            "tabular_imported": tabular_count
        })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{id}")
async def preview_geodata(id: int, db: Session = Depends(get_db)):
    """预览 TIF (转 PNG)"""
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = settings.STORAGE_DIR / asset.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file not found")
        
    # 这里为了简化，直接调用 PIL 转换逻辑，或者也可以封装进 Service
    # 为节省时间，我将复用之前的转换逻辑，但建议放在 Service 中
    try:
        from PIL import Image
        import io
        
        with Image.open(file_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return StreamingResponse(
                img_buffer,
                media_type='image/png'
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")

@router.get("/download/{id}")
async def download_geodata(id: int, db: Session = Depends(get_db)):
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = settings.STORAGE_DIR / asset.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file not found")
        
    filename = asset.name
    encoded_filename = quote(filename, safe='')
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream',
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
    )

from pydantic import BaseModel
class SpatialDownloadRequest(BaseModel):
    extent: list[float]
    srid: int

@router.post("/spatial-download")
async def spatial_download(request: SpatialDownloadRequest, db: Session = Depends(get_db)):
    result = SpatialService.spatial_download(request.extent, request.srid, db)
    if not result:
        return JSONResponse(content={"message": "No files found in extent"})
    return result
