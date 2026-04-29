# 地质数据获取与展示方案

**作者**：孟泽晖  
**日期**：2026 年 3 月  
**目标**：实现点击地质点后显示关联的图像（如 TIF 文件）

---

## 📍 一、地质数据来源

### 1.1 系统现有数据来源

你的系统支持**3 种地质数据**的存储和管理：

#### （1）栅格数据（Raster）
- **格式**：GeoTIFF (.tif, .tiff)
- **用途**：遥感影像、数字高程模型（DEM）、地质解译图
- **存储位置**：`backend/app/storage/rasters/`
- **示例**：
  ```
  北京地区遥感影像.tif
  华北地区 DEM.tif
  地质构造解译图.tif
  ```

#### （2）矢量数据（Vector）
- **格式**：Shapefile (.shp + .dbf + .shx + .prj)
- **用途**：地质构造线、断层分布、采样点位置
- **存储位置**：`backend/app/storage/vectors/`
- **示例**：
  ```
  华北地区断裂带.shp
  地震采样点.shp
  矿产资源分布.shp
  ```

#### （3）科学数据（NetCDF）
- **格式**：NetCDF (.nc, .nc4)
- **用途**：气象数据、海洋数据、地球物理场数据
- **存储位置**：`backend/app/storage/`
- **示例**：
  ```
  中国地区温度场.nc
  降水数据.nc
  重力场数据.nc
  ```

---

### 1.2 外部数据源推荐

如果你需要获取更多地质数据，推荐以下免费数据源：

#### 国内数据源

| 数据源名称 | 网址 | 数据类型 | 说明 |
|-----------|------|---------|------|
| **中国地质调查局** | http://www.cgs.gov.cn/ | 地质图、矿产数据 | 官方权威数据 |
| **地质云** | https://geocloud.cgs.gov.cn/ | 综合地质数据 | 提供在线服务和下载 |
| **资源环境科学与数据中心** | http://www.resdc.cn/ | 土地利用、遥感影像 | 免费开放部分数据 |
| **国家地球系统科学数据中心** | http://www.geodata.cn/ | 多学科数据 | 地质、气象、海洋等 |

#### 国际数据源

| 数据源名称 | 网址 | 数据类型 | 说明 |
|-----------|------|---------|------|
| **USGS EarthExplorer** | https://earthexplorer.usgs.gov/ | Landsat、DEM | 免费遥感影像 |
| **NASA Earthdata** | https://search.earthdata.nasa.gov/ | 多源遥感数据 | 气象、海洋、陆地 |
| **Copernicus Open Access Hub** | https://scihub.copernicus.eu/ | Sentinel 系列 | 欧洲航天局数据 |
| **OneGeology** | http://www.onegeology.org/ | 全球地质图 | 1:100 万地质图 |

---

### 1.3 如何获取测试数据

#### 方法 1：使用公开数据（推荐）

**步骤 1**：下载 USGS Landsat 影像
```bash
1. 访问 https://earthexplorer.usgs.gov/
2. 注册账号（免费）
3. 选择研究区域（如北京）
4. 选择 Landsat 8 OLI/TIRS
5. 选择无云覆盖的场景
6. 下载 Level-1 产品（.tif 格式）
```

**步骤 2**：下载 SRTM DEM 数据
```bash
1. 访问 https://earthexplorer.usgs.gov/
2. 在 Data Sets 中选择 Digital Elevation > SRTM
3. 选择区域
4. 下载 1 Arc-Second Global（30 米分辨率）
```

**步骤 3**：放入系统存储目录
```bash
# 将下载的数据放入对应目录
cp ~/Downloads/LC08_L1TP_123032_20200101_*.TIF backend/app/storage/rasters/
cp ~/Downloads/SRTM1N40E116.tif backend/app/storage/rasters/
```

#### 方法 2：使用系统已有测试数据

如果你的系统已经有测试数据（如 `未命名 (2).tif`），可以直接使用。

检查存储目录：
```bash
cd /Users/mengzh/Desktop/vue-map/backend/app/storage
ls -la
```

---

## 🎨 二、地质数据呈现方式

### 2.1 你期望的功能

> **需求**：点击每个地质点后，在右侧地质信息卡片的下方显示相应的图像（如 TIF）

这个功能非常实用！想象一下这样的场景：
- 用户在地图上点击一个**地震采样点**
- 右侧显示该点的详细信息（名称、坐标、岩性等）
- **下方自动显示该位置最近的遥感影像**
- 用户可以直观地看到该点的地形地貌

---

### 2.2 技术实现方案

我为你设计了**两种实现方式**：

#### 方案 A：自动关联最近的栅格图像（推荐）

**原理**：
1. 用户点击一个地质点（矢量数据）
2. 系统自动查找离该点**最近的栅格图像**（TIF）
3. 在信息卡片下方显示该 TIF 图像的预览

**优点**：
- 无需手动关联，自动匹配
- 用户体验好，直观展示

**缺点**：
- 需要系统中有栅格数据
- 可能不是最相关的图像

**适用场景**：系统同时有矢量点和栅格影像数据

---

#### 方案 B：手动关联特定图像

**原理**：
1. 在数据库中为每个地质点添加 `image_path` 字段
2. 上传数据时指定关联的图像文件
3. 点击时显示指定的图像

**优点**：
- 精确控制显示哪个图像
- 可以关联多个图像（如不同时期的遥感影像）

**缺点**：
- 需要额外的人工操作
- 数据结构需要调整

**适用场景**：需要精确控制关联关系

---

### 2.3 推荐方案：方案 A（自动关联）

下面我会详细说明如何实现方案 A。

---

## 💻 三、具体实现步骤

### 3.1 后端实现

#### 步骤 1：修改详情接口，添加关联图像信息

**文件**：`backend/app/api/v1/geodata.py`

在 `get_geodata_detail` 接口中添加查找最近栅格图像的逻辑：

```python
@router.get("/detail/{id}")
async def get_geodata_detail(id: int, db: Session = Depends(get_db)):
    """获取地质数据详情及关联图像"""
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="数据不存在")
    
    # 获取元数据
    full_path = settings.STORAGE_DIR / asset.file_path
    metadata = SpatialService.extract_metadata(full_path) if full_path.exists() else {}
    
    # 🆕 查找最近的栅格图像
    associated_image = None
    if asset.center_x and asset.center_y:
        # 使用 PostGIS 空间查询查找最近的栅格
        from sqlalchemy import text
        query = text("""
            SELECT id, name, file_path, center_x, center_y
            FROM geo_assets
            WHERE file_type = '栅格'
              AND is_sidecar = FALSE
              AND center_x IS NOT NULL
              AND center_y IS NOT NULL
            ORDER BY ST_Distance(
                geography(ST_SetSRID(ST_MakePoint(center_x, center_y), 4326)),
                geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            )
            LIMIT 1
        """)
        
        result = db.execute(query, {"lon": asset.center_x, "lat": asset.center_y}).first()
        
        if result:
            associated_image = {
                "id": result.id,
                "name": result.name,
                "file_path": result.file_path,
                "preview_url": f"/api/geodata/preview/{result.id}",
                "download_url": f"/api/geodata/download/{result.id}"
            }
    
    return {
        "id": asset.id,
        "name": asset.name,
        "type": asset.file_type,
        "center_x": asset.center_x,
        "center_y": asset.center_y,
        "metadata": metadata,
        "associated_image": associated_image  # 🆕 返回关联图像信息
    }
```

---

#### 步骤 2：添加图像预览接口（如果还没有）

**文件**：`backend/app/api/v1/geodata.py`

添加生成 TIF 图像预览的功能：

```python
@router.get("/preview/{id}")
async def preview_geodata(id: int, db: Session = Depends(get_db)):
    """生成地质数据的预览图（JPEG 格式）"""
    asset = db.query(GeoAsset).filter(GeoAsset.id == id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="数据不存在")
    
    full_path = settings.STORAGE_DIR / asset.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 读取 TIF 文件并生成预览
    from PIL import Image
    import io
    
    try:
        with Image.open(full_path) as img:
            # 转换为 RGB（如果原来是灰度或多波段）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 生成缩略图（最大 800x600）
            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
            
            # 保存到内存
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            return StreamingResponse(
                buffer,
                media_type="image/jpeg",
                headers={"Content-Disposition": f"inline; filename=preview_{id}.jpg"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成预览失败：{str(e)}")
```

---

### 3.2 前端实现

#### 步骤 1：修改 API 接口定义

**文件**：`src/api/geodata.ts`

添加获取详情的接口：

```typescript
export interface GeoDataDetail {
  id: number
  name: string
  type: string
  center_x?: number
  center_y?: number
  metadata?: any
  associated_image?: {
    id: number
    name: string
    file_path: string
    preview_url: string
    download_url: string
  }
}

export const geoDataApi = {
  // ... 现有接口 ...
  
  // 🆕 获取地质数据详情
  getDetail: (id: number) => {
    return api.get<GeoDataDetail>(`/api/geodata/detail/${id}`)
  },
  
  // 🆕 获取图像预览
  getPreview: (id: number) => {
    return `${API_BASE_URL}/api/geodata/preview/${id}`
  }
}
```

---

#### 步骤 2：修改右侧信息卡片组件

**文件**：`src/views/MapView.vue` 或 `src/components/map/components/InfoPanel.vue`

在右侧信息卡片中添加图像显示区域：

```vue
<template>
  <div class="info-panel">
    <!-- 现有信息卡片内容 -->
    <div class="info-header">
      <h3>{{ currentFeature?.name || '详细信息' }}</h3>
    </div>
    
    <div class="info-body">
      <!-- 基本信息 -->
      <el-descriptions :column="1" size="small">
        <el-descriptions-item label="类型">
          {{ currentFeature?.type }}
        </el-descriptions-item>
        <el-descriptions-item label="坐标">
          {{ formatCoords(currentFeature?.center) }}
        </el-descriptions-item>
      </el-descriptions>
      
      <!-- 🆕 关联图像显示区域 -->
      <div v-if="associatedImage" class="associated-image-section">
        <div class="image-header">
          <h4>📍 关联影像</h4>
          <el-tag size="small" type="info">
            {{ associatedImage.name }}
          </el-tag>
        </div>
        
        <div class="image-container">
          <!-- 预览图 -->
          <img 
            :src="geoDataApi.getPreview(associatedImage.id)" 
            :alt="associatedImage.name"
            class="preview-image"
            @click="handleImageClick(associatedImage)"
          />
          
          <!-- 操作按钮 -->
          <div class="image-actions">
            <el-button 
              size="small" 
              type="primary" 
              icon="Download" 
              @click="handleDownloadImage(associatedImage)"
            >
              下载
            </el-button>
            <el-button 
              size="small" 
              icon="ZoomIn" 
              @click="handleImageClick(associatedImage)"
            >
              查看大图
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- loading 状态 -->
      <div v-else-if="loadingImage" class="loading-image">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在加载影像...</span>
      </div>
      
      <!-- 无关联图像提示 -->
      <div v-else class="no-image-tip">
        <el-empty :image-size="100" description="暂无关联影像" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { geoDataApi, type GeoDataDetail } from '@/api/geodata'

const currentFeature = ref<any>(null)
const associatedImage = ref<any>(null)
const loadingImage = ref(false)

// 监听要素变化，加载关联图像
watch(currentFeature, async (newFeature) => {
  if (newFeature?.id) {
    loadingImage.value = true
    try:
      // 获取详情（包含关联图像信息）
      const detail = await geoDataApi.getDetail(newFeature.id)
      associatedImage.value = detail.associated_image || null
    } catch (error) {
      console.error('加载关联图像失败:', error)
      associatedImage.value = null
    } finally {
      loadingImage.value = false
    }
  } else {
    associatedImage.value = null
  }
}, { immediate: true })

// 格式化坐标显示
const formatCoords = (coords?: [number, number]) => {
  if (!coords) return '未知'
  return `${coords[1].toFixed(4)}°N, ${coords[0].toFixed(4)}°E`
}

// 下载图像
const handleDownloadImage = async (image: any) => {
  try:
    const blob = await geoDataApi.download(image.id)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = image.name
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 查看大图（可以用 Dialog 或新窗口）
const handleImageClick = (image: any) => {
  // 实现查看大图逻辑
  window.open(geoDataApi.getPreview(image.id), '_blank')
}
</script>

<style scoped>
.associated-image-section {
  margin-top: 20px;
  border-top: 1px solid #e4e7ed;
  padding-top: 15px;
}

.image-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.image-header h4 {
  margin: 0;
  font-size: 14px;
  color: #303133;
}

.image-container {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.preview-image {
  width: 100%;
  max-height: 400px;
  object-fit: cover;
  cursor: pointer;
  transition: transform 0.3s;
}

.preview-image:hover {
  transform: scale(1.05);
}

.image-actions {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  gap: 10px;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-container:hover .image-actions {
  opacity: 1;
}

.loading-image {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}

.no-image-tip {
  padding: 20px;
}
</style>
```

---

## 📊 四、数据关系说明

### 4.1 地质点与图像的关系
