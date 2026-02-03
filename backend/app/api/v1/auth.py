from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, verify_token
from app.models.user import User
from app.schemas import UserRegister, UserLogin, TokenResponse, UserResponse

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = verify_token(token)
    if username is None:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=TokenResponse)
async def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # 检查用户是否已存在
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    # 创建新用户
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 生成 token
    access_token = create_access_token(data={"sub": new_user.username})
    return {
        "token": access_token,
        "user": new_user
    }

@router.post("/login/json", response_model=TokenResponse)
async def login_json(user_in: UserLogin, db: Session = Depends(get_db)):
    print(f"DEBUG: Login attempt for user: {user_in.username}")
    user = db.query(User).filter(User.username == user_in.username).first()
    
    if not user:
        print(f"DEBUG: User not found: {user_in.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
        
    if not verify_password(user_in.password, user.password_hash):
        print(f"DEBUG: Password verification failed for user: {user_in.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    print(f"DEBUG: Login successful for user: {user_in.username}")
    access_token = create_access_token(data={"sub": user.username})
    return {
        "token": access_token,
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
