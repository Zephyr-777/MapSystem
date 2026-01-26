from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="附件名称")
    file_path = Column(String(500), nullable=False, comment="附件存储路径")
    file_type = Column(String(50), nullable=True, comment="文件类型 (pdf/img/excel)")
    
    # 外键关联到 GeoAsset
    geo_asset_id = Column(Integer, ForeignKey("geo_assets.id"), nullable=False, comment="关联的地质资产ID")
    
    # 建立关系
    geo_asset = relationship("GeoAsset", back_populates="attachments")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Attachment(id={self.id}, name={self.name}, asset_id={self.geo_asset_id})>"
