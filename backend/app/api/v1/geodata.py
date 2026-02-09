from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Union
import shutil
from pathlib import Path
from urllib.parse import quote
import io
import zipfile
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models.geo_asset import GeoAsset
from app.services.spatial_service import SpatialService
from app.services.parser_service import ParserService
from app.schemas import GeoDataListResponse, GeoDataItem
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/stats")
async def get_geodata_stats(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取数据统计信息"""
    # 1. 矢量 vs 栅格 比例
    # 简单起见，按 file_type 分组
    type_counts = db.query(
        GeoAsset.file_type, 
        func.count(GeoAsset.id)
    ).filter(
        GeoAsset.is_sidecar == False
    ).group_by(GeoAsset.file_type).all()
    
    # 格式化为 ECharts pie data
    pie_data = [{"name": t[0] or "未知", "value": t[1]} for t in type_counts]
    
    # 2. 最近一周上传数量
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
    
    # 补全日期 (即使某天没有数据也要显示 0)
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
    
    # 提取元数据
    metadata = SpatialService.extract_metadata(full_path)
    
    return {
        "id": asset.id,
        "name": asset.name,
        "file_path": asset.file_path,
        "type": asset.file_type,
        "sub_type": asset.sub_type,
        "srid": asset.srid,
        "upload_time": asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
        "metadata": metadata
    }

@router.get("/list", response_model=GeoDataListResponse)
async def get_geodata_list(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取数据列表 (仅展示主文件，隐藏附属文件)"""
    assets = db.query(GeoAsset).filter(GeoAsset.is_sidecar == False).order_by(GeoAsset.updated_at.desc()).all()
    data_list = []
    
    for asset in assets:
        # 检查文件是否存在
        full_path = settings.STORAGE_DIR / asset.file_path
        exists = full_path.exists()
        
        extent = None
        if asset.extent_min_x is not None:
            extent = [asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y]
        
        center_x = asset.center_x
        center_y = asset.center_y
        if center_x is None and extent:
            center_x = (extent[0] + extent[2]) / 2
            center_y = (extent[1] + extent[3]) / 2
            
        data_list.append(GeoDataItem(
            id=asset.id,
            name=asset.name,
            type=asset.file_type, # 这里可以改为 sub_type
            uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
            extent=extent,
            srid=asset.srid,
            exists=exists,
            center_x=center_x,
            center_y=center_y,
            description=asset.description,
            source="internal"
        ))
        
    return GeoDataListResponse(data=data_list, total=len(data_list))

@router.get("/search", response_model=GeoDataListResponse)
async def search_geodata(
    q: str = None, 
    lat: float = None, 
    lon: float = None,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """搜索地质数据 (支持关键字和附近搜索)"""
    if not q and (lat is None or lon is None):
        return GeoDataListResponse(data=[], total=0)
    
    # 基础查询
    base_query = db.query(GeoAsset).filter(GeoAsset.is_sidecar == False)
    
    # 0. 检查是否为坐标格式 "lon, lat"
    import re
    coord_match = re.match(r'^(-?\d+(\.\d+)?),\s*(-?\d+(\.\d+)?)$', q if q else "")
    
    if coord_match:
        # 坐标搜索模式
        search_lon = float(coord_match.group(1))
        search_lat = float(coord_match.group(3))
        
        pt_search = func.ST_SetSRID(func.ST_MakePoint(search_lon, search_lat), 4326)
        
        # 计算距离
        distance_expr = func.ST_Distance(
            func.ST_Cast(func.ST_SetSRID(func.ST_MakePoint(GeoAsset.center_x, GeoAsset.center_y), 4326), 'Geography'),
            func.ST_Cast(pt_search, 'Geography')
        )
        
        query = db.query(GeoAsset, distance_expr.label('distance')).filter(
            GeoAsset.is_sidecar == False,
            GeoAsset.center_x.isnot(None),
            GeoAsset.center_y.isnot(None)
        ).order_by(distance_expr).limit(5)
        
        results = query.all()
        
        for asset, dist in results:
            full_path = settings.STORAGE_DIR / asset.file_path
            exists = full_path.exists()
            
            extent = None
            if asset.extent_min_x is not None:
                extent = [asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y]
                
            data_list.append(GeoDataItem(
                id=asset.id,
                name=asset.name,
                type=asset.file_type,
                uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
                extent=extent,
                srid=asset.srid,
                exists=exists,
                center_x=asset.center_x,
                center_y=asset.center_y,
                distance=dist,
                description=asset.description,
                source="internal"
            ))
            
        return GeoDataListResponse(data=data_list, total=len(data_list))

    # 如果有关键字
    if q:
        base_query = base_query.filter(
            (GeoAsset.name.ilike(f"%{q}%")) | 
            (GeoAsset.file_path.ilike(f"%{q}%")) |
            (GeoAsset.description.ilike(f"%{q}%"))
        )
    
    # 如果有坐标，计算距离 (附近搜索)
    if lat is not None and lon is not None:
        # 使用 PostGIS 计算距离
        # 构造 Point(center_x, center_y) 并设置 SRID 4326
        # 假设 center_x/y 也是 4326 (Lon/Lat)
        pt_asset = func.ST_SetSRID(func.ST_MakePoint(GeoAsset.center_x, GeoAsset.center_y), 4326)
        pt_view = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        
        # 计算距离 (转为 Geography 以获取米单位)
        distance_expr = func.ST_Distance(
            func.ST_Cast(pt_asset, 'Geography'),
            func.ST_Cast(pt_view, 'Geography')
        )
        
        # 修改查询以包含距离
        # 必须过滤掉 center_x/y 为空的记录
        query = db.query(GeoAsset, distance_expr.label('distance')).filter(
            GeoAsset.is_sidecar == False,
            GeoAsset.center_x.isnot(None),
            GeoAsset.center_y.isnot(None)
        )
        
        if q:
            query = query.filter(
                (GeoAsset.name.ilike(f"%{q}%")) | 
                (GeoAsset.file_path.ilike(f"%{q}%")) |
                (GeoAsset.description.ilike(f"%{q}%"))
            )
            
        # 按距离排序
        results = query.order_by(distance_expr).limit(50).all()
        
        for asset, dist in results:
            full_path = settings.STORAGE_DIR / asset.file_path
            exists = full_path.exists()
            
            extent = None
            if asset.extent_min_x is not None:
                extent = [asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y]
                
            data_list.append(GeoDataItem(
                id=asset.id,
                name=asset.name,
                type=asset.file_type,
                uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
                extent=extent,
                srid=asset.srid,
                exists=exists,
                center_x=asset.center_x,
                center_y=asset.center_y,
                distance=dist, # 米
                description=asset.description,
                source="internal"
            ))
            
    else:
        # 仅关键字搜索
        assets = base_query.order_by(GeoAsset.updated_at.desc()).all()
        
        for asset in assets:
            full_path = settings.STORAGE_DIR / asset.file_path
            exists = full_path.exists()
            
            extent = None
            if asset.extent_min_x is not None:
                extent = [asset.extent_min_x, asset.extent_min_y, asset.extent_max_x, asset.extent_max_y]
                
            center_x = asset.center_x
            center_y = asset.center_y
            if center_x is None and extent:
                center_x = (extent[0] + extent[2]) / 2
                center_y = (extent[1] + extent[3]) / 2
                
            data_list.append(GeoDataItem(
                id=asset.id,
                name=asset.name,
                type=asset.file_type,
                uploadTime=asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else "",
                extent=extent,
                srid=asset.srid,
                exists=exists,
                center_x=center_x,
                center_y=center_y,
                description=asset.description,
                source="internal"
            ))
        
    return GeoDataListResponse(data=data_list, total=len(data_list))

@router.post("/upload")
async def upload_files(
    files: Union[List[UploadFile], UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 统一转为列表处理
    if isinstance(files, UploadFile):
        files = [files]
        
    if not files:
        raise HTTPException(status_code=422, detail="No files provided. Please upload at least one file.")

    # 1. 定义允许的扩展名和批次ID
    ALLOWED_EXTENSIONS = {
        # 矢量数据
        '.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.geojson', '.json', '.kml', '.gpx',
        # 栅格数据
        '.tif', '.tiff', '.tfw', '.img',
        # 表格/文档
        '.csv', '.txt', '.pdf', '.doc', '.docx',
        # 压缩包
        '.zip', '.rar', '.7z'
    }
    
    import uuid
    from datetime import datetime
    
    batch_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    upload_dir = settings.TEMP_DIR / batch_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_file_paths = []
    processed_assets = []
    errors = []
    
    try:
        # 2. 保存所有文件到临时批次目录
        for file in files:
            filename = file.filename
            ext = Path(filename).suffix.lower()
            
            if ext not in ALLOWED_EXTENSIONS:
                errors.append(f"文件 {filename} 格式不支持")
                continue
                
            file_path = upload_dir / filename
            
            # 使用 shutil.copyfileobj 高效保存
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_file_paths.append(file_path)

        if not uploaded_file_paths and errors:
             raise HTTPException(status_code=400, detail=f"上传失败: {'; '.join(errors)}")

        # 3. 分析文件类型并分类处理
        # 识别主文件
        shp_files = [f for f in uploaded_file_paths if f.suffix.lower() == '.shp']
        tif_files = [f for f in uploaded_file_paths if f.suffix.lower() in ['.tif', '.tiff']]
        zip_files = [f for f in uploaded_file_paths if f.suffix.lower() == '.zip']
        tabular_files = [f for f in uploaded_file_paths if f.suffix.lower() in ['.csv', '.txt']]
        
        # 3.1 处理 Shapefile (需检查完整性)
        for shp_path in shp_files:
            stem = shp_path.stem
            # 检查必须的 sidecar 文件 (.shx, .dbf)
            required_extensions = ['.shx', '.dbf']
            missing = []
            sidecars = []
            
            # 在当前批次目录中查找同名文件
            for req_ext in required_extensions:
                req_file = upload_dir / f"{stem}{req_ext}"
                if not req_file.exists():
                    # 尝试查找不同大小写的情况? 暂时假设文件名一致
                    missing.append(req_ext)
                else:
                    sidecars.append(req_file)
            
            # 还要查找其他可选 sidecar (.prj, .cpg, etc)
            optional_extensions = ['.prj', '.cpg', '.sbn', '.sbx', '.xml']
            for opt_ext in optional_extensions:
                opt_file = upload_dir / f"{stem}{opt_ext}"
                if opt_file.exists():
                    sidecars.append(opt_file)

            if missing:
                errors.append(f"Shapefile {shp_path.name} 缺少必要文件: {', '.join(missing)}")
                continue
                
            # 移动文件到 VECTOR_DIR/batch_id
            target_dir = settings.VECTOR_DIR / batch_id
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # 移动主文件
            target_shp = target_dir / shp_path.name
            shutil.move(str(shp_path), str(target_shp))
            
            # 移动 Sidecars
            for sidecar in sidecars:
                shutil.move(str(sidecar), str(target_dir / sidecar.name))
            
            # 入库与解析
            try:
                gdf = ParserService.parse_vector_file(target_shp, target_crs="EPSG:4326")
                bounds = gdf.total_bounds
                extent_min_x = float(bounds[0])
                extent_min_y = float(bounds[1])
                extent_max_x = float(bounds[2])
                extent_max_y = float(bounds[3])
                center_x = (extent_min_x + extent_max_x) / 2
                center_y = (extent_min_y + extent_max_y) / 2

                # 1. 创建 GeoAsset
                asset = GeoAsset(
                    name=shp_path.name,
                    file_path=str(target_shp.relative_to(settings.STORAGE_DIR)),
                    file_type="矢量",
                    sub_type="矢量/SHP",
                    is_sidecar=False,
                    srid=4326,
                    extent_min_x=extent_min_x,
                    extent_min_y=extent_min_y,
                    extent_max_x=extent_max_x,
                    extent_max_y=extent_max_y,
                    center_x=center_x,
                    center_y=center_y
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
                processed_assets.append({"id": asset.id, "name": asset.name, "type": "shp"})
                
                # 2. 解析内容 (可选，耗时操作可放入后台任务)
                # await run_in_threadpool(SpatialService.process_and_import_vector, target_shp, db)
                # 这里为了即时反馈，我们简单尝试导入，失败不影响上传成功
                try:
                    count = SpatialService.process_and_import_vector(target_shp, db)
                    processed_assets[-1]["features_count"] = count
                except Exception as e:
                    print(f"矢量解析警告: {e}")
                    processed_assets[-1]["warning"] = f"上传成功但解析失败: {str(e)}"
                    
            except Exception as e:
                errors.append(f"处理 Shapefile {shp_path.name} 失败: {str(e)}")

        # 3.2 处理 TIFF
        for tif_path in tif_files:
            # 查找关联的 .tfw, .prj
            related_files = []
            stem = tif_path.stem
            for ext in ['.tfw', '.prj', '.xml', '.ovr']:
                f = upload_dir / f"{stem}{ext}"
                if f.exists():
                    related_files.append(f)
            
            target_dir = settings.RASTER_DIR / batch_id
            target_dir.mkdir(parents=True, exist_ok=True)
            
            target_tif = target_dir / tif_path.name
            shutil.move(str(tif_path), str(target_tif))
            
            for rf in related_files:
                shutil.move(str(rf), str(target_dir / rf.name))
                
            try:
                asset = SpatialService.process_and_save_geo_file(target_tif, settings.STORAGE_DIR, db)
                asset.sub_type = "影像"
                db.commit()
                processed_assets.append({"id": asset.id, "name": asset.name, "type": "tif"})
            except Exception as e:
                errors.append(f"处理 TIFF {tif_path.name} 失败: {str(e)}")

        # 3.3 处理 ZIP (调用现有服务)
        zip_results = {}
        if zip_files:
            for zip_path in zip_files:
                try:
                    # 移动到 TEMP_DIR (根级) 或保持在 batch 目录
                    # SpatialService.process_zip_archive 会解压
                    res = await run_in_threadpool(
                        SpatialService.process_zip_archive, 
                        zip_path, 
                        db
                    )
                    zip_results[zip_path.name] = res
                    processed_assets.append({"name": zip_path.name, "type": "zip", "details": res})
                except Exception as e:
                    errors.append(f"处理 ZIP {zip_path.name} 失败: {str(e)}")

        # 3.4 处理表格
        for tab_path in tabular_files:
            target_dir = settings.DOC_DIR / batch_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / tab_path.name
            shutil.move(str(tab_path), str(target_path))
            
            try:
                 asset = GeoAsset(
                    name=tab_path.name,
                    file_path=str(target_path.relative_to(settings.STORAGE_DIR)),
                    file_type="文档",
                    sub_type="表格",
                    is_sidecar=False
                )
                 db.add(asset)
                 db.commit()
                 
                 count = SpatialService.process_and_import_tabular(target_path, db)
                 processed_assets.append({"name": tab_path.name, "type": "table", "rows": count})
            except Exception as e:
                 errors.append(f"处理表格 {tab_path.name} 失败: {str(e)}")

        # 4. 清理残留文件 (未被识别为主要数据或Sidecar的文件)
        # 如果 upload_dir 还有文件，说明是多余的或者孤立的 Sidecar
        # 可以选择保留在 temp 或删除
        # 这里选择保留在 temp/batch_id 以便后续排查，或者定期清理
        
        return JSONResponse(status_code=200, content={
            "message": "文件处理完成",
            "processed": processed_assets,
            "errors": errors,
            "zip_results": zip_results
        })

    except Exception as e:
        # 清理
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

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

class DownloadBatchRequest(BaseModel):
    ids: list[int]

@router.post("/download-batch")
async def download_batch(request: DownloadBatchRequest, db: Session = Depends(get_db)):
    assets = db.query(GeoAsset).filter(GeoAsset.id.in_(request.ids)).all()
    if not assets:
        raise HTTPException(status_code=404, detail="No files found")

    files_to_zip: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    shp_sidecars = [".dbf", ".shx", ".prj"]

    for asset in assets:
        abs_path = settings.STORAGE_DIR / asset.file_path
        if not abs_path.exists() or abs_path in seen:
            continue

        suffix = abs_path.suffix.lower()

        if suffix in [".shp", ".dbf", ".shx", ".prj"]:
            base_dir = abs_path.parent
            stem = abs_path.stem

            shp_path = base_dir / f"{stem}.shp"
            candidates = [shp_path] + [base_dir / f"{stem}{ext}" for ext in shp_sidecars]

            for p in candidates:
                if p.exists() and p not in seen:
                    files_to_zip.append((p, f"{asset.id}/{p.name}"))
                    seen.add(p)
            continue

        if suffix in [".tif", ".tiff"]:
            files_to_zip.append((abs_path, f"{asset.id}/{abs_path.name}"))
            seen.add(abs_path)
            continue

        files_to_zip.append((abs_path, f"{asset.id}/{abs_path.name}"))
        seen.add(abs_path)

    if not files_to_zip:
        raise HTTPException(status_code=404, detail="No files found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for f, arcname in files_to_zip:
            zip_file.write(f, arcname)

    zip_buffer.seek(0)
    filename = "geodata_export.zip"
    encoded_filename = quote(filename, safe="")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=utf-8\'\'{encoded_filename}'
        }
    )

class SpatialDownloadRequest(BaseModel):
    extent: list[float]
    srid: int

@router.post("/spatial-download")
async def spatial_download(request: SpatialDownloadRequest, db: Session = Depends(get_db)):
    result = SpatialService.spatial_download(request.extent, request.srid, db)
    if not result:
        return JSONResponse(content={"message": "No files found in extent"})
    return result
