from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    SUGGEST_ONLY = "suggest_only"
    APPROVER = "approver" 
    ADMIN = "admin"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.SUGGEST_ONLY
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class User(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None