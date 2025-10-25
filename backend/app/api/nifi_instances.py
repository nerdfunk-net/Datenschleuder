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


@router.get("/{instance_id}/get-registries")
async def get_registry_clients(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of registry clients configured in NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, versioning

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

        # Get list of registry clients
        registry_clients_entity = versioning.list_registry_clients()

        # Extract the actual list of clients from the entity
        clients_list = []
        if hasattr(registry_clients_entity, 'registries') and registry_clients_entity.registries:
            for client in registry_clients_entity.registries:
                client_data = {
                    "id": client.id if hasattr(client, 'id') else "Unknown",
                    "name": client.component.name if hasattr(client, 'component') and hasattr(client.component, 'name') else "Unknown",
                    "uri": client.component.properties.get('url', 'N/A') if hasattr(client, 'component') and hasattr(client.component, 'properties') else "N/A",
                    "description": client.component.description if hasattr(client, 'component') and hasattr(client.component, 'description') else "",
                    "type": client.component.type if hasattr(client, 'component') and hasattr(client.component, 'type') else "Unknown",
                }
                clients_list.append(client_data)

        return {
            "status": "success",
            "registry_clients": clients_list,
            "count": len(clients_list)
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Failed to get registry clients: {error_msg}",
            "registry_clients": [],
            "count": 0
        }


@router.get("/{instance_id}/registry/{registry_id}/get-buckets")
async def get_registry_buckets(
    instance_id: int,
    registry_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of buckets from a specific registry client"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, versioning

        # Configure nipyapi for NiFi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials for NiFi
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Get the registry client to find its URL
        registry_clients_entity = versioning.list_registry_clients()
        registry_client = None

        if hasattr(registry_clients_entity, 'registries') and registry_clients_entity.registries:
            for client in registry_clients_entity.registries:
                if client.id == registry_id:
                    registry_client = client
                    break

        if not registry_client:
            return {
                "status": "error",
                "message": f"Registry client with id {registry_id} not found",
                "buckets": [],
                "count": 0
            }

        # Use NiFi's FlowApi to get buckets from the registry client
        # This works for all registry types (NiFi Registry, GitHub, etc.)
        from nipyapi.nifi import FlowApi
        flow_api = FlowApi()

        # Get buckets using the registry client ID
        buckets_entity = flow_api.get_buckets(registry_id)

        # Convert to serializable format
        buckets_list = []
        if hasattr(buckets_entity, 'buckets') and buckets_entity.buckets:
            for bucket in buckets_entity.buckets:
                bucket_data = {
                    "identifier": bucket.id if hasattr(bucket, 'id') else "Unknown",
                    "name": bucket.bucket.name if hasattr(bucket, 'bucket') and hasattr(bucket.bucket, 'name') else "Unknown",
                    "description": bucket.bucket.description if hasattr(bucket, 'bucket') and hasattr(bucket.bucket, 'description') else "",
                    "created_timestamp": bucket.bucket.created_timestamp if hasattr(bucket, 'bucket') and hasattr(bucket.bucket, 'created_timestamp') else None,
                    "permissions": bucket.permissions.to_dict() if hasattr(bucket, 'permissions') and hasattr(bucket.permissions, 'to_dict') else {},
                }
                buckets_list.append(bucket_data)

        registry_type = registry_client.component.type if hasattr(registry_client, 'component') and hasattr(registry_client.component, 'type') else "Unknown"

        return {
            "status": "success",
            "buckets": buckets_list,
            "count": len(buckets_list),
            "registry_type": registry_type,
            "registry_id": registry_id
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Failed to get registry buckets: {error_msg}",
            "buckets": [],
            "count": 0
        }


@router.get("/{instance_id}/registry/{registry_id}/{bucket_id}/get-flows")
async def get_bucket_flows(
    instance_id: int,
    registry_id: str,
    bucket_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of flows in a specific bucket from a registry client"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security
        from nipyapi.nifi import FlowApi

        # Configure nipyapi for NiFi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials for NiFi
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Use NiFi's FlowApi to get flows from the bucket
        flow_api = FlowApi()
        flows_entity = flow_api.get_flows(registry_id, bucket_id)

        # Convert to serializable format
        flows_list = []
        if hasattr(flows_entity, 'versioned_flows') and flows_entity.versioned_flows:
            for flow in flows_entity.versioned_flows:
                flow_data = {
                    "identifier": flow.versioned_flow.flow_id if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'flow_id') else "Unknown",
                    "name": flow.versioned_flow.flow_name if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'flow_name') else "Unknown",
                    "description": flow.versioned_flow.description if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'description') else "",
                    "bucket_identifier": flow.versioned_flow.bucket_id if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'bucket_id') else bucket_id,
                    "bucket_name": flow.versioned_flow.bucket_name if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'bucket_name') else "",
                    "created_timestamp": flow.versioned_flow.created_timestamp if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'created_timestamp') else None,
                    "modified_timestamp": flow.versioned_flow.modified_timestamp if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'modified_timestamp') else None,
                    "version_count": flow.versioned_flow.version_count if hasattr(flow, 'versioned_flow') and hasattr(flow.versioned_flow, 'version_count') else 0,
                }
                flows_list.append(flow_data)

        return {
            "status": "success",
            "flows": flows_list,
            "count": len(flows_list),
            "registry_id": registry_id,
            "bucket_id": bucket_id
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Failed to get flows from bucket: {error_msg}",
            "flows": [],
            "count": 0
        }
