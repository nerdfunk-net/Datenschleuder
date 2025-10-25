"""NiFi instances management API endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import (
    NiFiInstance,
    NiFiInstanceCreate,
    NiFiInstanceUpdate,
    NiFiInstanceResponse,
)
from app.services.encryption_service import encryption_service

router = APIRouter(prefix="/api/nifi-instances", tags=["nifi-instances"])


@router.get("/", response_model=List[NiFiInstanceResponse])
async def list_nifi_instances(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get all NiFi instances"""
    instances = db.query(NiFiInstance).order_by(
        NiFiInstance.hierarchy_attribute, NiFiInstance.hierarchy_value
    ).all()

    # Return instances without decrypted passwords
    return instances


@router.get("/{instance_id}", response_model=NiFiInstanceResponse)
async def get_nifi_instance(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get a specific NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    return instance


@router.post("/", response_model=NiFiInstanceResponse)
async def create_nifi_instance(
    data: NiFiInstanceCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new NiFi instance"""
    # Check if instance already exists for this hierarchy value
    existing = db.query(NiFiInstance).filter(
        NiFiInstance.hierarchy_attribute == data.hierarchy_attribute,
        NiFiInstance.hierarchy_value == data.hierarchy_value,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NiFi instance already exists for {data.hierarchy_attribute}={data.hierarchy_value}",
        )

    # Encrypt password if provided
    encrypted_password = None
    if data.password:
        encrypted_password = encryption_service.encrypt_to_string(data.password)

    # Create instance
    instance = NiFiInstance(
        hierarchy_attribute=data.hierarchy_attribute,
        hierarchy_value=data.hierarchy_value,
        nifi_url=data.nifi_url,
        username=data.username,
        password_encrypted=encrypted_password,
        use_ssl=data.use_ssl,
        verify_ssl=data.verify_ssl,
    )

    db.add(instance)
    db.commit()
    db.refresh(instance)

    return instance


@router.put("/{instance_id}", response_model=NiFiInstanceResponse)
async def update_nifi_instance(
    instance_id: int,
    data: NiFiInstanceUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update a NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    # Update fields
    if data.nifi_url is not None:
        instance.nifi_url = data.nifi_url
    if data.username is not None:
        instance.username = data.username
    if data.password is not None:
        instance.password_encrypted = encryption_service.encrypt_to_string(data.password)
    if data.use_ssl is not None:
        instance.use_ssl = data.use_ssl
    if data.verify_ssl is not None:
        instance.verify_ssl = data.verify_ssl

    db.commit()
    db.refresh(instance)

    return instance


@router.delete("/{instance_id}")
async def delete_nifi_instance(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    db.delete(instance)
    db.commit()

    return {"message": f"Deleted NiFi instance for {instance.hierarchy_attribute}={instance.hierarchy_value}"}


@router.post("/test")
async def test_nifi_connection(
    data: NiFiInstanceCreate,
    token_data: dict = Depends(verify_token),
):
    """Test connection with provided NiFi credentials (without saving)"""
    try:
        import nipyapi
        from nipyapi import config, security

        # Configure nipyapi
        nifi_url = data.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = data.verify_ssl

        if not data.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Set credentials
        if data.username and data.password:
            config.nifi_config.username = data.username
            config.nifi_config.password = data.password
            security.service_login(service='nifi', username=data.username, password=data.password)

        # Test connection
        from nipyapi.nifi import FlowApi
        flow_api = FlowApi()
        controller_status = flow_api.get_controller_status()

        # Extract version
        version = "unknown"
        if hasattr(controller_status, 'controller_status'):
            if hasattr(controller_status.controller_status, 'version'):
                version = controller_status.controller_status.version

        return {
            "status": "success",
            "message": "Successfully connected to NiFi",
            "details": {
                "connected": True,
                "nifiUrl": nifi_url,
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
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security

        # Configure nipyapi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Test connection
        from nipyapi.nifi import FlowApi
        flow_api = FlowApi()
        controller_status = flow_api.get_controller_status()

        # Extract version
        version = "unknown"
        if hasattr(controller_status, 'controller_status'):
            if hasattr(controller_status.controller_status, 'version'):
                version = controller_status.controller_status.version

        return {
            "status": "success",
            "message": "Successfully connected to NiFi",
            "details": {
                "connected": True,
                "nifiUrl": nifi_url,
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
