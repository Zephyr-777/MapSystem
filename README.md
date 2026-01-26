# Vue Map - OpenLayers 集成项目

这是一个基于 Vue 3 和 OpenLayers 的地图应用，包含登录注册功能和侧边栏布局。

## 功能特性

- ✅ 用户登录和注册界面（参考 KnowledgeQuery 设计风格）
- ✅ 侧边栏导航布局
- ✅ OpenLayers 地图集成
- ✅ Vue Router 路由管理
- ✅ Pinia 状态管理
- ✅ Axios API 服务集成
- ✅ JWT Token 认证
- ✅ 数据库连接配置（后端 API）

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 下一代前端构建工具
- **Vue Router** - 官方路由管理器
- **Pinia** - Vue 的状态管理库
- **vue3-openlayers** - Vue 3 的 OpenLayers 组件库
- **OpenLayers** - 高性能地图库
- **Axios** - HTTP 客户端

## 安装依赖

```bash
npm install
```

## 开发运行

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动

## 构建生产版本

```bash
npm run build
```

## 项目结构

```
vue-map/
├── backend/              # 后端服务
│   ├── app/              # 应用逻辑 (DDD)
│   │   ├── api/v1/       # 路由接口
│   │   ├── core/         # 核心配置
│   │   ├── models/       # 数据库模型
│   │   └── services/     # 业务服务
│   ├── storage/          # 文件存储
│   ├── database.py       # 数据库连接
│   ├── main.py           # 入口文件
│   └── requirements.txt  # Python 依赖
├── src/                  # 前端源码
│   ├── api/              # API 服务
│   ├── layouts/          # 布局组件
│   ├── views/            # 页面组件
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia 状态管理
│   ├── App.vue           # 根组件
│   └── main.ts           # 入口文件
├── index.html            # HTML 模板
├── package.json          # 前端依赖配置
└── vite.config.ts        # Vite 配置
```

## 快速开始

### 后端设置

1. **进入后端目录**：
```bash
cd backend
```

2. **创建虚拟环境**（推荐）：
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

3. **安装 Python 依赖**：
```bash
pip install -r requirements.txt
```

4. **配置数据库**：
   - 确保 PostgreSQL + PostGIS 服务正在运行
   - 创建数据库：
   ```sql
   CREATE DATABASE vue_map_db;
   CREATE EXTENSION postgis;
   ```

5. **启动后端服务**：
```bash
uvicorn main:app --reload --port 9988
```
   后端将在 `http://localhost:9988` 启动

### 前端设置

1. **安装依赖**：
```bash
npm install
```

2. **配置环境变量**：
   编辑 `.env` 文件：
   ```
   VITE_API_BASE_URL=http://localhost:9988
   ```

3. **启动开发服务器**：
```bash
npm run dev
```
   前端将在 `http://localhost:3000` 或 `http://localhost:5173` 启动

## 数据库连接

后端使用 PostgreSQL 数据库，通过 SQLAlchemy ORM 进行数据库操作，并集成了 PostGIS 处理空间数据。

### 数据库表结构

**geo_assets 表**：
- `id` - 主键
- `name` - 文件名
- `file_path` - 相对存储路径
- `extent` - 空间范围 (PostGIS Geometry)
- `srid` - 坐标系 ID

## 参考资源

- [vue3-openlayers 文档](https://vue3openlayers.netlify.app/)
- [OpenLayers 官方文档](https://openlayers.org/)
- [Vue 3 文档](https://vuejs.org/)
