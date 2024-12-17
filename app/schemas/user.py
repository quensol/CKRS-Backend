from pydantic import BaseModel, EmailStr, constr, Field
from typing import Optional
from pydantic.types import constr as Constr

class UserBase(BaseModel):
    email: EmailStr
    phone: Constr(pattern=r'^1[3-9]\d{9}$')  # 手机号验证

class UserCreate(UserBase):
    password: Constr(min_length=8)
    confirm_password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": "13800138000",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        }

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "Password123"
            }
        }

class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True 