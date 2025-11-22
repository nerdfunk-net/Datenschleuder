"""NiFi connection testing API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstanceCreate
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.post("/test")
async def test_nifi_connection(
    data: NiFiInstanceCreate,
    token_data: dict = Depends(verify_token),
):
    """Test connection with provided NiFi credentials (without saving)"""
    try:
        from app.services.nifi_auth import configure_nifi_test_connection
        from nipyapi.nifi import FlowApi

        logger.info("=== CONNECTIONS.PY TEST ENDPOINT CALLED ===")
        logger.info(f"Received data: username={data.username!r}, oidc_provider_id={data.oidc_provider_id!r}, certificate_name={data.certificate_name!r}")

        # Configure nipyapi with authentication
        configure_nifi_test_connection(
            nifi_url=data.nifi_url,
            username=data.username,
            password=data.password,
            verify_ssl=data.verify_ssl,
            certificate_name=data.certificate_name,
            check_hostname=data.check_hostname,
            oidc_provider_id=data.oidc_provider_id,  # Added OIDC support
        )

        # Test connection
        flow_api = FlowApi()
        controller_status = flow_api.get_controller_status()

        # Extract version
        version = "unknown"
        if hasattr(controller_status, "controller_status"):
            if hasattr(controller_status.controller_status, "version"):
                version = controller_status.controller_status.version

        return {
            "status": "success",
            "message": "Successfully connected to NiFi",
            "details": {
                "connected": True,
                "nifiUrl": data.nifi_url,
                "version": version,
            },
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Connection failed: {error_msg}",
            "details": {
                "connected": False,
                "nifiUrl": data.nifi_url,
                "error": error_msg,
            },
        }


@router.post("/{instance_id}/test-connection")
async def test_nifi_instance_connection(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Test connection for a specific NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # Test connection
        flow_api = FlowApi()
        controller_status = flow_api.get_controller_status()

        # Extract version
        version = "unknown"
        if hasattr(controller_status, "controller_status"):
            if hasattr(controller_status.controller_status, "version"):
                version = controller_status.controller_status.version

        return {
            "status": "success",
            "message": "Successfully connected to NiFi",
            "details": {
                "connected": True,
                "nifiUrl": instance.nifi_url,
                "version": version,
            },
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Connection failed: {error_msg}",
            "details": {
                "connected": False,
                "nifiUrl": instance.nifi_url,
                "error": error_msg,
            },
        }
