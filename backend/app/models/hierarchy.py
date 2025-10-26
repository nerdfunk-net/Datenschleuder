"""Hierarchy value model"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import List

from app.core.database import Base


class HierarchyValue(Base):
    """Hierarchy values - stores individual values for each attribute"""
    __tablename__ = "hierarchy"

    id = Column(Integer, primary_key=True, index=True)
    attribute_name = Column(String, index=True, nullable=False)  # e.g., "CN", "O", "OU", "DC"
    value = Column(String, nullable=False)  # e.g., "test1", "test2", "myOrg"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic schemas
class HierarchyValueCreate(BaseModel):
    """Schema for creating a value"""
    attribute_name: str
    value: str


class HierarchyValueResponse(BaseModel):
    """Schema for value response"""
    id: int
    attribute_name: str
    value: str
    created_at: datetime

    class Config:
        from_attributes = True


class HierarchyValuesRequest(BaseModel):
    """Schema for batch creating/updating values for an attribute"""
    attribute_name: str
    values: List[str]
