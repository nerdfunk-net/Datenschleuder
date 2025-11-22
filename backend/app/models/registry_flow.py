"""Registry flow model for storing selected NiFi flows"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.database import Base


class RegistryFlow(Base):
    """Registry flow - stores selected flows from NiFi registries"""

    __tablename__ = "registry_flows"

    id = Column(Integer, primary_key=True, index=True)
    nifi_instance_id = Column(
        Integer, ForeignKey("nifi_instances.id"), nullable=False, index=True
    )
    nifi_instance_name = Column(
        String, nullable=False, index=True
    )  # Name of NiFi instance
    nifi_instance_url = Column(String, nullable=False)  # URL of NiFi instance
    registry_id = Column(String, nullable=False)  # Registry ID from NiFi
    registry_name = Column(String, nullable=False)  # Registry name
    bucket_id = Column(String, nullable=False, index=True)  # Bucket ID from NiFi
    bucket_name = Column(String, nullable=False)  # Bucket name
    flow_id = Column(String, nullable=False, index=True)  # Flow ID from NiFi
    flow_name = Column(String, nullable=False)  # Flow name
    flow_description = Column(Text, nullable=True)  # Flow description
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship to NiFi instance
    nifi_instance = relationship("NiFiInstance", back_populates="registry_flows")


# Pydantic schemas
class RegistryFlowCreate(BaseModel):
    """Schema for creating a registry flow"""

    nifi_instance_id: int
    nifi_instance_name: str
    nifi_instance_url: str
    registry_id: str
    registry_name: str
    bucket_id: str
    bucket_name: str
    flow_id: str
    flow_name: str
    flow_description: Optional[str] = None


class RegistryFlowResponse(BaseModel):
    """Schema for registry flow response"""

    id: int
    nifi_instance_id: int
    nifi_instance_name: str
    nifi_instance_url: str
    registry_id: str
    registry_name: str
    bucket_id: str
    bucket_name: str
    flow_id: str
    flow_name: str
    flow_description: Optional[str]
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True
