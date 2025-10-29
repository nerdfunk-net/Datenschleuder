"""NiFi integration API endpoints."""

import json
import urllib3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.services.encryption_service import encryption_service

# Disable SSL warnings for development/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(prefix="/api/nifi", tags=["nifi"])


def get_nifi_settings(db: Session):
    """Get NiFi settings from database"""
    from app.models.setting import Setting

    setting = db.query(Setting).filter(Setting.key == "nifi_config").first()
    if not setting:
        return None

    settings = json.loads(setting.value)

    # Decrypt password if present
    if settings.get("password"):
        try:
            settings["password"] = encryption_service.decrypt_from_string(
                settings["password"]
            )
        except Exception:
            settings["password"] = ""

    return settings


@router.post("/check-connection")
async def check_nifi_connection(
    token_data: dict = Depends(verify_token), db: Session = Depends(get_db)
):
    """
    Check if NiFi connection is valid using stored settings.
    Tests authentication and connectivity to NiFi instance.
    """
    try:
        import nipyapi
        from nipyapi import config, security

        # Get stored NiFi settings
        settings = get_nifi_settings(db)

        if not settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No NiFi settings found. Please configure NiFi connection first.",
            )

        if not settings.get("nifiUrl"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NiFi URL is required",
            )

        # Configure nipyapi
        nifi_url = settings["nifiUrl"].rstrip("/")  # Remove trailing slashes
        username = settings.get("username", "")
        password = settings.get("password", "")
        verify_ssl = settings.get("verifySSL", True)

        # Validate URL format
        if not nifi_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NiFi URL cannot be empty",
            )

        # Configure NiFi endpoint
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = verify_ssl

        # Disable SSL warnings for self-signed certificates if needed
        if not verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Set credentials if provided
        if username and password:
            config.nifi_config.username = username
            config.nifi_config.password = password

        # Attempt to authenticate
        try:
            from nipyapi.nifi import FlowApi

            flow_api = FlowApi()

            # If credentials provided, try to login
            if username and password:
                security.service_login(
                    service="nifi", username=username, password=password
                )

            # Test the connection
            controller_status = flow_api.get_controller_status()

            # Extract version info
            version = "unknown"
            if hasattr(controller_status, "controller_status"):
                if hasattr(controller_status.controller_status, "version"):
                    version = controller_status.controller_status.version

            return {
                "status": "success",
                "message": "Successfully connected to NiFi",
                "details": {"connected": True, "nifiUrl": nifi_url, "version": version},
            }

        except Exception as conn_error:
            # Connection or authentication failed
            error_msg = str(conn_error)

            if "401" in error_msg or "Unauthorized" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed. Invalid username or password.",
                )
            elif "403" in error_msg or "Forbidden" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden. User may not have sufficient permissions.",
                )
            elif "timeout" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Connection timeout. Unable to reach NiFi at {nifi_url}",
                )
            elif "connection" in error_msg.lower() or "resolve" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Cannot connect to NiFi at {nifi_url}. Please check the URL and network connectivity.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Connection failed: {error_msg}",
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )
