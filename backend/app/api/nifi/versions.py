"""NiFi version control API endpoints"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.post("/{instance_id}/process-group/{process_group_id}/update-version")
async def update_process_group_version(
    instance_id: int,
    process_group_id: str,
    version_request: dict,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Update a version-controlled process group to a new version.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import versioning

        # Configure nipyapi connection with proper SSL handling
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Updating process group {process_group_id} to new version...")

        # Get the process group
        from nipyapi.nifi import ProcessGroupsApi

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        # Update to latest version
        target_version = version_request.get("version")  # None = latest
        versioning.update_flow_version(process_group=pg, target_version=target_version)

        logger.info("✓ Process group updated successfully")

        return {
            "status": "success",
            "message": "Process group updated to new version",
            "process_group_id": process_group_id,
            "version": target_version,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to update process group version: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update process group version: {error_msg}",
        )


@router.post("/{instance_id}/process-group/{process_group_id}/stop-versioning")
async def stop_process_group_versioning(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stop version control for a process group.
    Removes the process group from version control, making it a standalone flow.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import versioning, canvas

        # Configure nipyapi connection with proper SSL handling
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Stopping version control for process group {process_group_id}...")

        # Get the process group
        pg = canvas.get_process_group(process_group_id, 'id')

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group {process_group_id} not found"
            )

        # Check if process group is under version control
        if not hasattr(pg, 'component') or not hasattr(pg.component, 'version_control_information'):
            logger.info(f"Process group {process_group_id} is not under version control")
            return {
                "status": "success",
                "message": "Process group is not under version control",
                "process_group_id": process_group_id,
                "was_versioned": False,
            }

        version_info = pg.component.version_control_information
        if not version_info:
            logger.info(f"Process group {process_group_id} is not under version control")
            return {
                "status": "success",
                "message": "Process group is not under version control",
                "process_group_id": process_group_id,
                "was_versioned": False,
            }

        # Stop version control
        logger.info(f"Removing process group from version control...")
        versioning.stop_flow_ver(pg, refresh=True)

        logger.info(f"✓ Version control stopped for process group {process_group_id}")

        return {
            "status": "success",
            "message": "Version control stopped successfully",
            "process_group_id": process_group_id,
            "was_versioned": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to stop version control: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop version control: {error_msg}",
        )
