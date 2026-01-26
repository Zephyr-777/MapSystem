@echo off
REM Windows 启动脚本

echo 启动 Vue Map 后端服务...

REM 检查虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt

REM 检查 .env 文件
if not exist ".env" (
    echo 警告: .env 文件不存在，请从 .env.example 复制并配置
    copy .env.example .env
    echo 已创建 .env 文件，请编辑配置后重新运行
    pause
    exit /b 1
)

REM 启动服务
echo 启动服务...
uvicorn main:app --reload --port 9988

pause
