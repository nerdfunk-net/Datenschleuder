from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
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
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_oidc_user = Column(Boolean, default=False)  # Flag for OIDC-provisioned users
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to refresh tokens
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """Refresh token database model"""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)

    # Relationship to user
    user = relationship("User", back_populates="refresh_tokens")


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
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    is_active: bool
    is_superuser: bool
    is_oidc_user: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update schema"""

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class ProfileUpdate(BaseModel):
    """Profile update schema (for user self-update)"""

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class PasswordChange(BaseModel):
    """Password change schema"""

    current_password: str
    new_password: str


class Token(BaseModel):
    """Token response schema"""

    access_token: str
    token_type: str
    refresh_token: str | None = None


class TokenData(BaseModel):
    """Token payload schema"""

    username: str | None = None
