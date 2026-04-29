#!/bin/bash

# 启动后端服务脚本

echo "启动 Vue Map 后端服务..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，请从 .env.example 复制并配置"
    cp .env.example .env
    echo "已创建 .env 文件，请编辑配置后重新运行"
    exit 1
fi

# 启动服务
echo "执行数据库迁移..."
alembic upgrade head

echo "确保默认管理员用户存在..."
python create_test_user.py

echo "启动服务..."
# 排除 venv 目录，避免 WatchFiles 监听过多文件导致崩溃
uvicorn app.main:app --host 0.0.0.0 --reload --reload-exclude "venv/*" --port 9988
