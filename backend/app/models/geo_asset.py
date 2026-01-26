from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from app.models.base import Base

try:
    from geoalchemy2 import Geometry
except ImportError:
    Geometry = None

class GeoAsset(Base):
    __tablename__ = "geo_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, index=True, nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    
    # 原始 file_type 字段保留，用于向后兼容或大类区分
    file_type = Column(String(50), nullable=False, default="栅格", comment="文件类型")
    
    # 新增 sub_type 字段区分多元数据
    sub_type = Column(String(50), nullable=True, comment="子类型：影像/矢量/钻孔/文档")

    # PostGIS 空间范围
    # 强制使用 SRID 4326
    extent = Column(Geometry("POLYGON", srid=4326), nullable=True, comment="空间范围 Polygon") if Geometry else Column(String(50), nullable=True, comment="extent 占位")
    
    # 坐标系统 SRID（从 .prj 文件识别）
    srid = Column(Integer, nullable=True, default=4326, comment="坐标系统 EPSG 代码")

    # 兼容字段
    extent_min_x = Column(Float, nullable=True)
    extent_min_y = Column(Float, nullable=True)
    extent_max_x = Column(Float, nullable=True)
    extent_max_y = Column(Float, nullable=True)
    
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    resolution_x = Column(Float, nullable=True)
    resolution_y = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<GeoAsset(id={self.id}, name={self.name})>"
