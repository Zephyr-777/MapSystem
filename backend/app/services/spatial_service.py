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

from app.models.geologic_feature import GeologicFeature
from app.models.geo_asset import GeoAsset
from app.services.parser_service import ParserService
from app.core.config import settings
import json
import pandas as pd

class SpatialService:
    @staticmethod
    def extract_metadata(file_path: Path) -> dict:
        """
        提取地理空间文件元数据
        支持 .shp (通过 geopandas) 和 .tif (通过 rasterio)
        """
        import geopandas as gpd
        import rasterio
        
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": "File not found"}
            
        suffix = file_path.suffix.lower()
        metadata = {}
        
        try:
            if suffix == '.shp':
                gdf = gpd.read_file(file_path)
                
                # CRS
                crs_info = "Unknown"
                if gdf.crs:
                    crs_info = gdf.crs.to_string()
                    
                # Attribute table preview (first 5 rows)
                # Drop geometry column for attribute table and convert to list of dicts
                attributes = gdf.drop(columns='geometry', errors='ignore').head(5).to_dict(orient='records')
                
                # Handle non-serializable types in attributes (e.g. Timestamp)
                safe_attributes = []
                for record in attributes:
                    safe_record = {}
                    for k, v in record.items():
                        if pd.notnull(v):
                            if isinstance(v, (datetime, pd.Timestamp)):
                                safe_record[k] = str(v)
                            else:
                                safe_record[k] = v
                        else:
                            safe_record[k] = None
                    safe_attributes.append(safe_record)
                
                metadata = {
                    "type": "Vector",
                    "format": "Shapefile",
                    "crs": crs_info,
                    "feature_count": len(gdf),
                    "attributes_preview": safe_attributes,
                    "columns": list(gdf.columns.drop('geometry', errors='ignore'))
                }
                
            elif suffix in ['.tif', '.tiff']:
                with rasterio.open(file_path) as src:
                    # CRS
                    crs_info = "Unknown"
                    if src.crs:
                        crs_info = src.crs.to_string()
                        
                    metadata = {
                        "type": "Raster",
                        "format": "GeoTIFF",
                        "crs": crs_info,
                        "width": src.width,
                        "height": src.height,
                        "count": src.count, # number of bands
                        "bounds": {
                            "left": src.bounds.left,
                            "bottom": src.bounds.bottom,
                            "right": src.bounds.right,
                            "top": src.bounds.top
                        },
                        "driver": src.driver,
                        "nodata": src.nodata
                    }
            else:
                metadata = {"error": f"Unsupported file format: {suffix}"}
                
        except Exception as e:
            metadata = {"error": str(e)}
            
        return metadata

    @staticmethod
    def process_and_import_vector(file_path: Path, db: Session) -> int:
        """
        处理并导入矢量数据到 GeologicFeature 表
        """
        # 解析并重投影到 3857
        gdf = ParserService.parse_vector_file(file_path, target_crs="EPSG:3857")
        
        count = 0
        for _, row in gdf.iterrows():
            # 获取几何 WKT
            geom_wkt = row.geometry.wkt
            
            # 提取属性 (排除 geometry 列)
            properties = row.drop('geometry').to_dict()
            # 处理可能的 NaN
            properties = {k: (v if pd.notnull(v) else None) for k, v in properties.items()}
            
            # 尝试获取名称
            name = properties.get('name') or properties.get('Name') or properties.get('NAME') or f"Feature_{count}"
            
            # 尝试获取类型
            feature_type = row.geometry.geom_type
            
            # 创建记录
            feature = GeologicFeature(
                name=str(name),
                type=feature_type,
                properties=properties,
                geometry=geom_wkt # WKTElement(geom_wkt, srid=3857) -> String
            )
            db.add(feature)
            count += 1
            
        db.commit()
        return count

    @staticmethod
    def process_and_import_tabular(file_path: Path, db: Session) -> int:
        """
        处理并导入表格数据 (CSV/TXT)
        """
        records = ParserService.parse_tabular_file(file_path)
        count = 0
        
        for record in records:
            # 简单的文本挖掘逻辑：查找坐标列
            # 假设列名包含 lat/lon 或 x/y
            keys = {k.lower(): k for k in record.keys()}
            
            lon_key = next((k for k in keys if 'lon' in k or 'lng' in k), None)
            lat_key = next((k for k in keys if 'lat' in k), None)
            
            geom = None
            if lon_key and lat_key:
                try:
                    lon = float(record[keys[lon_key]])
                    lat = float(record[keys[lat_key]])
                    # 使用 ST_GeomFromText 将经纬度转为 geometry 点 (SRID 4326)
                    # 注意：如果目标表是 3857，这里需要 ST_Transform
                    # 假设 GeologicFeature.geometry 是 3857 (基于 geologic_feature.py 定义)
                    # 则: ST_Transform(ST_GeomFromText('POINT(...)', 4326), 3857)
                    
                    # 构造 Point WKT
                    wkt = f"POINT({lon} {lat})"
                    # 确保导入 func
                    # from sqlalchemy import func
                    geom = func.ST_Transform(func.ST_GeomFromText(wkt, 4326), 3857)
                except:
                    pass
            
            # 如果没有坐标，可能是纯属性表
            if geom is None:
                continue
                
            name = record.get('name') or record.get('Name') or f"Record_{count}"
            
            feature = GeologicFeature(
                name=str(name),
                type="Point",
                properties=record,
                geometry=geom
            )
            db.add(feature)
            count += 1
            
        db.commit()
        return count

    @staticmethod
    def process_zip_archive(zip_path: Path, db: Session) -> dict:
        """
        处理 ZIP 压缩包：解压 -> 递归扫描 -> 分类处理
        """
        import shutil
        import os
        
        extract_dir = settings.TEMP_DIR / zip_path.stem
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "tif_imported": 0,
            "vector_imported": 0,
            "tabular_imported": 0,
            "database_imported": 0,
            "files_found": []
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 第一遍扫描：处理主文件 (SHP, TIF, MDB, CSV)
            # 建立 stem -> main_asset_id 映射
            main_assets_map = {} # { (stem, parent_dir_name): asset_id }
            
            all_files = []
            for root, dirs, files in os.walk(extract_dir):
                for filename in files:
                    file_path = Path(root) / filename
                    # 忽略 macOS 隐藏文件
                    if filename.startswith('._') or filename == '.DS_Store':
                        continue
                    all_files.append(file_path)

            # 1. 处理主文件
            for file_path in all_files:
                filename = file_path.name
                ext = file_path.suffix.lower()
                stem = file_path.stem
                
                results["files_found"].append(filename)
                
                main_asset = None
                
                # 1.1 影像数据 (.tif)
                if ext in ['.tif', '.tiff']:
                    target_path = settings.RASTER_DIR / filename
                    shutil.move(str(file_path), str(target_path))
                    try:
                        main_asset = SpatialService.process_and_save_geo_file(target_path, settings.STORAGE_DIR, db)
                        main_asset.sub_type = "影像"
                        results["tif_imported"] += 1
                    except Exception as e:
                        print(f"ZIP内影像导入失败 {filename}: {e}")

                # 1.2 矢量数据 (.shp) - 注意只处理 .shp
                elif ext == '.shp':
                    target_path = settings.VECTOR_DIR / filename
                    shutil.move(str(file_path), str(target_path))
                    try:
                        # 尝试使用 fiona 读取更准确的元数据 (SRID)
                        import fiona
                        
                        srid = 4326 # 默认
                        bbox = None
                        
                        try:
                            with fiona.open(str(target_path)) as src:
                                bbox = src.bounds
                                if src.crs and 'init' in src.crs:
                                    # 尝试解析 epsg:4326 格式
                                    try:
                                        srid = int(src.crs['init'].split(':')[1])
                                    except:
                                        pass
                        except Exception as e:
                            print(f"Fiona 读取 ZIP 内 SHP 失败: {e}")
                        
                        if bbox:
                            extent_min_x, extent_min_y, extent_max_x, extent_max_y = map(float, bbox)
                        else:
                            # 回退到 geopandas
                            gdf = ParserService.parse_vector_file(target_path, target_crs="EPSG:4326")
                            bounds = gdf.total_bounds
                            extent_min_x, extent_min_y, extent_max_x, extent_max_y = map(float, bounds)
                            # 如果用了 geopandas 转换，srid 就是 4326 (因为 target_crs)
                            # 但如果我们想保持原始 srid，应该不传 target_crs
                            # 这里为了保险，如果有 srid，我们用 srid；如果没有，我们假设 geopandas 转成了 4326
                            if srid == 4326: 
                                srid = 4326

                        center_x = (extent_min_x + extent_max_x) / 2
                        center_y = (extent_min_y + extent_max_y) / 2

                        # 创建 GeoAsset 记录
                        main_asset = GeoAsset(
                            name=filename,
                            file_path=str(target_path.relative_to(settings.STORAGE_DIR)),
                            file_type="矢量",
                            sub_type="矢量/SHP",
                            is_sidecar=False,
                            srid=srid,
                            extent_min_x=extent_min_x,
                            extent_min_y=extent_min_y,
                            extent_max_x=extent_max_x,
                            extent_max_y=extent_max_y,
                            center_x=center_x,
                            center_y=center_y
                        )
                        db.add(main_asset)
                        db.commit()
                        db.refresh(main_asset)
                        
                        # 更新 Geometry 字段
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
                            "id": main_asset.id
                        })
                        
                        # 如果 srid != 4326，再转换一次到 4326
                        if srid != 4326:
                             db.execute(text(f"""
                                UPDATE geo_assets 
                                SET extent = ST_Transform(extent, 4326)
                                WHERE id = :id
                            """), {"id": main_asset.id})
                        
                        db.commit()
                        
                        results["vector_imported"] += 1
                    except Exception as e:
                        db.rollback()
                        print(f"ZIP内矢量记录创建失败 {filename}: {e}")

                # 1.3 数据库 (.mdb, .db)
                elif ext in ['.mdb', '.db', '.gdb']:
                    # 创建新的 DATABASE_DIR 或者放在 DOC_DIR
                    # 暂时放在 DOC_DIR
                    target_path = settings.DOC_DIR / filename
                    shutil.move(str(file_path), str(target_path))
                    try:
                        main_asset = GeoAsset(
                            name=filename,
                            file_path=str(target_path.relative_to(settings.STORAGE_DIR)),
                            file_type="数据库",
                            sub_type="Geologic Database",
                            is_sidecar=False
                        )
                        db.add(main_asset)
                        db.commit()
                        db.refresh(main_asset)
                        results["database_imported"] += 1
                    except Exception as e:
                        print(f"ZIP内数据库导入失败 {filename}: {e}")

                # 1.4 表格/文档 (.csv, .txt)
                elif ext in ['.csv', '.txt']:
                    target_path = settings.DOC_DIR / filename
                    shutil.move(str(file_path), str(target_path))
                    try:
                        # 既要创建 GeoAsset，也要尝试挖掘内容
                        main_asset = GeoAsset(
                            name=filename,
                            file_path=str(target_path.relative_to(settings.STORAGE_DIR)),
                            file_type="文档",
                            sub_type="表格",
                            is_sidecar=False
                        )
                        db.add(main_asset)
                        db.commit()
                        db.refresh(main_asset)
                        
                        # 挖掘内容
                        SpatialService.process_and_import_tabular(target_path, db)
                        results["tabular_imported"] += 1
                    except Exception as e:
                        print(f"ZIP内表格导入失败 {filename}: {e}")

                if main_asset:
                    # 记录主文件ID，用于关联 Sidecar
                    # Key 使用 (stem, parent_dir_name) 以防不同目录下有同名文件
                    # 或者简单点只用 stem，假设 ZIP 内文件名唯一
                    # SOTER 数据集结构比较复杂，可能在 GIS/ 和 SOTER/ 下都有文件
                    # 使用 file_path.parent.name 作为辅助 key
                    key = (stem, file_path.parent.name) 
                    main_assets_map[key] = main_asset.id
                    
                    # 同时也记录纯 stem，作为备选 (如果 sidecar 在同一目录下)
                    # 如果有重名，后面的会覆盖前面的，这是个风险，但在同一目录下通常没问题
                    main_assets_map[stem] = main_asset.id

            # 2. 第二遍扫描：处理 Sidecar 文件
            # 需要重新遍历 extracted_dir，因为文件已经被移动了？
            # 不，我们之前遍历的是 all_files 列表，其中主文件已经被移动了，但 file_path 对象还在
            # 实际上，如果主文件被移动了，原来的路径就不存在了，但这不影响 file_path 对象
            # 但是 sidecar 文件还在原地
            
            # 重新扫描 extract_dir，因为剩下的就是未处理的文件 (sidecars + 其它)
            # 或者直接遍历 all_files，检查文件是否还在原地
            
            for file_path in all_files:
                if not file_path.exists(): 
                    continue # 已经被移动处理过了
                
                filename = file_path.name
                ext = file_path.suffix.lower()
                stem = file_path.stem
                
                # 常见的 Sidecar 后缀
                is_sidecar = ext in ['.shx', '.dbf', '.prj', '.sbx', '.sbn', '.xml', '.box', '.lbd', '.tfw']
                
                target_dir = settings.DOC_DIR # 默认
                
                # 尝试找到 parent
                parent_id = None
                
                # 优先尝试 (stem, parent_dir_name) 匹配
                key = (stem, file_path.parent.name)
                if key in main_assets_map:
                    parent_id = main_assets_map[key]
                elif stem in main_assets_map:
                    parent_id = main_assets_map[stem]
                
                # 决定目标目录
                # 如果找到了 parent，应该去 parent 所在的目录
                # 但这里简化处理，根据后缀归类
                if ext in ['.shx', '.dbf', '.prj', '.sbx', '.sbn']:
                    target_dir = settings.VECTOR_DIR
                elif ext in ['.tfw', '.xml']:
                    target_dir = settings.RASTER_DIR
                
                # 移动文件
                target_path = target_dir / filename
                shutil.move(str(file_path), str(target_path))
                
                # 创建 Sidecar GeoAsset
                try:
                    asset = GeoAsset(
                        name=filename,
                        file_path=str(target_path.relative_to(settings.STORAGE_DIR)),
                        file_type="附属文件",
                        sub_type=ext[1:].upper(),
                        is_sidecar=True, # 标记为附属文件
                        parent_id=parent_id
                    )
                    db.add(asset)
                except Exception as e:
                    print(f"Sidecar 创建失败 {filename}: {e}")
            
            db.commit()
                        
        except zipfile.BadZipFile:
            raise ValueError("无效的 ZIP 文件")
        finally:
            # 清理临时解压目录
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
                
        return results

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
        center_x = None
        center_y = None
        
        if tfw_path:
            tfw_data = ParserService.parse_tfw_file(tfw_path)
            width, height = ParserService.get_image_size(tif_path)
            extent = ParserService.calculate_extent(tfw_data, width, height)
            
            extent_vals = extent
            res_x = tfw_data['pixel_width']
            res_y = abs(tfw_data['pixel_height'])
            center_x = (extent_vals.get('min_x') + extent_vals.get('max_x')) / 2
            center_y = (extent_vals.get('min_y') + extent_vals.get('max_y')) / 2
            
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
            # geom_element = WKTElement(wkt, srid=srid)
            # if srid != 4326:
            #     extent_geom = func.ST_Transform(geom_element, 4326)
            # else:
            #     extent_geom = geom_element
            extent_geom = wkt # 临时降级为字符串

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
                existing.center_x = center_x
                existing.center_y = center_y
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
                extent_max_y=extent_vals.get('max_y'),
                center_x=center_x,
                center_y=center_y
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
        # query = text("""
        #     SELECT * FROM geo_assets 
        #     WHERE ST_Intersects(
        #         extent, 
        #         ST_Transform(ST_MakeEnvelope(:minX, :minY, :maxX, :maxY, :srid), 4326)
        #     )
        # """)
        
        # results = db.execute(query, {
        #     "minX": minX, "minY": minY, "maxX": maxX, "maxY": maxY, "srid": srid
        # }).fetchall()
        
        # 降级模式：如果无法使用 PostGIS，暂时返回空或做简单的属性过滤
        # 这里简单地不做过滤，或者直接返回 None 提示用户
        print("Warning: Spatial query disabled due to missing PostGIS")
        return None
        
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
