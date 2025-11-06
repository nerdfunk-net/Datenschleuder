from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime

from app.core.database import Base


class User(Base):
    """User database model with SHA256 hashed passwords"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(
        String, nullable=False
    )  # SHA256 hash (one-way, for login only)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_oidc_user = Column(Boolean, default=False)  # Flag for OIDC-provisioned users
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic schemas for API validation
class UserBase(BaseModel):
    """Base user schema"""

    username: str


class UserCreate(UserBase):
    """User creation schema"""

    password: str


class UserResponse(UserBase):
    """User response schema"""

    id: int
    is_active: bool
    is_superuser: bool
    is_oidc_user: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update schema"""

    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class PasswordChange(BaseModel):
    """Password change schema"""

    current_password: str
    new_password: str


class Token(BaseModel):
    """Token response schema"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload schema"""

    username: str | None = None
