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
│   ├── routers/          # 路由
│   │   └── auth.py       # 认证路由
│   ├── database.py       # 数据库配置
│   ├── models.py         # 数据模型
│   ├── schemas.py        # Pydantic 模式
│   ├── utils.py          # 工具函数
│   ├── main.py           # 主应用入口
│   ├── requirements.txt  # Python 依赖
│   └── README.md         # 后端文档
├── src/                  # 前端源码
│   ├── api/              # API 服务
│   │   └── auth.ts       # 认证相关 API
│   ├── layouts/          # 布局组件
│   │   └── MainLayout.vue # 主布局（侧边栏）
│   ├── views/            # 页面组件
│   │   ├── Login.vue     # 登录页面
│   │   ├── Register.vue  # 注册页面
│   │   └── MapView.vue   # 地图视图
│   ├── router/           # 路由配置
│   │   └── index.ts
│   ├── stores/           # Pinia 状态管理
│   │   └── auth.ts       # 认证状态
│   ├── App.vue           # 根组件
│   ├── main.ts           # 入口文件
│   ├── env.d.ts          # 环境变量类型定义
│   └── style.css         # 全局样式
├── index.html            # HTML 模板
├── package.json          # 前端依赖配置
├── vite.config.ts        # Vite 配置
└── .env.example          # 环境变量示例
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
   - 确保 MySQL 服务正在运行
   - 创建数据库：
   ```sql
   CREATE DATABASE vue_map_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

5. **配置环境变量**：
```bash
cp .env.example .env
```
   编辑 `.env` 文件，配置数据库连接信息：
   ```
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DATABASE=vue_map_db
   SECRET_KEY=your-secret-key-change-this-in-production
   ```

6. **启动后端服务**：
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
```bash
cp .env.example .env
```
   编辑 `.env` 文件：
   ```
   VITE_API_BASE_URL=http://localhost:9988
   ```

3. **启动开发服务器**：
```bash
npm run dev
```
   前端将在 `http://localhost:3000` 或 `http://localhost:5173` 启动

## 使用说明

1. **启动后端和前端服务**（需要分别启动）

2. **访问应用**：
   - 打开浏览器访问前端地址
   - 首先会显示登录页面
   - 点击"立即注册"可以跳转到注册页面
   - 注册新用户或登录现有用户
   - 登录成功后进入主界面，可以看到侧边栏和地图
   - 侧边栏可以折叠/展开
   - 点击"退出登录"可以返回登录页面

3. **查看 API 文档**：
   - Swagger UI: http://localhost:9988/docs
   - ReDoc: http://localhost:9988/redoc

## 地图功能

- ✅ OpenLayers 地图集成
- ✅ 使用 OpenStreetMap 底图
- ✅ 默认中心：北京（116.3974, 39.9093）
- ✅ 支持缩放和拖拽操作

## API 接口说明

后端提供以下 API 接口：

### 认证接口

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login/json` - 用户登录（JSON 格式）
- `GET /api/auth/me` - 获取当前用户信息（需要认证）

### 请求示例

**注册用户**：
```bash
POST /api/auth/register
Content-Type: application/json

{
  "username": "user123",
  "password": "password123",
  "email": "user@example.com"
}
```

**登录**：
```bash
POST /api/auth/login/json
Content-Type: application/json

{
  "username": "user123",
  "password": "password123"
}
```

**获取当前用户信息**：
```bash
GET /api/auth/me
Authorization: Bearer YOUR_TOKEN_HERE
```

### 响应格式

```json
{
  "token": "jwt_token_here",
  "user": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  }
}
```

## 数据库连接

后端使用 MySQL 数据库，通过 SQLAlchemy ORM 进行数据库操作。

### 数据库表结构

**users 表**：
- `id` - 主键（自增）
- `username` - 用户名（唯一索引）
- `email` - 邮箱（唯一索引，可选）
- `password_hash` - 密码哈希（bcrypt）
- `is_active` - 是否激活
- `created_at` - 创建时间
- `updated_at` - 更新时间

### 数据库配置

数据库连接配置在后端 `.env` 文件中：
- `MYSQL_HOST` - MySQL 主机地址
- `MYSQL_PORT` - MySQL 端口
- `MYSQL_USER` - MySQL 用户名
- `MYSQL_PASSWORD` - MySQL 密码
- `MYSQL_DATABASE` - 数据库名称

启动后端服务时，会自动创建数据库表（如果不存在）。

## 参考资源

- [vue3-openlayers 文档](https://vue3openlayers.netlify.app/)
- [OpenLayers 官方文档](https://openlayers.org/)
- [Vue 3 文档](https://vuejs.org/)
