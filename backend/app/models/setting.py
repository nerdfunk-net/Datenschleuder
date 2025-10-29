"""Settings model for storing application configuration"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.database import Base


class Setting(Base):
    """Settings database model - stores key-value configuration"""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)  # e.g., "nifi_config"
    value = Column(Text, nullable=False)  # JSON-encoded value
    category = Column(String, nullable=True)  # e.g., "nifi", "registry", etc.
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic schemas for API validation
class NifiSettings(BaseModel):
    """NiFi connection settings"""

    nifiUrl: str
    username: Optional[str] = None
    password: Optional[str] = None
    useSSL: bool = True
    verifySSL: bool = True


class RegistrySettings(BaseModel):
    """NiFi Registry settings"""

    registryUrl: str
    username: Optional[str] = None
    password: Optional[str] = None
    useSSL: bool = True
    verifySSL: bool = True


class SettingCreate(BaseModel):
    """Setting creation schema"""

    key: str
    value: str
    category: Optional[str] = None
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    """Setting update schema"""

    value: str
    description: Optional[str] = None


class SettingResponse(BaseModel):
    """Setting response schema"""

    id: int
    key: str
    value: str
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
