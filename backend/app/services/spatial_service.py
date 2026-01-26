from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import zipfile
import io
import urllib.parse
from datetime import datetime
from geoalchemy2.elements import WKTElement

from app.models.geo_asset import GeoAsset
from app.services.parser_service import ParserService
from app.core.config import settings

class SpatialService:
    @staticmethod
    def process_and_save_geo_file(tif_path: Path, storage_dir: Path, db: Session) -> GeoAsset:
        file_name = tif_path.name
        
        # 1. 确定存储路径
        try:
            file_path_str = str(tif_path.relative_to(storage_dir))
        except ValueError:
            file_path_str = file_name
            
        # 2. 查找并解析 .prj
        prj_path = None
        for candidate in [
            tif_path.with_suffix('.prj'),
            storage_dir / f"{tif_path.stem}.prj"
        ]:
            if candidate.exists():
                prj_path = candidate
                break
        
        srid = ParserService.parse_prj_file(prj_path) if prj_path else 4326
        
        # 3. 查找并解析 .tfw
        tfw_path = None
        for candidate in [
            tif_path.with_suffix('.tfw'),
            storage_dir / f"{tif_path.stem}.tfw"
        ]:
            if candidate.exists():
                tfw_path = candidate
                break
        
        extent_geom = None
        width = height = None
        res_x = res_y = None
        extent_vals = {}
        
        if tfw_path:
            tfw_data = ParserService.parse_tfw_file(tfw_path)
            width, height = ParserService.get_image_size(tif_path)
            extent = ParserService.calculate_extent(tfw_data, width, height)
            
            extent_vals = extent
            res_x = tfw_data['pixel_width']
            res_y = abs(tfw_data['pixel_height'])
            
            wkt = (
                "POLYGON((" 
                f"{extent['min_x']} {extent['min_y']}, "
                f"{extent['max_x']} {extent['min_y']}, "
                f"{extent['max_x']} {extent['max_y']}, "
                f"{extent['min_x']} {extent['max_y']}, "
                f"{extent['min_x']} {extent['min_y']}"
                "))"
            )
            
            # 使用 ST_Transform 强制转为 4326
            geom_element = WKTElement(wkt, srid=srid)
            if srid != 4326:
                extent_geom = func.ST_Transform(geom_element, 4326)
            else:
                extent_geom = geom_element

        # 4. 数据库操作
        existing = db.query(GeoAsset).filter(GeoAsset.name == file_name).first()
        if existing:
            existing.file_path = file_path_str
            existing.srid = srid
            existing.extent = extent_geom
            existing.width = width
            existing.height = height
            existing.resolution_x = res_x
            existing.resolution_y = res_y
            if extent_vals:
                existing.extent_min_x = extent_vals['min_x']
                existing.extent_min_y = extent_vals['min_y']
                existing.extent_max_x = extent_vals['max_x']
                existing.extent_max_y = extent_vals['max_y']
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_asset = GeoAsset(
                name=file_name,
                file_path=file_path_str,
                file_type="栅格", # 默认
                sub_type="影像", # 默认
                srid=srid,
                extent=extent_geom,
                width=width,
                height=height,
                resolution_x=res_x,
                resolution_y=res_y,
                extent_min_x=extent_vals.get('min_x'),
                extent_min_y=extent_vals.get('min_y'),
                extent_max_x=extent_vals.get('max_x'),
                extent_max_y=extent_vals.get('max_y')
            )
            db.add(new_asset)
            db.commit()
            db.refresh(new_asset)
            return new_asset

    @staticmethod
    def spatial_download(extent: list[float], srid: int, db: Session):
        if len(extent) != 4:
            raise HTTPException(status_code=400, detail="Extent must be [minX, minY, maxX, maxY]")
            
        minX, minY, maxX, maxY = extent
        
        # 查询相交资产
        # 注意：前端传来的是 WebMercator (3857)，数据库存的是 4326
        # ST_MakeEnvelope 需要指定 SRID，然后 ST_Intersects 会自动处理投影转换（如果 PostGIS 配置正确）
        # 但稳妥起见，我们构造 3857 的 envelope，让 PostGIS 比较
        query = text("""
            SELECT * FROM geo_assets 
            WHERE ST_Intersects(
                extent, 
                ST_Transform(ST_MakeEnvelope(:minX, :minY, :maxX, :maxY, :srid), 4326)
            )
        """)
        
        results = db.execute(query, {
            "minX": minX, "minY": minY, "maxX": maxX, "maxY": maxY, "srid": srid
        }).fetchall()
        
        if not results:
            return None
            
        files_to_zip = []
        processed_names = set()
        
        for row in results:
            # RowProxy to dict compatibility
            row_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(row.keys(), row))
            name = row_dict['name']
            
            # 简单处理：假设所有文件都在 STORAGE_DIR (需要改进为根据 file_path 查找)
            # 由于 file_path 是相对路径，我们可以尝试 resolve
            # 这里为了简单，我们还是遍历 STORAGE_DIR 的所有子目录或者根据 sub_type 判断
            
            # 实际上，file_path 字段存储的是相对于 STORAGE_DIR 的路径
            # 所以我们直接拼凑
            rel_path = row_dict['file_path']
            abs_path = settings.STORAGE_DIR / rel_path
            
            stem = Path(name).stem
            if stem in processed_names:
                continue
            processed_names.add(stem)
            
            # 查找关联文件 (TFW, PRJ 等) - 假设它们和主文件在同一目录
            parent_dir = abs_path.parent
            for f in parent_dir.iterdir():
                if f.stem == stem and f.suffix.lower() in ['.tif', '.tfw', '.prj', '.xml', '.txt']:
                    files_to_zip.append(f)
        
        if not files_to_zip:
            return None
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for f in files_to_zip:
                zip_file.write(f, f.name)
        
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"geodata_export_{timestamp}.zip"
        encoded_filename = urllib.parse.quote(filename)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={encoded_filename}; filename*=utf-8''{encoded_filename}",
                "Content-Length": str(zip_buffer.getbuffer().nbytes)
            }
        )
