"""NiFi flow model with dynamic hierarchy fields"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NiFiFlowCreate(BaseModel):
    """Schema for creating a NiFi flow"""

    hierarchy_values: dict  # Dynamic hierarchy values e.g., {"CN": {"source": "test1", "destination": "test2"}, "O": {"source": "myOrg", "destination": "yourOrg"}, ...}
    name: Optional[str] = None  # Flow name
    contact: Optional[str] = None  # Contact information
    src_connection_param: str
    dest_connection_param: str
    src_template_id: Optional[int] = None  # ID of registry_flow
    dest_template_id: Optional[int] = None  # ID of registry_flow
    active: bool
    description: Optional[str] = None
    creator_name: Optional[str] = None


class NiFiFlowUpdate(BaseModel):
    """Schema for updating a NiFi flow"""

    hierarchy_values: Optional[dict] = None
    name: Optional[str] = None
    contact: Optional[str] = None
    src_connection_param: Optional[str] = None
    dest_connection_param: Optional[str] = None
    src_template_id: Optional[int] = None
    dest_template_id: Optional[int] = None
    active: Optional[bool] = None
    description: Optional[str] = None


class NiFiFlowResponse(BaseModel):
    """Schema for NiFi flow response"""

    id: int
    hierarchy_values: dict
    name: Optional[str]
    contact: Optional[str]
    src_connection_param: str
    dest_connection_param: str
    src_template_id: Optional[int]
    dest_template_id: Optional[int]
    active: bool
    description: Optional[str]
    creator_name: Optional[str]
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True
