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


@router.get("/{instance_id}/get-root")
async def get_root_process_group(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get the root process group information for a NiFi instance.
    
    Args:
        instance_id: The NiFi instance ID
    
    Returns:
        Root process group information including ID and name
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

        # Get root process group
        import nipyapi

        root_pg = nipyapi.canvas.get_root_pg_id()
        process_group = nipyapi.canvas.get_process_group(root_pg, 'id')

        # Convert to dict if needed
        if hasattr(process_group, "to_dict"):
            pg_dict = process_group.to_dict()
        else:
            pg_dict = process_group

        return {
            "status": "success",
            "instance_id": instance_id,
            "root_id": root_pg,
            "root_name": process_group.component.name if hasattr(process_group, 'component') else None,
            "data": pg_dict,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting root process group for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get root process group: {str(e)}",
        )


@router.get("/{instance_id}/get-all-paths")
async def get_all_process_group_paths(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get all process groups with their full hierarchical paths.
    
    Args:
        instance_id: The NiFi instance ID
    
    Returns:
        List of all process groups with their IDs, names, and full paths
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

        # Get all process groups recursively
        import nipyapi

        def build_pg_paths(pg_id, parent_path=None):
            """Recursively build paths for all process groups"""
            results = []
            
            # Get current process group
            pg = nipyapi.canvas.get_process_group(pg_id, 'id')
            pg_name = pg.component.name
            pg_parent_id = pg.component.parent_group_id
            
            # Build current path
            if parent_path is None:
                current_path = [{"id": pg_id, "name": pg_name, "parent_group_id": pg_parent_id}]
            else:
                current_path = [{"id": pg_id, "name": pg_name, "parent_group_id": pg_parent_id}] + parent_path
            
            # Calculate depth
            depth = len(current_path) - 1
            
            # Add current PG to results
            results.append({
                "id": pg_id,
                "name": pg_name,
                "parent_group_id": pg_parent_id,
                "comments": pg.component.comments if hasattr(pg.component, 'comments') else "",
                "path": current_path,
                "depth": depth
            })
            
            # Get child process groups
            child_pgs = nipyapi.canvas.list_all_process_groups(pg_id)
            
            for child_pg in child_pgs:
                child_id = child_pg.id
                # Skip the current process group itself
                if child_id != pg_id:
                    results.extend(build_pg_paths(child_id, current_path))
            
            return results

        root_pg_id = nipyapi.canvas.get_root_pg_id()
        all_pgs = build_pg_paths(root_pg_id)

        return {
            "status": "success",
            "process_groups": all_pgs,
            "count": len(all_pgs),
            "root_id": root_pg_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all process group paths for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group paths: {str(e)}",
        )


@router.get("/{instance_id}/process-group/{process_group_id}/status")
async def get_process_group_status(
    instance_id: int,
    process_group_id: str,
    detail: str = "all",
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get status of a specific process group.
    
    Args:
        instance_id: The NiFi instance ID
        process_group_id: The process group UUID (use 'root' for root process group)
        detail: 'names' returns simple dict of name:id pairings, 'all' returns full details (default: 'all')
    
    Returns:
        Process group entity including status information
    """
    try:
        # Validate detail parameter
        if detail not in ["names", "all"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="detail parameter must be either 'names' or 'all'",
            )

        # Get NiFi instance from database
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with id {instance_id} not found",
            )

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get process group status
        import nipyapi

        pg_status = nipyapi.canvas.get_process_group_status(
            pg_id=process_group_id, detail=detail
        )

        # Convert to dict if needed
        if hasattr(pg_status, "to_dict"):
            status_dict = pg_status.to_dict()
        else:
            status_dict = pg_status

        return {
            "status": "success",
            "instance_id": instance_id,
            "process_group_id": process_group_id,
            "detail": detail,
            "data": status_dict,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting process group {process_group_id} status for instance {instance_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group status: {str(e)}",
        )

