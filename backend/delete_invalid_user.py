#!/usr/bin/env python3
"""
删除无效的用户记录，该记录的密码哈希是明文密码，导致登录失败
"""

from sqlalchemy import create_engine, text
from database import DATABASE_URL

print("=== 删除无效的用户记录 ===")
print(f"使用数据库: {DATABASE_URL}")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 删除无效用户记录
try:
    with engine.connect() as conn:
        # 查询并显示要删除的用户
        query = text("SELECT id, username, password_hash FROM users WHERE password_hash = '123456';")
        result = conn.execute(query)
        user = result.fetchone()
        
        if user:
            id, username, password_hash = user
            print(f"⚠️  找到无效用户: ID={id}, 用户名={username}, 密码哈希={password_hash} (明文密码)")
            
            # 删除该用户
            delete_query = text("DELETE FROM users WHERE id = :id;")
            conn.execute(delete_query, {"id": id})
            conn.commit()
            
            print(f"✅ 已成功删除无效用户: {username}")
        else:
            print("✅ 未找到密码哈希为 '123456' 的无效用户")
    
    print("\n=== 清理完成 ===")
except Exception as e:
    print(f"❌ 清理失败: {e}")
    import traceback
    traceback.print_exc()
