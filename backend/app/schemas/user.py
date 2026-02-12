from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, Literal
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    target_exam: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuth(BaseModel):
    credential: str  # Google ID token from frontend


class UserResponse(BaseModel):
    id: Any = Field(alias="_id")
    email: str
    full_name: Optional[str]
    target_exam: Optional[str]
    is_active: bool
    created_at: datetime
    auth_provider: Literal["local", "google"] = "local"
    profile_picture: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
