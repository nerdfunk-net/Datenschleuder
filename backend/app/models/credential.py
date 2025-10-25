"""Credential model for storing encrypted credentials (SSH, TACACS, etc.)"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, LargeBinary
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

from app.core.database import Base


class Credential(Base):
    """Credential database model with Fernet-encrypted passwords"""
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'ssh', 'tacacs', 'generic', 'token'
    password_encrypted = Column(Text, nullable=False)  # Fernet-encrypted password as base64 string
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    source = Column(String, default="general")  # 'general' or 'private'
    owner = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic schemas for API validation
class CredentialBase(BaseModel):
    """Base credential schema"""
    name: str
    username: str
    type: Literal["ssh", "tacacs", "generic", "token"]
    valid_until: Optional[datetime] = None
    source: str = "general"
    owner: Optional[str] = None


class CredentialCreate(CredentialBase):
    """Credential creation schema"""
    password: str  # Plain password, will be encrypted


class CredentialUpdate(BaseModel):
    """Credential update schema"""
    name: Optional[str] = None
    username: Optional[str] = None
    type: Optional[Literal["ssh", "tacacs", "generic", "token"]] = None
    password: Optional[str] = None
    valid_until: Optional[datetime] = None
    source: Optional[str] = None
    owner: Optional[str] = None


class CredentialResponse(CredentialBase):
    """Credential response schema (without password)"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = "active"  # 'active', 'expiring', 'expired'

    class Config:
        from_attributes = True


class CredentialWithPassword(CredentialResponse):
    """Credential response schema with decrypted password"""
    password: str  # Decrypted password
