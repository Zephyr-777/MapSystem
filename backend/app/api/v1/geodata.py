from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
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
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models.geo_asset import GeoAsset
from app.services.spatial_service import SpatialService
from app.services.parser_service import ParserService
from app.schemas import GeoDataListResponse, GeoDataItem

router = APIRouter()

@router.get("/stats")
async def get_geodata_stats(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取数据统计信息"""
    # 1. 矢量 vs 栅格 比例
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

@router.get("/identify", response_model=GeoDataListResponse)
async def identify_geodata(
    lat: float, 
    lon: float,
    buffer: float = 100.0,
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """
    空间属性识别：查找点击位置周围一定范围内的数据
    """
    try:
        # 构造查询点 (SRID 4326)
        pt_view = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        
        # 查找范围内的点 (使用 ST_DWithin 计算地理距离，单位：米)
        # 注意：ST_DWithin(geography, geography, distance_meters)
        # 这里我们将 geometry 转为 geography 来进行米单位的计算
        
        # 1. 查找矢量/点位数据
        # 逻辑：点的 center_x/y 在点击点 buffer 范围内
        query = db.query(GeoAsset).filter(
            GeoAsset.is_sidecar == False,
            GeoAsset.center_x.isnot(None),
            GeoAsset.center_y.isnot(None),
            func.ST_DWithin(
                func.ST_Cast(func.ST_SetSRID(func.ST_MakePoint(GeoAsset.center_x, GeoAsset.center_y), 4326), 'Geography'),
                func.ST_Cast(pt_view, 'Geography'),
                buffer
            )
        ).limit(10) # 限制返回数量
        
        results = query.all()
        data_list = []
        
        for asset in results:
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
                description=asset.description,
                source="internal"
            ))
            
        return GeoDataListResponse(data=data_list, total=len(data_list))
        
    except Exception as e:
        print(f"Error in identify: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        data_list = []
        
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
        try:
            base_query = base_query.filter(
                (GeoAsset.name.ilike(f"%{q}%")) | 
                (GeoAsset.file_path.ilike(f"%{q}%")) |
                (GeoAsset.description.ilike(f"%{q}%"))
            )
        except Exception as e:
            print(f"Error constructing search query: {e}")
            pass
    
    # 如果有坐标，计算距离 (附近搜索)
    if lat is not None and lon is not None:
        try:
            # 使用 PostGIS 计算距离
            pt_asset = func.ST_SetSRID(func.ST_MakePoint(GeoAsset.center_x, GeoAsset.center_y), 4326)
            pt_view = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
            
            # 计算距离 (转为 Geography 以获取米单位)
            distance_expr = func.ST_Distance(
                func.ST_Cast(pt_asset, 'Geography'),
                func.ST_Cast(pt_view, 'Geography')
            )
            
            # 修改查询以包含距离
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
            
            data_list = []
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
            
            return GeoDataListResponse(data=data_list, total=len(data_list))

        except Exception as e:
             print(f"Error in nearby search: {e}")
             pass
            
    else:
        # 仅关键字搜索
        try:
            assets = base_query.order_by(GeoAsset.updated_at.desc()).all()
            data_list = []
            
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

        except Exception as e:
            print(f"Error in keyword search: {e}")
            pass
        
    return GeoDataListResponse(data=[], total=0)

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

    # 1. 定义允许的扩展名
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
    
    batch_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    upload_dir = settings.TEMP_DIR / batch_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_file_paths = []
    processed_assets = []
    errors = []
    zip_results = {}
    
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
        shp_files = [f for f in uploaded_file_paths if f.suffix.lower() == '.shp']
        tif_files = [f for f in uploaded_file_paths if f.suffix.lower() in ['.tif', '.tiff']]
        zip_files = [f for f in uploaded_file_paths if f.suffix.lower() == '.zip']
        tabular_files = [f for f in uploaded_file_paths if f.suffix.lower() in ['.csv', '.txt']]
        
        # 3.1 处理 Shapefile
        for shp_path in shp_files:
            stem = shp_path.stem
            # 检查必须的 sidecar 文件
            required_extensions = ['.shx', '.dbf']
            missing = []
            sidecars = []
            
            for req_ext in required_extensions:
                req_file = upload_dir / f"{stem}{req_ext}"
                if not req_file.exists():
                    missing.append(req_ext)
                else:
                    sidecars.append(req_file)
            
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
            
            target_shp = target_dir / shp_path.name
            shutil.move(str(shp_path), str(target_shp))
            
            for sidecar in sidecars:
                shutil.move(str(sidecar), str(target_dir / sidecar.name))
            
            try:
                # 使用 fiona 读取元数据
                import fiona
                
                srid = 4326 # 默认
                bbox = None
                
                try:
                    with fiona.open(str(target_shp)) as src:
                        bbox = src.bounds
                        if src.crs and 'init' in src.crs:
                            # 尝试解析 epsg:4326 格式
                            try:
                                srid = int(src.crs['init'].split(':')[1])
                            except:
                                pass
                except Exception as e:
                    print(f"Fiona read failed: {e}")
                    # Fallback to ParserService if fiona fails (e.g. missing dependencies or driver)
                    pass

                # 如果没有 bbox，尝试读取全部
                if not bbox:
                    gdf = ParserService.parse_vector_file(target_shp, target_crs="EPSG:4326")
                    bounds = gdf.total_bounds
                    extent_min_x, extent_min_y, extent_max_x, extent_max_y = map(float, bounds)
                    srid = 4326 # 已转为 4326
                else:
                    extent_min_x, extent_min_y, extent_max_x, extent_max_y = map(float, bbox)
                
                center_x = (extent_min_x + extent_max_x) / 2
                center_y = (extent_min_y + extent_max_y) / 2
                
                asset = GeoAsset(
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
                    center_y=center_y
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
                
                # 更新 geometry 字段
                # 如果 srid 不是 4326，需要 ST_Transform，但这里简单起见假设已经正确设置 srid
                # 并尝试将其转为 4326 存储到 extent 字段 (Geometry(Polygon, 4326))
                db.execute(text(f"""
                    UPDATE geo_assets 
                    SET extent = ST_SetSRID(ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, :srid), :srid)
                    WHERE id = :id
                """), {
                    "minx": extent_min_x,
                    "miny": extent_min_y,
                    "maxx": extent_max_x,
                    "maxy": extent_max_y,
                    "srid": srid,
                    "id": asset.id
                })
                # 如果 srid != 4326，再转换一次
                if srid != 4326:
                     db.execute(text(f"""
                        UPDATE geo_assets 
                        SET extent = ST_Transform(extent, 4326)
                        WHERE id = :id
                    """), {"id": asset.id})
                     
                db.commit()
                processed_assets.append({
                    "id": asset.id, 
                    "name": asset.name, 
                    "type": "shp", 
                    "center_x": center_x, 
                    "center_y": center_y,
                    "srid": srid
                })
                
            except Exception as e:
                db.rollback()
                errors.append(f"解析 Shapefile {shp_path.name} 失败: {str(e)}")
                
        # 3.2 处理 GeoTIFF
        for tif_path in tif_files:
            try:
                target_dir = settings.RASTER_DIR / batch_id
                target_dir.mkdir(parents=True, exist_ok=True)
                target_tif = target_dir / tif_path.name
                shutil.move(str(tif_path), str(target_tif))
                
                stem = tif_path.stem
                tfw_path = upload_dir / f"{stem}.tfw"
                if tfw_path.exists():
                    shutil.move(str(tfw_path), str(target_dir / tfw_path.name))
                
                import rasterio
                from rasterio.warp import transform_bounds
                
                width, height = 0, 0
                srid = 4326
                left, bottom, right, top = 0, 0, 0, 0
                
                with rasterio.open(str(target_tif)) as src:
                    bounds = src.bounds
                    if src.crs:
                        srid = src.crs.to_epsg() or 4326
                    
                    if srid != 4326:
                        try:
                            left, bottom, right, top = transform_bounds(src.crs, 'EPSG:4326', *bounds)
                        except:
                             left, bottom, right, top = bounds
                    else:
                        left, bottom, right, top = bounds
                        
                    width = src.width
                    height = src.height
                    
                center_x = (left + right) / 2
                center_y = (bottom + top) / 2
                
                asset = GeoAsset(
                    name=stem,
                    file_path=str(target_tif.relative_to(settings.STORAGE_DIR)),
                    file_type="栅格",
                    sub_type="GeoTIFF",
                    srid=srid,
                    width=width,
                    height=height,
                    extent_min_x=left,
                    extent_min_y=bottom,
                    extent_max_x=right,
                    extent_max_y=top,
                    center_x=center_x,
                    center_y=center_y
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
                
                db.execute(text(f"""
                    UPDATE geo_assets 
                    SET extent = ST_SetSRID(ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326), 4326)
                    WHERE id = :id
                """), {
                    "minx": left,
                    "miny": bottom,
                    "maxx": right,
                    "maxy": top,
                    "id": asset.id
                })
                db.commit()
                processed_assets.append({
                    "id": asset.id, 
                    "name": asset.name, 
                    "type": "tif",
                    "center_x": center_x,
                    "center_y": center_y,
                    "srid": srid
                })
                
            except Exception as e:
                db.rollback()
                errors.append(f"解析 GeoTIFF {tif_path.name} 失败: {str(e)}")

        # 3.3 处理 ZIP
        if zip_files:
            for zip_path in zip_files:
                try:
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

        # 4. 清理
        shutil.rmtree(upload_dir, ignore_errors=True)
        
        return JSONResponse(status_code=200, content={
            "message": f"处理完成: 成功 {len(processed_assets)} 个, 失败 {len(errors)} 个",
            "processed": processed_assets,
            "errors": errors,
            "zip_results": zip_results
        })
        
    except Exception as e:
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"上传处理过程错误: {str(e)}")

@router.get("/preview/{id}")
async def preview_geodata(id: int, db: Session = Depends(get_db)):
    """预览 TIF (转 PNG)"""
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = settings.STORAGE_DIR / asset.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file not found")
        
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
