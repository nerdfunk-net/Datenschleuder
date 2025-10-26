"""Deployment models for flow deployment operations"""

from pydantic import BaseModel
from typing import Optional, Union


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
    version: Optional[Union[int, str]] = None  # None = latest; int for NiFi Registry, str (commit hash) for GitHub Registry
    x_position: Optional[int] = 0
    y_position: Optional[int] = 0


class DeploymentResponse(BaseModel):
    """Response model for deployment operation"""
    status: str
    message: str
    process_group_id: Optional[str] = None
    process_group_name: Optional[str] = None
    instance_id: int
    bucket_id: str
    flow_id: str
    version: Optional[Union[int, str]] = None  # int for NiFi Registry, str (commit hash) for GitHub Registry
