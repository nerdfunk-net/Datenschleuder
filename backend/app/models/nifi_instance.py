"""NiFi instance model for managing multiple NiFi systems"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.core.database import Base


class NiFiInstance(Base):
    """NiFi instance model - one instance per top hierarchy value"""

    __tablename__ = "nifi_instances"

    id = Column(Integer, primary_key=True, index=True)
    hierarchy_attribute = Column(String, nullable=False)  # e.g., "DC"
    hierarchy_value = Column(String, nullable=False, index=True)  # e.g., "DC1", "DC2"
    nifi_url = Column(
        String, nullable=False
    )  # e.g., "https://dc1.nifi.com:8443/nifi-api"
    username = Column(String, nullable=True)
    password_encrypted = Column(Text, nullable=True)  # Fernet-encrypted password
    use_ssl = Column(Boolean, default=True)
    verify_ssl = Column(Boolean, default=True)
    certificate_name = Column(
        String, nullable=True
    )  # Name of certificate to use (from certificates.yaml), None = username/password
    check_hostname = Column(
        Boolean, default=True
    )  # Whether to verify SSL certificate hostname matches

    # OIDC Authentication (references provider from oidc_providers.yaml)
    oidc_provider_id = Column(
        String, nullable=True
    )  # ID of OIDC provider to use (from oidc_providers.yaml), e.g. "nifi_backend"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    registry_flows = relationship("RegistryFlow", back_populates="nifi_instance")


# Pydantic schemas
class NiFiInstanceCreate(BaseModel):
    """Schema for creating a NiFi instance"""

    hierarchy_attribute: str
    hierarchy_value: str
    nifi_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = True
    verify_ssl: bool = True
    certificate_name: Optional[str] = None
    check_hostname: bool = True

    # OIDC authentication - provider ID from oidc_providers.yaml
    oidc_provider_id: Optional[str] = None

    class Config:
        # Ensure field names are used as-is without conversion
        populate_by_name = True


class NiFiInstanceUpdate(BaseModel):
    """Schema for updating a NiFi instance"""

    nifi_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: Optional[bool] = None
    verify_ssl: Optional[bool] = None
    certificate_name: Optional[str] = None
    check_hostname: Optional[bool] = None

    # OIDC authentication - provider ID from oidc_providers.yaml
    oidc_provider_id: Optional[str] = None


class NiFiInstanceResponse(BaseModel):
    """Schema for NiFi instance response"""

    id: int
    hierarchy_attribute: str
    hierarchy_value: str
    nifi_url: str
    username: Optional[str] = None
    use_ssl: bool
    verify_ssl: bool
    certificate_name: Optional[str] = None
    check_hostname: bool

    # OIDC authentication - provider ID from oidc_providers.yaml
    oidc_provider_id: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
