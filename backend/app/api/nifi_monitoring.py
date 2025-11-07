"""NiFi monitoring API endpoints for cluster and system diagnostics"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance
from app.services.nifi_auth import configure_nifi_connection

router = APIRouter(prefix="/api/nifi-instances", tags=["nifi-monitoring"])
logger = logging.getLogger(__name__)


class NiFiInstanceResponse(BaseModel):
    """Response model for NiFi instance listing"""
    id: int
    hierarchy_attribute: str
    hierarchy_value: str
    nifi_url: str
    use_ssl: bool
    verify_ssl: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NiFiInstanceResponse])
async def list_nifi_instances(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get list of all NiFi instances.
    Returns basic information about each instance without sensitive credentials.
    """
    try:
        instances = db.query(NiFiInstance).all()
        return instances
    except Exception as e:
        logger.error(f"Error listing NiFi instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list NiFi instances: {str(e)}",
        )


@router.get("/{instance_id}/get-cluster")
async def get_cluster(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get cluster information for a NiFi instance.
    Returns cluster status and node information.
    """
    try:
        # Get NiFi instance from database
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with id {instance_id} not found",
            )

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get cluster information
        import nipyapi

        cluster_data = nipyapi.system.get_cluster()

        # Convert to dict if needed
        if hasattr(cluster_data, "to_dict"):
            cluster_dict = cluster_data.to_dict()
        else:
            cluster_dict = cluster_data

        return {
            "status": "success",
            "instance_id": instance_id,
            "data": cluster_dict,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster info for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cluster information: {str(e)}",
        )


@router.get("/{instance_id}/get-nifi-version")
async def get_nifi_version(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get NiFi version information for a specific instance.
    """
    try:
        # Get NiFi instance from database
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with id {instance_id} not found",
            )

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get version information
        import nipyapi

        version_info = nipyapi.system.get_nifi_version_info()

        # Convert to dict if needed
        if hasattr(version_info, "to_dict"):
            version_dict = version_info.to_dict()
        else:
            version_dict = version_info

        return {
            "status": "success",
            "instance_id": instance_id,
            "data": version_dict,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting NiFi version for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get NiFi version: {str(e)}",
        )


@router.get("/{instance_id}/get-system-diagnostics")
async def get_system_diagnostics(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get system diagnostics for a NiFi instance.
    Returns heap usage, CPU, storage, and other system metrics.
    """
    try:
        # Get NiFi instance from database
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with id {instance_id} not found",
            )

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get system diagnostics
        import nipyapi

        diagnostics = nipyapi.system.get_system_diagnostics()

        # Convert to dict if needed
        if hasattr(diagnostics, "to_dict"):
            diagnostics_dict = diagnostics.to_dict()
        else:
            diagnostics_dict = diagnostics

        return {
            "status": "success",
            "instance_id": instance_id,
            "data": diagnostics_dict,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system diagnostics for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system diagnostics: {str(e)}",
        )


@router.get("/{instance_id}/get-node/{node_id}")
async def get_node(
    instance_id: int,
    node_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get specific node information from a NiFi cluster.
    
    Args:
        instance_id: The NiFi instance ID
        node_id: The node ID from the cluster
    """
    try:
        # Get NiFi instance from database
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with id {instance_id} not found",
            )

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get node information
        import nipyapi

        node_info = nipyapi.system.get_node(node_id)

        # Convert to dict if needed
        if hasattr(node_info, "to_dict"):
            node_dict = node_info.to_dict()
        else:
            node_dict = node_info

        return {
            "status": "success",
            "instance_id": instance_id,
            "node_id": node_id,
            "data": node_dict,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting node {node_id} info for instance {instance_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get node information: {str(e)}",
        )

