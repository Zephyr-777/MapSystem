from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

# 密码加密上下文
#
# 说明：
# - 支持多种哈希算法，包括 pbkdf2_sha256（默认）和 bcrypt
# - 支持验证旧的 bcrypt 哈希，同时使用 pbkdf2_sha256 生成新哈希
# - pbkdf2_sha256 不依赖 bcrypt 且无 72 bytes 限制，作为本项目的默认方案更稳
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

from fastapi import Header, HTTPException, status

def verify_token(token: str) -> Optional[str]:
    """验证令牌并返回用户名"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def role_checker(x_user_role: str = Header(default="guest", alias="X-User-Role")):
    """
    检查请求头中的 X-User-Role 是否为 admin
    注意：在实际生产中，角色应该从 JWT Token 或数据库中获取，而不是完全信任客户端 Header。
    这里为了演示方便，遵循用户指令使用 Header 检查。
    """
    if x_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Admin role required."
        )
    return x_user_role
