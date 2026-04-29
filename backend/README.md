# Vue Map 后端 API

基于 FastAPI 的后端服务，提供用户认证、空间数据管理、地质要素检索与文件上传处理功能。

## 功能特性

- ✅ FastAPI 框架
- ✅ PostgreSQL / PostGIS 数据库连接
- ✅ SQLAlchemy ORM
- ✅ 用户注册和登录
- ✅ JWT Token 认证
- ✅ GeoTIFF / Shapefile / NetCDF 元数据处理
- ✅ 密码加密（pbkdf2_sha256，兼容 bcrypt）
- ✅ CORS 支持

## 技术栈

- **FastAPI** - 现代、快速的 Web 框架
- **SQLAlchemy** - Python SQL 工具包和 ORM
- **psycopg2** - PostgreSQL 数据库驱动
- **PostGIS** - 空间扩展
- **python-jose** - JWT 令牌处理
- **passlib** - 密码哈希和验证
- **python-dotenv** - 环境变量管理

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 数据库配置

1. 确保 PostgreSQL 与 PostGIS 服务正在运行

2. 创建数据库：
```sql
CREATE DATABASE vue_map_db;
\c vue_map_db
CREATE EXTENSION postgis;
```

3. 复制环境变量文件：
```bash
cp .env.example .env
```

4. 编辑 `.env` 文件，配置数据库连接信息：
```env
DATABASE_URL=postgresql://username:password@localhost:5432/vue_map_db
SECRET_KEY=your-secret-key-change-this-in-production
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## 运行服务

```bash
# 开发模式（自动重载）
uvicorn app.main:app --reload --port 9988
```

或者使用启动脚本：
```bash
./start.sh
```

服务将在 `http://localhost:9988` 启动

## API 文档

启动服务后，可以访问以下地址查看 API 文档：

- Swagger UI: http://localhost:9988/docs
- ReDoc: http://localhost:9988/redoc

## API 端点

### 认证相关

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login/json` - 用户登录（JSON 格式）
- `GET /api/auth/me` - 获取当前用户信息（需要认证）

### 健康检查

- `GET /` - 根路径
- `GET /api/health` - 健康检查

## 请求示例

### 注册用户

```bash
curl -X POST "http://localhost:9988/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "email": "test@example.com"
  }'
```

### 登录

```bash
curl -X POST "http://localhost:9988/api/auth/login/json" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

### 获取当前用户信息

```bash
curl -X GET "http://localhost:9988/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 测试

```bash
pytest
```

## 数据库模型

### User 表

- `id` - 主键
- `username` - 用户名（唯一）
- `email` - 邮箱（唯一，可选）
- `password_hash` - 密码哈希
- `is_active` - 是否激活
- `created_at` - 创建时间
- `updated_at` - 更新时间

## 注意事项

1. 生产环境中请务必修改 `SECRET_KEY` 为强随机字符串
2. 确保数据库用户有足够的权限创建扩展、建表和写入数据
3. 建议通过环境变量配置 `DATABASE_URL`、`SECRET_KEY` 与 `BACKEND_CORS_ORIGINS`
4. 未配置 `DASHSCOPE_API_KEY` 时，智能分类与智能搜索会自动降级为本地规则逻辑
