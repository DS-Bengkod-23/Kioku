from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.user import UserRole


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: UUID
    name: str
    email: str


class UserProfileResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    job_title: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
