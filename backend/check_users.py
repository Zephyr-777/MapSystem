#!/usr/bin/env python3
"""
检查数据库中的用户记录，了解密码哈希格式
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.database import DATABASE_URL

print("=== 检查数据库中的用户记录 ===")
print(f"使用数据库: {DATABASE_URL}")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 检查用户表记录
try:
    with engine.connect() as conn:
        # 查询所有用户记录
        query = text("SELECT id, username, email, password_hash, is_active, created_at FROM users;")
        result = conn.execute(query)
        
        users = result.fetchall()
        
        if not users:
            print("✅ 数据库中没有用户记录")
        else:
            print(f"📊 找到 {len(users)} 个用户记录:")
            print("=" * 80)
            print(f"{'ID':<5} {'用户名':<15} {'邮箱':<25} {'密码哈希前50字符':<55} {'激活状态':<10} {'创建时间':<25}")
            print("=" * 130)
            
            for user in users:
                id, username, email, password_hash, is_active, created_at = user
                
                # 处理None值
                username = username or "无"
                email = email or "无"
                hash_prefix = password_hash[:50] if password_hash else "无"
                is_active = str(is_active) if is_active is not None else "未知"
                created_at = str(created_at) if created_at else "未知"
                
                print(f"{id:<5} {username:<15} {email:<25} {hash_prefix:<55} {is_active:<10} {created_at:<25}")
            
            print("=" * 130)
            
            # 分析密码哈希格式
            for user in users:
                _, username, _, password_hash, _, _ = user
                if password_hash:
                    print(f"\n🔍 用户 {username} 的密码哈希格式分析:")
                    print(f"   完整哈希: {password_hash}")
                    print(f"   长度: {len(password_hash)}")
                    print(f"   前缀: {password_hash.split('$')[0] if '$' in password_hash else '无 $ 分隔符'}")
                    
                    if '$' in password_hash:
                        parts = password_hash.split('$')
                        print(f"   组成部分: {len(parts)} 部分")
                        for i, part in enumerate(parts):
                            print(f"     第 {i+1} 部分: '{part}'")
    
    print("\n=== 检查完成 ===")
except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()
