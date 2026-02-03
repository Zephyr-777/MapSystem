import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

def check_database():
    print("正在检查数据库连接...")
    
    # 获取数据库连接 URL
    # 优先使用环境变量，否则使用默认值（与 config.py 保持一致）
    database_url = os.getenv("DATABASE_URL", "postgresql://mengzh@localhost:5432/postgres")
    # 适配 sqlalchemy
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
    
    print(f"尝试连接到: {database_url}")
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ 数据库连接成功！")
            
            # 检查 PostGIS 扩展
            try:
                result = connection.execute(text("SELECT PostGIS_Version()"))
                version = result.scalar()
                print(f"✅ PostGIS 扩展已安装: {version}")
            except Exception as e:
                print("❌ PostGIS 扩展检查失败 (可能是未安装或权限不足)")
                print(f"   错误信息: {e}")
                
    except Exception as e:
        print("❌ 数据库连接失败！")
        print(f"   错误信息: {e}")
        print("\n可能的原因:")
        print("1. PostgreSQL 服务未启动")
        print("2. 数据库用户名或密码错误")
        print("3. 数据库不存在")
        print("4. 端口 5432 被占用或不允许连接")
        sys.exit(1)

if __name__ == "__main__":
    check_database()
