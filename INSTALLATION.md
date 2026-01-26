# 地质数据管理功能安装指南

## 1. 安装 Element Plus

```bash
npm install element-plus
```

## 2. 创建存储目录

在后端项目根目录创建 `storage` 文件夹，用于存储地质数据文件：

```bash
cd backend
mkdir storage
```

如果需要测试功能，可以将测试文件（如 `未命名(2).tif`）放入 `storage` 目录。

## 3. 启动服务

### 启动后端
```bash
cd backend
uvicorn main:app --reload --port 9988
```

### 启动前端
```bash
npm install  # 安装 Element Plus
npm run dev
```

## 4. 功能说明

### 前端功能
- 左侧 400px 宽的数据管理侧边栏
- Element Plus 表格展示文件列表
- 预览按钮：地图飞行到文件范围并显示红色虚线矩形框
- 下载按钮：下载文件到本地

### 后端 API
- `GET /api/geodata/list` - 获取文件列表
- `GET /api/geodata/download/{id}` - 下载文件

## 5. 测试数据

系统包含一个硬编码的测试数据：
- 文件名：未命名(2).tif
- 类型：栅格
- 空间范围：[116.4111, 39.9727, 116.4188, 39.9750] (WGS84)

即使 `storage` 目录为空，也会显示这个测试数据用于功能测试。
