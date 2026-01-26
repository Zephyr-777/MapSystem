#!/usr/bin/env python3
"""
修复数据库序列问题
解决用户注册时出现的 duplicate key value violates unique constraint "users_pkey" 错误
"""

from sqlalchemy import create_engine, text
from database import DATABASE_URL

print("=== 修复数据库序列问题 ===")
print(f"使用数据库: {DATABASE_URL}")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 修复 users 表的序列
try:
    with engine.connect() as conn:
        # 检查 users 表是否存在
        check_table = text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');")
        table_exists = conn.execute(check_table).scalar()
        
        if not table_exists:
            print("❌ users 表不存在，可能需要先运行迁移脚本")
        else:
            # 检查是否有记录
            check_records = text("SELECT COUNT(*) FROM users;")
            record_count = conn.execute(check_records).scalar()
            
            if record_count == 0:
                print("✅ users 表为空，无需修复序列")
            else:
                # 获取最大 ID
                get_max_id = text("SELECT MAX(id) FROM users;")
                max_id = conn.execute(get_max_id).scalar()
                
                print(f"📊 当前 users 表最大 ID: {max_id}")
                
                # 修复序列
                fix_sequence = text(f"SELECT setval('users_id_seq', :max_id + 1);")
                result = conn.execute(fix_sequence, {"max_id": max_id})
                new_val = result.scalar()
                
                print(f"✅ 序列修复成功！新的序列值: {new_val}")
    
    print("\n=== 修复完成 ===")
except Exception as e:
    print(f"❌ 修复失败: {e}")
    import traceback
    traceback.print_exc()
