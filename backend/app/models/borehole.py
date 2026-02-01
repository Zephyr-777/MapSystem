from sqlalchemy import Column, Integer, String, Float, DateTime, func, JSON
from app.models.base import Base

class Borehole(Base):
    """
    钻孔模型
    """
    __tablename__ = "boreholes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True, comment="钻孔编号/名称")
    
    # 空间位置 (WGS84)
    longitude = Column(Float, nullable=False, comment="经度")
    latitude = Column(Float, nullable=False, comment="纬度")
    elevation = Column(Float, nullable=True, comment="孔口标高")
    depth = Column(Float, nullable=True, comment="孔深")
    
    # 扩展属性
    properties = Column(JSON, nullable=True, comment="其他属性")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Borehole(id={self.id}, name={self.name})>"
