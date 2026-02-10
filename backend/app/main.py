from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import geodata, auth
from app.core.config import settings
from app.models.base import Base
from app.core.database import engine, init_postgis

# 初始化数据库
init_postgis()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="地图应用后端API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3001",
        "http://localhost:3002"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(geodata.router, prefix="/api/geodata", tags=["地质数据"])

@app.get("/")
async def root():
    return {"message": "Vue Map API Server"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9988)
