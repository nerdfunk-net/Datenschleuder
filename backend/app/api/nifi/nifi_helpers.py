"""Helper functions for NiFi API endpoints"""

import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.nifi_instance import NiFiInstance
from app.services.nifi_auth import configure_nifi_connection
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)


def get_instance_or_404(db: Session, instance_id: int) -> NiFiInstance:
    """
    Get NiFi instance by ID or raise 404.

    Args:
        db: Database session
        instance_id: NiFi instance ID

    Returns:
        NiFi instance object

    Raises:
        HTTPException: 404 if instance not found
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )
    return instance


def setup_nifi_connection(instance: NiFiInstance, normalize_url: bool = False) -> None:
    """
    Configure NiFi connection for an instance.

    Args:
        instance: NiFi instance to configure
        normalize_url: Whether to normalize the URL

    Raises:
        HTTPException: If connection configuration fails
    """
    try:
        configure_nifi_connection(instance, normalize_url=normalize_url)
    except Exception as e:
        logger.error(f"Failed to configure NiFi connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure NiFi connection: {str(e)}",
        )


def extract_pg_info(pg: Any) -> Dict[str, Optional[str]]:
    """
    Extract process group information from nipyapi object.

    Args:
        pg: Process group object from nipyapi

    Returns:
        Dictionary with id, name, parent_group_id, and comments
    """
    pg_info = {
        "id": pg.id if hasattr(pg, "id") else None,
        "name": None,
        "parent_group_id": None,
        "comments": None,
    }

    if hasattr(pg, "component"):
        component = pg.component
        if hasattr(component, "name"):
            pg_info["name"] = component.name
        if hasattr(component, "parent_group_id"):
            pg_info["parent_group_id"] = component.parent_group_id
        if hasattr(component, "comments"):
            pg_info["comments"] = component.comments

    return pg_info


def decrypt_instance_password(instance: NiFiInstance) -> Optional[str]:
    """
    Decrypt instance password if present.

    Args:
        instance: NiFi instance

    Returns:
        Decrypted password or None
    """
    if instance.password_encrypted:
        try:
            return encryption_service.decrypt_from_string(instance.password_encrypted)
        except Exception as e:
            logger.warning(f"Failed to decrypt password: {e}")
            return None
    return None


def build_error_response(
    error: Exception, default_message: str = "Operation failed"
) -> Dict[str, str]:
    """
    Build standardized error response.

    Args:
        error: Exception that occurred
        default_message: Default error message if exception message is empty

    Returns:
        Dictionary with status and error message
    """
    error_msg = str(error) if str(error) else default_message
    return {"status": "error", "message": error_msg}


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that required fields are present in data.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Raises:
        HTTPException: 400 if any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {', '.join(missing_fields)}",
        )
