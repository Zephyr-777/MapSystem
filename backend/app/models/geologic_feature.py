from sqlalchemy import Column, Integer, String, DateTime, func, JSON
from app.models.base import Base

try:
    from geoalchemy2 import Geometry
except ImportError:
    Geometry = None

class GeologicFeature(Base):
    __tablename__ = "geologic_features"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="要素名称")
    type = Column(String(50), nullable=False, comment="要素类型：点/线/面")
    
    # 存储地质属性，如 {"lithology": "granite", "age": "Jurassic"}
    properties = Column(JSON, nullable=True, comment="地质属性 (JSONB)")
    
    # PostGIS 几何字段，支持所有几何类型 (GeometryCollection)，SRID 3857 (Web Mercator)
    if Geometry:
        geometry = Column(Geometry("GEOMETRY", srid=3857), nullable=False, comment="空间几何")
    else:
        geometry = Column(String, nullable=True, comment="几何字段占位")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<GeologicFeature(id={self.id}, name={self.name}, type={self.type})>"
