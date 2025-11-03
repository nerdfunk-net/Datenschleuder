"""Deployment models for flow deployment operations"""

from pydantic import BaseModel
from typing import Optional, Union, List


class DeploymentRequest(BaseModel):
    """
    Model for deploying a flow from registry to NiFi instance.

    The flow will be deployed as a new process group inside the parent_process_group_id.
    If parent_process_group_id is not specified, it deploys to the root process group.

    Can specify either template_id (to lookup registry info) or direct registry parameters.
    """

    # Option 1: Use template_id to lookup registry flow information
    template_id: Optional[int] = None

    # Option 2: Provide registry information directly
    bucket_id: Optional[str] = None
    flow_id: Optional[str] = None
    registry_client_id: Optional[str] = None

    # Common parameters
    parent_process_group_id: Optional[str] = None  # ID of parent PG, None = root
    parent_process_group_path: Optional[str] = None  # Path to parent PG (alternative to ID)
    process_group_name: Optional[str] = (
        None  # Name for the deployed process group (will rename after deployment)
    )
    version: Optional[Union[int, str]] = (
        None  # None = latest; int for NiFi Registry, str (commit hash) for GitHub Registry
    )
    x_position: Optional[int] = 0
    y_position: Optional[int] = 0
    parameter_context_id: Optional[str] = None  # Optional parameter context to assign to the deployed process group


class DeploymentResponse(BaseModel):
    """Response model for deployment operation"""

    status: str
    message: str
    process_group_id: Optional[str] = None
    process_group_name: Optional[str] = None
    instance_id: int
    bucket_id: str
    flow_id: str
    version: Optional[Union[int, str]] = (
        None  # int for NiFi Registry, str (commit hash) for GitHub Registry
    )


class PortInfo(BaseModel):
    """Information about a NiFi port (input or output)"""

    id: str
    name: str
    state: str
    comments: Optional[str] = None


class PortsResponse(BaseModel):
    """Response model for listing ports"""

    process_group_id: str
    process_group_name: Optional[str] = None
    ports: List[PortInfo]


class ConnectionRequest(BaseModel):
    """Request to create a connection between two ports/processors"""

    source_id: str  # ID of source port/processor
    target_id: str  # ID of target port/processor
    name: Optional[str] = None  # Optional name for the connection
    relationships: Optional[List[str]] = (
        None  # For processors, list of relationships to connect
    )


class ConnectionResponse(BaseModel):
    """Response model for connection creation"""

    status: str
    message: str
    connection_id: str
    source_id: str
    source_name: str
    target_id: str
    target_name: str


class DeploymentPathSettings(BaseModel):
    """Deployment path settings for a specific NiFi instance"""

    instance_id: int
    source_path: Optional[str] = None  # Path for source element in top hierarchy
    dest_path: Optional[str] = None  # Path for destination element in top hierarchy


class DeploymentSettings(BaseModel):
    """Global deployment settings"""

    process_group_name_template: str = (
        "{last_hierarchy_value}"  # Default: use last hierarchy value
    )
    disable_after_deploy: bool = False
    create_parameter_context: bool = True
