"""NiFi version control API endpoints"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404
from app.services.encryption_service import encryption_service

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
        import nipyapi
        from nipyapi import config, security, versioning

        # Configure nipyapi
        nifi_base_url = instance.nifi_url.rstrip("/")
        if nifi_base_url.endswith("/nifi-api"):
            nifi_base_url = nifi_base_url[:-9]

        config.nifi_config.host = f"{nifi_base_url}/nifi-api"
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password and authenticate
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(
                instance.password_encrypted
            )

        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(
                service="nifi", username=instance.username, password=password
            )

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
