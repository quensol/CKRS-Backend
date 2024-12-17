from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.models import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from typing import Any
from datetime import datetime

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    用户注册接口
    """
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=409,
            detail={
                "field": "email",
                "message": "该邮箱已被注册"
            }
        )
    
    # 检查手机号是否已存在
    if db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(
            status_code=409,
            detail={
                "field": "phone",
                "message": "该手机号已被注册"
            }
        )
    
    # 创建新用户
    db_user = User(
        email=user_data.email,
        phone=user_data.phone,
        password=get_password_hash(user_data.password)
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return {
            "id": db_user.id,
            "email": db_user.email,
            "phone": db_user.phone
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="注册失败，请稍后重试"
        )

@router.post("/login")
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """
    用户登录接口
    """
    # 查找用户
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    # 生成访问令牌
    access_token = create_access_token(user.id)
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "id": user.id,
        "email": user.email,
        "access_token": access_token,
        "token_type": "Bearer"
    }
