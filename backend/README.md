# Vue Map 后端 API

基于 FastAPI 的后端服务，提供用户认证和数据库连接功能。

## 功能特性

- ✅ FastAPI 框架
- ✅ MySQL 数据库连接
- ✅ SQLAlchemy ORM
- ✅ 用户注册和登录
- ✅ JWT Token 认证
- ✅ 密码加密（bcrypt）
- ✅ CORS 支持

## 技术栈

- **FastAPI** - 现代、快速的 Web 框架
- **SQLAlchemy** - Python SQL 工具包和 ORM
- **PyMySQL** - MySQL 数据库驱动
- **python-jose** - JWT 令牌处理
- **passlib** - 密码哈希和验证
- **python-dotenv** - 环境变量管理

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 数据库配置

1. 确保 MySQL 服务正在运行

2. 创建数据库：
```sql
CREATE DATABASE vue_map_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. 复制环境变量文件：
```bash
cp .env.example .env
```

4. 编辑 `.env` 文件，配置数据库连接信息：
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=vue_map_db

SECRET_KEY=your-secret-key-change-this-in-production
```

## 运行服务

```bash
# 开发模式（自动重载）
# 确保在 backend 目录下执行
uvicorn main:app --reload --port 9988
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
- `POST /api/auth/login` - 用户登录（OAuth2 格式）
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
2. 确保数据库用户有足够的权限创建表和插入数据
3. 建议在生产环境中使用环境变量管理敏感信息
4. 可以考虑添加更多的安全措施，如速率限制、IP 白名单等
