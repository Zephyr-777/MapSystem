from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.v1 import geodata, auth, geology, download
from app.core.config import settings
from app.core.database import init_postgis

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 初始化 PostGIS 扩展（建表迁移由 Alembic 管理）
    init_postgis()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="地图应用后端API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Range", "Accept-Ranges"],
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(geodata.router, prefix="/api/geodata", tags=["地质数据"])
app.include_router(geology.router, prefix="/api/geology", tags=["虚拟地质数据"])
app.include_router(download.router, prefix="/api/download", tags=["数据下载"])

@app.get("/")
async def root():
    return {"message": "Vue Map API Server"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9988)
