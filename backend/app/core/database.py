import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# PostgreSQL / PostGIS
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base is now imported from app.models.base
from app.models.base import Base

# Import all models to ensure they are registered with Base.metadata
from app.models.geo_asset import GeoAsset
from app.models.user import User
from app.models.geologic_feature import GeologicFeature
from app.models.attachment import Attachment


def init_postgis() -> None:
    """
    确保 PostGIS 扩展已启用（需要数据库具备创建扩展权限）。
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to initialize PostGIS: {e}")
        print("Spatial features may not work correctly.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
