import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "GeoData Manager"
    API_V1_STR: str = "/api/v1"
    APP_VERSION: str = os.getenv("APP_VERSION", "1.1.0")
    
    # 存储路径配置
    BASE_DIR: Path = BASE_DIR
    STORAGE_DIR: Path = BASE_DIR / "app" / "storage"
    RASTER_DIR: Path = STORAGE_DIR / "rasters"
    VECTOR_DIR: Path = STORAGE_DIR / "vectors"
    DOC_DIR: Path = STORAGE_DIR / "docs"
    TEMP_DIR: Path = STORAGE_DIR / "temp"

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://mengzh@localhost:5432/postgres")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3001,http://localhost:3002",
        ).split(",")
        if origin.strip()
    ]

    SMART_SEARCH_PROVIDER: str = os.getenv("SMART_SEARCH_PROVIDER", "zhipu")
    SMART_SEARCH_MODEL: str = os.getenv("SMART_SEARCH_MODEL", "glm-4.5-air")
    SMART_SEARCH_BASE_URL: str = os.getenv("SMART_SEARCH_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    SMART_SEARCH_API_KEY: str = os.getenv("SMART_SEARCH_API_KEY", "").strip()

    def create_dirs(self):
        self.RASTER_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        self.DOC_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.create_dirs()
