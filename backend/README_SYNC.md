# 地质文件同步脚本使用说明

## 功能说明

`sync_files.py` 脚本用于扫描 `backend/storage` 目录下的 `.tif` 文件，解析对应的 `.tfw` 文件（World File），并将文件信息和空间范围存入数据库。

## 安装依赖

```bash
pip install Pillow
```

或者重新安装所有依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 基本使用

```bash
cd backend
python sync_files.py
```

### 2. 文件准备

将 `.tif` 文件和对应的 `.tfw` 文件放入 `backend/storage` 目录：

```
backend/storage/
  ├── 未命名(2).tif
  └── 未命名(2).tfw
```

### 3. .tfw 文件格式说明

World File (.tfw) 是包含地理参考信息的文本文件，格式为6行：

```
0.000277777777778    (Line 1: pixel width - x方向分辨率)
0.0                  (Line 2: rotation parameter)
0.0                  (Line 3: rotation parameter)
-0.000277777777778   (Line 4: pixel height - y方向分辨率，通常是负值)
116.4111             (Line 5: 左上角 x 坐标)
39.9727              (Line 6: 左上角 y 坐标)
```

## 功能特性

1. **自动扫描**：扫描 `storage` 目录下所有 `.tif` 文件
2. **解析 .tfw**：自动查找并解析同名的 `.tfw` 文件
3. **计算 Extent**：根据图像尺寸和 .tfw 信息计算空间范围矩形
4. **去重更新**：如果数据库中已存在同名文件，则更新元数据，不重复创建
5. **错误处理**：如果找不到 .tfw 文件，仍然会保存文件信息（但没有 extent）

## 数据库表结构

`geo_assets` 表包含以下字段：

- `id` - 主键
- `name` - 文件名（唯一索引）
- `file_path` - 文件完整路径
- `file_type` - 文件类型（默认"栅格"）
- `extent_min_x`, `extent_min_y`, `extent_max_x`, `extent_max_y` - 空间范围
- `width`, `height` - 图像尺寸（像素）
- `resolution_x`, `resolution_y` - 分辨率
- `created_at`, `updated_at` - 创建和更新时间

## 输出示例

```
============================================================
地质文件同步脚本
============================================================
存储目录: /path/to/backend/storage

检查数据库表...
✓ 数据库表已就绪

找到 1 个 .tif 文件

处理文件: 未命名(2).tif
  找到 .tfw 文件: 未命名(2).tfw
  图像尺寸: 2768 x 1624
  Extent: [116.4111, 39.9712, 116.4188, 39.9727]
  分辨率: 0.000277777777778 x 0.000277777777778
  ✓ 创建新数据库记录

同步完成:
  成功: 1
  创建: 1
  更新: 0
  错误: 0
```

## 注意事项

1. 确保 `.tfw` 文件的坐标系统与前端使用的一致（通常是 WGS84，EPSG:4326）
2. 如果图像是地理坐标系（经纬度），`pixel_height` 通常是负值
3. 脚本会自动创建 `geo_assets` 表（如果不存在）
4. 运行脚本前确保数据库连接配置正确（`.env` 文件）
