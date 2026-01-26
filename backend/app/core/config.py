import os
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "GeoData Manager"
    API_V1_STR: str = "/api/v1"
    
    # 存储路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    RASTER_DIR: Path = STORAGE_DIR / "rasters"
    VECTOR_DIR: Path = STORAGE_DIR / "vectors"
    DOC_DIR: Path = STORAGE_DIR / "docs"

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/vue_map_db")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    def create_dirs(self):
        self.RASTER_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        self.DOC_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.create_dirs()
