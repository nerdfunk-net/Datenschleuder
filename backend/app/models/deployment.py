"""Deployment models for flow deployment operations"""

from pydantic import BaseModel
from typing import Optional


class DeploymentRequest(BaseModel):
    """
    Model for deploying a flow from registry to NiFi instance.

    The flow will be deployed as a new process group inside the parent_process_group_id.
    If parent_process_group_id is not specified, it deploys to the root process group.
    """
    bucket_id: str
    flow_id: str
    registry_client_id: str
    parent_process_group_id: Optional[str] = None  # ID of parent PG, None = root
    version: Optional[int] = None  # None = latest version
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
    version: Optional[int] = None
