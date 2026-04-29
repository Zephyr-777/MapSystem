import os

import psycopg2
from dotenv import load_dotenv

from app.core.security import get_password_hash

# 加载环境变量
load_dotenv()

# 数据库连接参数
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'vue_map_db')
DB_USER = os.getenv('POSTGRES_USER', 'mengzh')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

DEFAULT_USERS = [
    ("test", "test@example.com", "test"),
    ("admin", "admin@example.com", "admin"),
]

# 连接数据库并插入测试用户
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()
    
    for username, email, password in DEFAULT_USERS:
        cur.execute(
            """INSERT INTO users (username, email, password_hash, role, is_active)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (username) DO UPDATE SET
                   email = EXCLUDED.email,
                   role = 'admin',
                   is_active = TRUE""",
            (username, email, get_password_hash(password), 'admin', True)
        )
    
    conn.commit()
    print("默认管理员用户已就绪：")
    for username, _email, password in DEFAULT_USERS:
        print(f"用户名: {username} / 密码: {password}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"创建测试用户失败: {e}")
