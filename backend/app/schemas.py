from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Literal, Optional
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str] = None
    role: str = "guest"
    is_active: bool
    created_at: datetime

# Token 响应
class TokenResponse(BaseModel):
    token: str
    user: UserResponse

# Token 数据
class TokenData(BaseModel):
    username: Optional[str] = None

# 地质数据项
class GeoDataItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    uploadTime: str
    extent: Optional[list[float]] = None  # [minX, minY, maxX, maxY]
    srid: Optional[int] = None  # 坐标系统 EPSG 代码（如 3857 或 4326）
    exists: Optional[bool] = None  # 文件是否存在于磁盘
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    distance: Optional[float] = None  # 距离 (米)
    description: Optional[str] = None
    image_path: Optional[str] = None  # 优化预览图片路径
    sub_type: Optional[str] = None
    dataset_id: Optional[str] = None
    bbox: Optional[list[float]] = None
    time_range: Optional[str] = None
    download_url: Optional[str] = None
    asset_family: Optional[str] = None
    render_mode: Optional[str] = None
    overlay_supported: bool = False
    index_point_enabled: bool = True
    downloadable: bool = True
    overlay_id: Optional[str] = None
    source: str = "internal"

# 地质数据列表响应
class GeoDataListResponse(BaseModel):
    data: list[GeoDataItem]
    total: int


class SmartSearchConfig(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True


class SmartSearchRequest(BaseModel):
    query: str
    config: Optional[SmartSearchConfig] = None


class SmartSearchResponse(GeoDataListResponse):
    mode: Literal["ai", "fallback"] = "fallback"
    reason: Optional[str] = None


class LocalRasterOverlayResponse(BaseModel):
    id: str
    name: str
    extent: list[float]
    srid: int = 4326
    min_zoom: int = 8
    opacity: int = 75
    center_x: Optional[float] = None
    center_y: Optional[float] = None
    description: Optional[str] = None
    source_path: Optional[str] = None
    raster_url: Optional[str] = None
    band_count: Optional[int] = None
    dtype: Optional[str] = None
    nodata: Optional[float] = None
    raster_min: Optional[float] = None
    raster_max: Optional[float] = None
