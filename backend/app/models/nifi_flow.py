"""NiFi flow model with dynamic hierarchy fields"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NiFiFlowCreate(BaseModel):
    """Schema for creating a NiFi flow"""
    hierarchy_values: dict  # Dynamic hierarchy values e.g., {"CN": "test1", "O": "myOrg", ...}
    source: str
    destination: str
    connection_param: str
    template: str
    active: bool
    description: Optional[str] = None
    creator_name: Optional[str] = None


class NiFiFlowUpdate(BaseModel):
    """Schema for updating a NiFi flow"""
    hierarchy_values: Optional[dict] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    connection_param: Optional[str] = None
    template: Optional[str] = None
    active: Optional[bool] = None
    description: Optional[str] = None


class NiFiFlowResponse(BaseModel):
    """Schema for NiFi flow response"""
    id: int
    hierarchy_values: dict
    source: str
    destination: str
    connection_param: str
    template: str
    active: bool
    description: Optional[str]
    creator_name: Optional[str]
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True
