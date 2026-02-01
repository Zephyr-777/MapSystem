from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# 用户注册请求
class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None

# 用户登录请求
class UserLogin(BaseModel):
    username: str
    password: str

# 用户响应
class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Token 响应
class TokenResponse(BaseModel):
    token: str
    user: UserResponse

# Token 数据
class TokenData(BaseModel):
    username: Optional[str] = None

# 地质数据项
class GeoDataItem(BaseModel):
    id: int
    name: str
    type: str
    uploadTime: str
    extent: Optional[list[float]] = None  # [minX, minY, maxX, maxY]
    srid: Optional[int] = None  # 坐标系统 EPSG 代码（如 3857 或 4326）
    exists: Optional[bool] = None  # 文件是否存在于磁盘
    center_x: Optional[float] = None
    center_y: Optional[float] = None

    class Config:
        from_attributes = True

# 地质数据列表响应
class GeoDataListResponse(BaseModel):
    data: list[GeoDataItem]
    total: int
