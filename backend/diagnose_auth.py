import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from app.models.user import User
from app.core.security import verify_password, create_access_token, verify_token, get_password_hash

def run_diagnostics():
    print("=== 后端认证系统诊断报告 ===")
    db = SessionLocal()
    try:
        # 1. 检查数据库连接
        print("\n[1/4] 数据库连接检查...")
        db.execute(text("SELECT 1"))
        print("✅ 数据库连接正常")

        # 2. 检查用户及密码校验
        print("\n[2/4] 用户及密码校验检查...")
        username = "testuser"
        test_password = "testpassword"
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ 未找到用户: {username}")
            # 尝试创建一个
            print(f"尝试创建测试用户: {username}...")
            new_user = User(
                username=username,
                password_hash=get_password_hash(test_password),
                is_active=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
            print(f"✅ 测试用户创建成功")
        
        print(f"找到用户: {user.username}")
        print(f"存储的哈希值: {user.password_hash}")
        
        is_valid = verify_password(test_password, user.password_hash)
        if is_valid:
            print(f"✅ 密码校验成功 (测试密码: {test_password})")
        else:
            print(f"❌ 密码校验失败 (测试密码: {test_password})")

        # 3. 令牌生成与验证
        print("\n[3/4] JWT 令牌生成与验证检查...")
        token = create_access_token(data={"sub": user.username})
        print(f"生成的 Token: {token[:20]}...")
        
        verified_username = verify_token(token)
        if verified_username == user.username:
            print(f"✅ Token 验证成功，Sub: {verified_username}")
        else:
            print(f"❌ Token 验证失败，期望: {user.username}, 实际: {verified_username}")

        # 4. 权限与状态
        print("\n[4/4] 账户状态检查...")
        if user.is_active:
            print("✅ 账户状态: 激活")
        else:
            print("❌ 账户状态: 禁用")

    except Exception as e:
        print(f"\n💥 诊断过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_diagnostics()
