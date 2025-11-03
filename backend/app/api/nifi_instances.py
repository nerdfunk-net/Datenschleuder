"""NiFi instances management API endpoints"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import (
    NiFiInstance,
    NiFiInstanceCreate,
    NiFiInstanceUpdate,
    NiFiInstanceResponse,
)
from app.models.parameter_context import (
    ParameterContext,
    ParameterEntity,
    ParameterContextListResponse,
    ParameterContextCreate,
    ParameterContextUpdate,
    AssignParameterContextRequest,
    AssignParameterContextResponse,
)
from app.models.deployment import (
    PortsResponse,
    PortInfo,
    ConnectionRequest,
    ConnectionResponse,
    ProcessorInfo,
    ProcessorsResponse,
    InputPortInfo,
    InputPortsResponse,
    ProcessorConfiguration,
    ProcessorConfigurationResponse,
    ProcessorConfigurationUpdate,
    ProcessorConfigurationUpdateResponse,
)
from app.services.encryption_service import encryption_service
from app.utils.nifi_helpers import extract_pg_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nifi-instances", tags=["nifi-instances"])


@router.get("/", response_model=List[NiFiInstanceResponse])
async def list_nifi_instances(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get all NiFi instances"""
    instances = (
        db.query(NiFiInstance)
        .order_by(NiFiInstance.hierarchy_attribute, NiFiInstance.hierarchy_value)
        .all()
    )

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
    existing = (
        db.query(NiFiInstance)
        .filter(
            NiFiInstance.hierarchy_attribute == data.hierarchy_attribute,
            NiFiInstance.hierarchy_value == data.hierarchy_value,
        )
        .first()
    )

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
        certificate_name=data.certificate_name,
        check_hostname=data.check_hostname,
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
        instance.password_encrypted = encryption_service.encrypt_to_string(
            data.password
        )
    if data.use_ssl is not None:
        instance.use_ssl = data.use_ssl
    if data.verify_ssl is not None:
        instance.verify_ssl = data.verify_ssl
    if data.certificate_name is not None:
        instance.certificate_name = data.certificate_name
    if data.check_hostname is not None:
        instance.check_hostname = data.check_hostname

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

    return {
        "message": f"Deleted NiFi instance for {instance.hierarchy_attribute}={instance.hierarchy_value}"
    }


@router.post("/test")
async def test_nifi_connection(
    data: NiFiInstanceCreate,
    token_data: dict = Depends(verify_token),
):
    """Test connection with provided NiFi credentials (without saving)"""
    try:
        from app.services.nifi_auth import configure_nifi_test_connection
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        configure_nifi_test_connection(
            nifi_url=data.nifi_url,
            username=data.username,
            password=data.password,
            verify_ssl=data.verify_ssl,
            certificate_name=data.certificate_name,
            check_hostname=data.check_hostname,
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
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

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
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import versioning

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get list of registry clients
        registry_clients_entity = versioning.list_registry_clients()

        # Extract the actual list of clients from the entity
        clients_list = []
        if (
            hasattr(registry_clients_entity, "registries")
            and registry_clients_entity.registries
        ):
            for client in registry_clients_entity.registries:
                client_data = {
                    "id": client.id if hasattr(client, "id") else "Unknown",
                    "name": client.component.name
                    if hasattr(client, "component")
                    and hasattr(client.component, "name")
                    else "Unknown",
                    "uri": client.component.properties.get("url", "N/A")
                    if hasattr(client, "component")
                    and hasattr(client.component, "properties")
                    else "N/A",
                    "description": client.component.description
                    if hasattr(client, "component")
                    and hasattr(client.component, "description")
                    else "",
                    "type": client.component.type
                    if hasattr(client, "component")
                    and hasattr(client.component, "type")
                    else "Unknown",
                }
                clients_list.append(client_data)

        return {
            "status": "success",
            "registry_clients": clients_list,
            "count": len(clients_list),
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Failed to get registry clients: {error_msg}",
            "registry_clients": [],
            "count": 0,
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
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import versioning
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get the registry client to find its URL
        registry_clients_entity = versioning.list_registry_clients()
        registry_client = None

        if (
            hasattr(registry_clients_entity, "registries")
            and registry_clients_entity.registries
        ):
            for client in registry_clients_entity.registries:
                if client.id == registry_id:
                    registry_client = client
                    break

        if not registry_client:
            return {
                "status": "error",
                "message": f"Registry client with id {registry_id} not found",
                "buckets": [],
                "count": 0,
            }

        # Use NiFi's FlowApi to get buckets from the registry client
        # This works for all registry types (NiFi Registry, GitHub, etc.)
        flow_api = FlowApi()

        # Get buckets using the registry client ID
        buckets_entity = flow_api.get_buckets(registry_id)

        # Convert to serializable format
        buckets_list = []
        if hasattr(buckets_entity, "buckets") and buckets_entity.buckets:
            for bucket in buckets_entity.buckets:
                bucket_data = {
                    "identifier": bucket.id if hasattr(bucket, "id") else "Unknown",
                    "name": bucket.bucket.name
                    if hasattr(bucket, "bucket") and hasattr(bucket.bucket, "name")
                    else "Unknown",
                    "description": bucket.bucket.description
                    if hasattr(bucket, "bucket")
                    and hasattr(bucket.bucket, "description")
                    else "",
                    "created_timestamp": bucket.bucket.created_timestamp
                    if hasattr(bucket, "bucket")
                    and hasattr(bucket.bucket, "created_timestamp")
                    else None,
                    "permissions": bucket.permissions.to_dict()
                    if hasattr(bucket, "permissions")
                    and hasattr(bucket.permissions, "to_dict")
                    else {},
                }
                buckets_list.append(bucket_data)

        registry_type = (
            registry_client.component.type
            if hasattr(registry_client, "component")
            and hasattr(registry_client.component, "type")
            else "Unknown"
        )

        return {
            "status": "success",
            "buckets": buckets_list,
            "count": len(buckets_list),
            "registry_type": registry_type,
            "registry_id": registry_id,
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Failed to get registry buckets: {error_msg}",
            "buckets": [],
            "count": 0,
        }


@router.get("/{instance_id}/registry/{registry_id}/details")
async def get_registry_details(
    instance_id: int,
    registry_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get details about a specific registry client including type and properties"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import versioning

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get the registry client
        registry_client = versioning.get_registry_client(registry_id, identifier_type='id')

        if not registry_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registry client with id {registry_id} not found",
            )

        # Extract registry details
        registry_name = registry_client.component.name if hasattr(registry_client, 'component') and hasattr(registry_client.component, 'name') else 'Unknown'
        registry_type = registry_client.component.type if hasattr(registry_client, 'component') and hasattr(registry_client.component, 'type') else 'Unknown'

        # Extract properties
        properties = {}
        github_url = None

        if hasattr(registry_client, 'component') and hasattr(registry_client.component, 'properties'):
            properties = registry_client.component.properties

            # For GitHub registries, construct the repository URL
            if 'github' in registry_type.lower():
                repo_owner = properties.get('Repository Owner')
                repo_name = properties.get('Repository Name')
                repo_path = properties.get('Repository Path', '')

                if repo_owner and repo_name:
                    github_url = f"https://github.com/{repo_owner}/{repo_name}"
                    if repo_path:
                        github_url += f"/tree/main/{repo_path}"

        return {
            "status": "success",
            "registry_id": registry_id,
            "name": registry_name,
            "type": registry_type,
            "is_github": 'github' in registry_type.lower(),
            "github_url": github_url,
            "properties": properties,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get registry details: {error_msg}",
        )


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
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Use NiFi's FlowApi to get flows from the bucket
        flow_api = FlowApi()
        flows_entity = flow_api.get_flows(registry_id, bucket_id)

        # Convert to serializable format
        flows_list = []
        if hasattr(flows_entity, "versioned_flows") and flows_entity.versioned_flows:
            for flow in flows_entity.versioned_flows:
                flow_data = {
                    "identifier": flow.versioned_flow.flow_id
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "flow_id")
                    else "Unknown",
                    "name": flow.versioned_flow.flow_name
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "flow_name")
                    else "Unknown",
                    "description": flow.versioned_flow.description
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "description")
                    else "",
                    "bucket_identifier": flow.versioned_flow.bucket_id
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "bucket_id")
                    else bucket_id,
                    "bucket_name": flow.versioned_flow.bucket_name
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "bucket_name")
                    else "",
                    "created_timestamp": flow.versioned_flow.created_timestamp
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "created_timestamp")
                    else None,
                    "modified_timestamp": flow.versioned_flow.modified_timestamp
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "modified_timestamp")
                    else None,
                    "version_count": flow.versioned_flow.version_count
                    if hasattr(flow, "versioned_flow")
                    and hasattr(flow.versioned_flow, "version_count")
                    else 0,
                }
                flows_list.append(flow_data)

        return {
            "status": "success",
            "flows": flows_list,
            "count": len(flows_list),
            "registry_id": registry_id,
            "bucket_id": bucket_id,
        }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"Failed to get flows from bucket: {error_msg}",
            "flows": [],
            "count": 0,
        }


@router.get(
    "/{instance_id}/get-parameters", response_model=ParameterContextListResponse
)
async def get_parameter_contexts(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of parameter contexts configured in NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get parameter contexts using the FlowApi
        flow_api = FlowApi()
        param_contexts_entity = flow_api.get_parameter_contexts()

        # Convert to our response model
        contexts_list = []
        if (
            hasattr(param_contexts_entity, "parameter_contexts")
            and param_contexts_entity.parameter_contexts
        ):
            for context in param_contexts_entity.parameter_contexts:
                # Extract parameters
                parameters = []
                if hasattr(context, "component") and hasattr(
                    context.component, "parameters"
                ):
                    for param in context.component.parameters:
                        param_data = ParameterEntity(
                            name=param.parameter.name
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "name")
                            else "Unknown",
                            description=param.parameter.description
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "description")
                            else None,
                            sensitive=param.parameter.sensitive
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "sensitive")
                            else False,
                            value=param.parameter.value
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "value")
                            and not param.parameter.sensitive
                            else None,
                            provided=param.parameter.provided
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "provided")
                            else False,
                            referenced_attributes=param.parameter.referenced_attributes
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "referenced_attributes")
                            else None,
                            parameter_context_id=context.id
                            if hasattr(context, "id")
                            else None,
                        )
                        parameters.append(param_data)

                # Extract bound process groups
                bound_groups = []
                if hasattr(context, "component") and hasattr(
                    context.component, "bound_process_groups"
                ):
                    for pg in context.component.bound_process_groups:
                        if hasattr(pg, "to_dict"):
                            bound_groups.append(pg.to_dict())

                # Extract inherited parameter contexts
                inherited_contexts = []
                if hasattr(context, "component") and hasattr(
                    context.component, "inherited_parameter_contexts"
                ):
                    for ipc in context.component.inherited_parameter_contexts:
                        if hasattr(ipc, "id"):
                            inherited_contexts.append(ipc.id)

                context_data = ParameterContext(
                    id=context.id if hasattr(context, "id") else "Unknown",
                    name=context.component.name
                    if hasattr(context, "component")
                    and hasattr(context.component, "name")
                    else "Unknown",
                    description=context.component.description
                    if hasattr(context, "component")
                    and hasattr(context.component, "description")
                    else None,
                    parameters=parameters,
                    bound_process_groups=bound_groups if bound_groups else None,
                    inherited_parameter_contexts=inherited_contexts
                    if inherited_contexts
                    else None,
                    component_revision=context.revision.to_dict()
                    if hasattr(context, "revision")
                    and hasattr(context.revision, "to_dict")
                    else None,
                    permissions=context.permissions.to_dict()
                    if hasattr(context, "permissions")
                    and hasattr(context.permissions, "to_dict")
                    else None,
                )
                contexts_list.append(context_data)

        return ParameterContextListResponse(
            status="success",
            parameter_contexts=contexts_list,
            count=len(contexts_list),
        )

    except Exception as e:
        error_msg = str(e)
        return ParameterContextListResponse(
            status="error",
            parameter_contexts=[],
            count=0,
            message=f"Failed to get parameter contexts: {error_msg}",
        )


@router.post("/{instance_id}/parameter-contexts")
async def create_parameter_context(
    instance_id: int,
    data: ParameterContextCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new parameter context in NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi.nifi.apis.parameter_contexts_api import ParameterContextsApi
        from nipyapi.nifi.models import (
            ParameterContextEntity,
            ParameterContextDTO,
            ParameterEntity as NiFiParameterEntity,
            ParameterDTO,
        )

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Build parameters list
        parameters = []
        for param in data.parameters:
            param_dto = ParameterDTO(
                name=param.name,
                description=param.description,
                sensitive=param.sensitive,
                value=param.value,
            )
            param_entity = NiFiParameterEntity(parameter=param_dto)
            parameters.append(param_entity)

        # Create parameter context DTO
        param_context_dto = ParameterContextDTO(
            name=data.name,
            description=data.description,
            parameters=parameters if parameters else None,
        )

        # Create parameter context entity
        param_context_entity = ParameterContextEntity(
            component=param_context_dto,
            revision={"version": 0},
        )

        # Create parameter context
        param_api = ParameterContextsApi()
        result = param_api.create_parameter_context(body=param_context_entity)

        return {
            "status": "success",
            "message": "Parameter context created successfully",
            "parameter_context": {
                "id": result.id if hasattr(result, "id") else None,
                "name": result.component.name
                if hasattr(result, "component")
                else data.name,
            },
        }

    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create parameter context: {error_msg}",
        )


@router.put("/{instance_id}/parameter-contexts/{context_id}")
async def update_parameter_context(
    instance_id: int,
    context_id: str,
    data: ParameterContextUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update an existing parameter context in NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi.nifi.apis.parameter_contexts_api import ParameterContextsApi
        from nipyapi.nifi.models import (
            ParameterEntity as NiFiParameterEntity,
            ParameterDTO,
        )
        import time

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get existing parameter context to get current revision
        param_api = ParameterContextsApi()
        existing_context = param_api.get_parameter_context(id=context_id)

        print(
            f"Existing context has {len(existing_context.component.parameters) if existing_context.component.parameters else 0} parameters"
        )
        print(
            f"Update data has {len(data.parameters) if data.parameters else 0} parameters"
        )

        # Get the names of parameters we want to keep
        desired_param_names = set()
        if data.parameters is not None:
            desired_param_names = {param.name for param in data.parameters}

        print(f"Desired parameters: {desired_param_names}")

        # Build complete parameters list - merge existing with updates and mark deletions
        parameters = []
        existing_param_map = {}

        # First, map existing parameters
        if existing_context.component.parameters:
            for existing_param in existing_context.component.parameters:
                param_name = existing_param.parameter.name
                existing_param_map[param_name] = existing_param

        print(f"Existing parameters: {set(existing_param_map.keys())}")

        # Now build the final parameter list
        if data.parameters is not None:
            # Add/update parameters that are in the desired list
            for param in data.parameters:
                print(f"Adding/updating parameter: {param.name} = {param.value}")

                # For updates to existing parameters, we need to preserve the parameter reference
                if param.name in existing_param_map:
                    # Updating existing parameter - modify it
                    existing_param = existing_param_map[param.name]
                    existing_param.parameter.description = param.description
                    existing_param.parameter.sensitive = param.sensitive
                    if (
                        not param.sensitive
                    ):  # Only update value for non-sensitive parameters
                        existing_param.parameter.value = param.value
                    parameters.append(existing_param)
                else:
                    # New parameter - create fresh
                    param_dto = ParameterDTO(
                        name=param.name,
                        description=param.description,
                        sensitive=param.sensitive,
                        value=param.value,
                    )
                    param_entity = NiFiParameterEntity(parameter=param_dto)
                    parameters.append(param_entity)

            # Mark parameters for deletion (exist in NiFi but not in desired list)
            for param_name in existing_param_map.keys():
                if param_name not in desired_param_names:
                    print(f"Marking parameter for deletion: {param_name}")
                    # Create a parameter entity with value_removed=True to mark for deletion
                    delete_param_dto = ParameterDTO(
                        name=param_name,
                        value_removed=True,
                    )
                    delete_param_entity = NiFiParameterEntity(
                        parameter=delete_param_dto
                    )
                    parameters.append(delete_param_entity)
        else:
            # Keep all existing parameters if not provided
            parameters = list(existing_param_map.values())

        print(
            f"Final parameters list has {len(parameters)} parameters (including deletions)"
        )
        for p in parameters:
            if hasattr(p.parameter, "value_removed") and p.parameter.value_removed:
                print(f"  - {p.parameter.name} (MARKED FOR DELETION)")
            else:
                print(f"  - {p.parameter.name}")

        # Now modify the existing context in place
        existing_context.component.parameters = parameters
        if data.name is not None:
            existing_context.component.name = data.name
        if data.description is not None:
            existing_context.component.description = data.description

        # Submit update request with the modified existing context
        update_response = param_api.submit_parameter_context_update(
            context_id=context_id, body=existing_context
        )

        # Wait for update to complete (poll the update request)
        request_id = update_response.request.request_id
        print(f"Update request submitted, request_id: {request_id}")
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            status_response = param_api.get_parameter_context_update(
                context_id=context_id, request_id=request_id
            )

            # Log detailed status information
            percent = (
                status_response.request.percent_completed
                if hasattr(status_response.request, "percent_completed")
                else 0
            )
            state = (
                status_response.request.state
                if hasattr(status_response.request, "state")
                else "unknown"
            )
            print(
                f"Attempt {attempt}: complete={status_response.request.complete}, state={state}, percent={percent}%"
            )

            # Also check for affected components
            if hasattr(status_response.request, "update_steps"):
                print(f"  Update steps: {len(status_response.request.update_steps)}")
                for step in status_response.request.update_steps:
                    if hasattr(step, "description") and hasattr(step, "complete"):
                        print(
                            f"    - {step.description}: {'complete' if step.complete else 'pending'}"
                        )

            if status_response.request.complete:
                # Check if there was a failure
                if (
                    hasattr(status_response.request, "failure_reason")
                    and status_response.request.failure_reason
                ):
                    print(f"Update failed: {status_response.request.failure_reason}")
                    raise Exception(
                        f"Update failed: {status_response.request.failure_reason}"
                    )

                # Verify it's truly complete (100%)
                if percent < 100:
                    print(f"Warning: Marked complete but only {percent}% done")

                print(f"Update completed successfully at {percent}%")

                # Delete the update request
                param_api.delete_update_request(
                    context_id=context_id, request_id=request_id
                )

                # Verify the update by fetching the context again
                print("Verifying update by fetching context...")
                updated_context = param_api.get_parameter_context(id=context_id)
                actual_param_count = (
                    len(updated_context.component.parameters)
                    if updated_context.component.parameters
                    else 0
                )
                expected_param_count = len(parameters)

                print(
                    f"Expected {expected_param_count} parameters, got {actual_param_count}"
                )
                if updated_context.component.parameters:
                    for p in updated_context.component.parameters:
                        print(
                            f"  - {p.parameter.name if hasattr(p, 'parameter') else 'unknown'}"
                        )

                return {
                    "status": "success",
                    "message": "Parameter context updated successfully",
                    "parameter_context": {
                        "id": context_id,
                        "name": data.name or existing_context.component.name,
                        "actual_parameter_count": actual_param_count,
                        "expected_parameter_count": expected_param_count,
                    },
                }

            time.sleep(0.5)
            attempt += 1

        # If we get here, update timed out
        print(f"Update request timed out after {max_attempts} attempts")
        raise Exception("Update request timed out")

    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update parameter context: {error_msg}",
        )


@router.delete("/{instance_id}/parameter-contexts/{context_id}")
async def delete_parameter_context(
    instance_id: int,
    context_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a parameter context from NiFi instance"""
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi.nifi.apis.parameter_contexts_api import ParameterContextsApi

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get existing parameter context to get current revision
        param_api = ParameterContextsApi()
        existing_context = param_api.get_parameter_context(id=context_id)

        # Delete parameter context
        param_api.delete_parameter_context(
            id=context_id,
            version=existing_context.revision.version,
        )

        return {
            "status": "success",
            "message": "Parameter context deleted successfully",
        }

    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete parameter context: {error_msg}",
        )


@router.get("/{instance_id}/registry/{registry_id}/{bucket_id}/export-flow")
async def export_flow(
    instance_id: int,
    registry_id: str,
    bucket_id: str,
    flow_id: str,
    version: str = None,
    mode: str = "json",
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Export a flow from registry using nipyapi.versioning.export_flow_version"""
    from fastapi.responses import Response
    import nipyapi
    from nipyapi import config, versioning

    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection

        # Configure nipyapi for NiFi instance
        configure_nifi_connection(instance)

        # Validate mode parameter
        if mode not in ["json", "yaml"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mode must be 'json' or 'yaml'",
            )

        # Verify the registry client exists and get its type
        registry_clients = versioning.list_registry_clients()
        registry_found = False
        registry_client = None
        registry_type = None

        if hasattr(registry_clients, 'registries') and registry_clients.registries:
            for client in registry_clients.registries:
                if client.id == registry_id:
                    registry_found = True
                    registry_client = client
                    if hasattr(client, 'component') and hasattr(client.component, 'type'):
                        registry_type = client.component.type
                    break

        if not registry_found:
            available_registries = []
            if hasattr(registry_clients, 'registries') and registry_clients.registries:
                available_registries = [f"{c.id} ({c.component.name if hasattr(c, 'component') else 'unknown'})" for c in registry_clients.registries]

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registry client with id '{registry_id}' not found. Available registries: {', '.join(available_registries) if available_registries else 'none'}",
            )

        # Check if this is a GitHub or other external registry type
        is_external_registry = registry_type and ('github' in registry_type.lower() or 'git' in registry_type.lower())

        if is_external_registry:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Export is not supported for {registry_type} registries. Please access the flow files directly from your Git repository.",
            )

        # For NiFi Registry, use nipyapi's built-in export function
        exported_content = versioning.export_flow_version(
            bucket_id=bucket_id,
            flow_id=flow_id,
            version=version,
            mode=mode
        )

        # Get flow name for filename
        flow_name = flow_id
        try:
            flow = versioning.get_flow_in_bucket(bucket_id, identifier=flow_id)
            if hasattr(flow, 'name'):
                flow_name = flow.name
        except:
            pass

        # Generate filename
        version_suffix = f"_v{version}" if version else "_latest"
        filename = f"{flow_name}{version_suffix}.{mode}"

        # Set appropriate content type
        content_type = "application/json" if mode == "json" else "application/x-yaml"

        return Response(
            content=exported_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export flow: {error_msg}",
        )


@router.post("/{instance_id}/registry/{registry_id}/{bucket_id}/import-flow")
async def import_flow(
    instance_id: int,
    registry_id: str,
    bucket_id: str,
    file: UploadFile = File(...),
    flow_name: str = Form(None),
    flow_id: str = Form(None),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Import a flow to registry using nipyapi.versioning.import_flow_version"""
    import nipyapi
    from nipyapi import config, versioning

    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NiFi instance not found",
        )

    # Validate parameters
    if not flow_name and not flow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either flow_name (for new flow) or flow_id (for existing flow) must be provided",
        )

    # Validate file type
    if not file.filename.endswith(('.json', '.yaml', '.yml')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON or YAML file",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection

        # Configure nipyapi for NiFi instance
        configure_nifi_connection(instance)

        # Verify the registry client exists and get its type
        registry_clients = versioning.list_registry_clients()
        registry_found = False
        registry_client = None
        registry_type = None

        if hasattr(registry_clients, 'registries') and registry_clients.registries:
            for client in registry_clients.registries:
                if client.id == registry_id:
                    registry_found = True
                    registry_client = client
                    if hasattr(client, 'component') and hasattr(client.component, 'type'):
                        registry_type = client.component.type
                    break

        if not registry_found:
            available_registries = []
            if hasattr(registry_clients, 'registries') and registry_clients.registries:
                available_registries = [f"{c.id} ({c.component.name if hasattr(c, 'component') else 'unknown'})" for c in registry_clients.registries]

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registry client with id '{registry_id}' not found. Available registries: {', '.join(available_registries) if available_registries else 'none'}",
            )

        # Check if this is a GitHub or other external registry type
        is_external_registry = registry_type and ('github' in registry_type.lower() or 'git' in registry_type.lower())

        if is_external_registry:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Import is not supported for {registry_type} registries. Please commit the flow directly to your Git repository.",
            )

        # Read the uploaded file content
        file_content = await file.read()
        encoded_flow = file_content.decode('utf-8')

        # For NiFi Registry, use nipyapi's built-in import function
        imported_flow = versioning.import_flow_version(
            bucket_id=bucket_id,
            encoded_flow=encoded_flow,
            flow_name=flow_name,
            flow_id=flow_id
        )

        # Extract flow information from the response
        result_flow_name = flow_name
        result_flow_id = flow_id
        result_version = "unknown"

        if hasattr(imported_flow, 'snapshot_metadata'):
            metadata = imported_flow.snapshot_metadata
            if hasattr(metadata, 'flow_identifier'):
                result_flow_id = metadata.flow_identifier
            if hasattr(metadata, 'version'):
                result_version = str(metadata.version)

        if hasattr(imported_flow, 'flow'):
            if hasattr(imported_flow.flow, 'identifier'):
                result_flow_id = imported_flow.flow.identifier
            if hasattr(imported_flow.flow, 'name'):
                result_flow_name = imported_flow.flow.name

        return {
            "status": "success",
            "message": "Flow imported successfully",
            "flow_name": result_flow_name or "Unknown",
            "flow_id": result_flow_id or "Unknown",
            "version": result_version,
            "filename": file.filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import flow: {error_msg}",
        )


# ============================================================================
# Process Group Management Endpoints (moved from deploy.py)
# ============================================================================


@router.get("/{instance_id}/process-group")
async def get_process_group(
    instance_id: int,
    id: str = None,
    name: str = None,
    greedy: bool = True,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a process group by ID or name.

    Either 'id' or 'name' parameter must be provided.
    If 'id' is provided, searches by process group ID.
    If 'name' is provided, searches by process group name.

    Args:
        instance_id: ID of the NiFi instance
        id: Optional process group ID to search for
        name: Optional process group name to search for
        greedy: If True (default), allows partial matching. If False, requires exact match.

    Returns:
        Process group information (id, name, parent_group_id, etc.)
        If multiple matches found, returns a list of process groups.
    """
    # Validate that at least one search parameter is provided
    if not id and not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'id' or 'name' parameter must be provided",
        )

    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Search for process group by ID or name
        process_group_result = None

        if id:
            logger.info(f"Searching for process group with ID: {id} (greedy={greedy})")
            process_group_result = canvas.get_process_group(
                identifier=id, identifier_type="id", greedy=greedy
            )
        elif name:
            logger.info(f"Searching for process group with name: {name} (greedy={greedy})")
            process_group_result = canvas.get_process_group(
                identifier=name, identifier_type="name", greedy=greedy
            )

        if process_group_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group not found with {'ID' if id else 'name'}: {id or name}",
            )

        # Handle different return types
        if isinstance(process_group_result, list):
            if len(process_group_result) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group not found with {'ID' if id else 'name'}: {id or name}",
                )

            # Multiple matches - return as list
            pg_list = [extract_pg_info(pg) for pg in process_group_result]
            logger.info(f"Found {len(pg_list)} process groups")

            return {
                "status": "success",
                "process_groups": pg_list,
                "count": len(pg_list),
            }
        else:
            # Single match
            pg_info = extract_pg_info(process_group_result)
            logger.info(f"Found process group: {pg_info['name']} (ID: {pg_info['id']})")

            return {
                "status": "success",
                "process_group": pg_info,
            }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get process group: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group: {error_msg}",
        )


@router.get("/{instance_id}/process-groups")
async def search_process_groups(
    instance_id: int,
    name: str = None,
    parent_id: str = None,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Search for process groups on a NiFi instance by name and/or parent.

    If name is not provided, returns all process groups (or children of parent_id if specified).
    If name is provided, searches for process groups matching that name.
    If parent_id is provided, only returns children of that process group.

    Args:
        instance_id: ID of the NiFi instance
        name: Optional name to search for (supports partial matching)
        parent_id: Optional parent process group ID to search within

    Returns:
        List of process groups with id, name, and parent information.
        If both name and parent_id are provided, checks if a child with that name exists.
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        process_groups = []

        if parent_id and name:
            # Check for a specific child process group by name within a parent
            logger.info(
                f"Checking for child process group with name '{name}' in parent '{parent_id}'"
            )

            # Get all process groups from the parent
            from nipyapi.nifi import ProcessGroupsApi

            pg_api = ProcessGroupsApi()
            parent_pg_response = pg_api.get_process_groups(id=parent_id)

            if hasattr(parent_pg_response, "process_groups"):
                for pg in parent_pg_response.process_groups:
                    if hasattr(pg, "component") and hasattr(pg.component, "name"):
                        if pg.component.name == name:
                            process_groups.append(pg)
        elif parent_id:
            # List all children of a specific parent
            logger.info(f"Listing all child process groups of parent '{parent_id}'")

            from nipyapi.nifi import ProcessGroupsApi

            pg_api = ProcessGroupsApi()
            parent_pg_response = pg_api.get_process_groups(id=parent_id)

            if hasattr(parent_pg_response, "process_groups"):
                process_groups = parent_pg_response.process_groups
        elif name:
            # Search for process groups by name (globally)
            logger.info(f"Searching for process groups with name: {name}")
            result = canvas.get_process_group(
                identifier=name, identifier_type="name", greedy=True
            )

            # Handle different return types
            if result is None:
                # No matches
                process_groups = []
            elif isinstance(result, list):
                # Multiple matches
                process_groups = result
            else:
                # Single match
                process_groups = [result]
        else:
            # List all process groups
            logger.info("Listing all process groups")
            process_groups = canvas.list_all_process_groups()

        # Format the response
        pg_list = []
        for pg in process_groups:
            pg_info = extract_pg_info(pg)
            pg_list.append(pg_info)

        logger.info(f"Found {len(pg_list)} process groups")

        return {
            "status": "success",
            "process_groups": pg_list,
            "count": len(pg_list),
            "search_name": name,
            "parent_id": parent_id,
            "exists": len(pg_list) > 0 if (parent_id and name) else None,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to search process groups: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search process groups: {error_msg}",
        )


@router.get("/{instance_id}/get-path")
async def get_process_group_path(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the full path from a process group to the root.

    Returns a list of all parent process groups from the specified process group
    up to the root process group.

    Args:
        instance_id: ID of the NiFi instance
        process_group_id: ID of the process group to get path for

    Returns:
        List of process groups representing the path to root, with each entry
        containing id, name, and parent_group_id. The list starts with the
        specified process group and ends with the root.
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get root process group ID for comparison
        root_pg_id = canvas.get_root_pg_id()
        logger.info(f"Root process group ID: {root_pg_id}")

        # Build path from process_group_id to root
        path = []
        current_pg_id = process_group_id
        visited_ids = set()  # Prevent infinite loops

        logger.info(f"Building path from process group ID: {process_group_id}")

        while current_pg_id:
            # Check for circular reference
            if current_pg_id in visited_ids:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Circular reference detected in process group hierarchy at ID: {current_pg_id}",
                )
            visited_ids.add(current_pg_id)

            # Get current process group
            try:
                current_pg = canvas.get_process_group(
                    identifier=current_pg_id, identifier_type="id", greedy=False
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group with ID '{current_pg_id}' not found: {str(e)}",
                )

            if current_pg is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group with ID '{current_pg_id}' not found",
                )

            # Handle list return (shouldn't happen with ID search, but be safe)
            if isinstance(current_pg, list):
                if len(current_pg) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Process group with ID '{current_pg_id}' not found",
                    )
                current_pg = current_pg[0]

            # Extract process group info
            pg_info = extract_pg_info(current_pg)

            path.append(pg_info)
            logger.debug(
                f"Added to path: {pg_info['name']} (ID: {pg_info['id']}, Parent: {pg_info['parent_group_id']})"
            )

            # Check if we've reached the root
            if current_pg_id == root_pg_id:
                logger.debug("Reached root process group")
                break

            # Move to parent
            parent_id = pg_info["parent_group_id"]
            if not parent_id:
                # No parent means we're at root
                logger.debug("No parent ID - reached root")
                break

            current_pg_id = parent_id

        logger.info(f"Path built successfully with {len(path)} levels")

        return {
            "status": "success",
            "path": path,
            "depth": len(path),
            "root_id": root_pg_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get process group path: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group path: {error_msg}",
        )


@router.get("/{instance_id}/get-all-paths")
async def get_all_process_group_paths(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get all process group paths from the NiFi instance.

    Returns a list of all process groups with their full paths to the root.
    This endpoint recursively traverses the entire canvas starting from root.

    Args:
        instance_id: ID of the NiFi instance

    Returns:
        List of all process groups with their paths, where each entry contains:
        - id: Process group ID
        - name: Process group name
        - parent_group_id: Parent process group ID
        - path: List of parent process groups from this PG to root
        - depth: How deep in the hierarchy (0 = root)
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get root process group ID
        root_pg_id = canvas.get_root_pg_id()
        logger.info(f"Root process group ID: {root_pg_id}")

        # Get all process groups using nipyapi's recursive function
        logger.info("Fetching all process groups...")
        all_process_groups = canvas.list_all_process_groups(pg_id=root_pg_id)
        logger.info(f"Found {len(all_process_groups)} process groups")

        # Build a map of process groups for quick lookup
        pg_map = {}
        for pg in all_process_groups:
            pg_id = pg.id if hasattr(pg, "id") else None
            if pg_id:
                pg_map[pg_id] = {
                    "id": pg_id,
                    "name": pg.component.name
                    if hasattr(pg, "component") and hasattr(pg.component, "name")
                    else None,
                    "parent_group_id": pg.component.parent_group_id
                    if hasattr(pg, "component")
                    and hasattr(pg.component, "parent_group_id")
                    else None,
                    "comments": pg.component.comments
                    if hasattr(pg, "component") and hasattr(pg.component, "comments")
                    else None,
                }

        # Function to build path for a process group
        def build_path(pg_id):
            path = []
            current_id = pg_id
            visited = set()

            while current_id and current_id in pg_map:
                if current_id in visited:
                    # Circular reference
                    break
                visited.add(current_id)

                pg_info = pg_map[current_id]
                path.append(
                    {
                        "id": pg_info["id"],
                        "name": pg_info["name"],
                        "parent_group_id": pg_info["parent_group_id"],
                    }
                )

                # Check if we've reached root
                if current_id == root_pg_id or not pg_info["parent_group_id"]:
                    break

                current_id = pg_info["parent_group_id"]

            return path

        # Build result with paths for each process group
        result = []
        for pg_id, pg_info in pg_map.items():
            path = build_path(pg_id)

            result.append(
                {
                    "id": pg_info["id"],
                    "name": pg_info["name"],
                    "parent_group_id": pg_info["parent_group_id"],
                    "comments": pg_info["comments"],
                    "path": path,
                    "depth": len(path)
                    - 1,  # depth is path length minus 1 (root is depth 0)
                }
            )

        # Sort by depth (root first, then children, etc.)
        result.sort(key=lambda x: x["depth"])

        logger.info(f"Built paths for {len(result)} process groups")

        return {
            "status": "success",
            "process_groups": result,
            "count": len(result),
            "root_id": root_pg_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get all process group paths: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all process group paths: {error_msg}",
        )


@router.get("/{instance_id}/get-root")
async def get_root_process_group(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the root process group ID for a NiFi instance.

    This is useful as the default parent_process_group_id for deployments.

    Args:
        instance_id: ID of the NiFi instance

    Returns:
        Root process group ID and name
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance)

        # Get root process group ID
        root_pg_id = canvas.get_root_pg_id()
        logger.info(f"Root process group ID: {root_pg_id}")

        # Get root process group details
        root_pg = canvas.get_process_group(root_pg_id, identifier_type="id")

        root_pg_name = None
        if (
            root_pg
            and hasattr(root_pg, "component")
            and hasattr(root_pg.component, "name")
        ):
            root_pg_name = root_pg.component.name

        return {
            "status": "success",
            "root_process_group_id": root_pg_id,
            "name": root_pg_name,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get root process group: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get root process group: {error_msg}",
        )


@router.get(
    "/{instance_id}/process-group/{process_group_id}/output-ports",
    response_model=PortsResponse,
)
async def get_output_ports(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get all output ports for a specific process group.

    Args:
        instance_id: The NiFi instance ID
        process_group_id: The process group ID to get output ports from

    Returns:
        List of output ports with their details
    """
    # Get the NiFi instance
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance, normalize_url=True)

        # Get process group info
        pg = canvas.get_process_group(
            process_group_id, identifier_type="id", greedy=False
        )
        if isinstance(pg, list):
            pg = pg[0]
        pg_name = pg.component.name if hasattr(pg, "component") else None

        # Get output ports
        logger.info(f"Getting output ports for process group {process_group_id} ({pg_name})")
        output_ports = canvas.list_all_output_ports(
            pg_id=process_group_id, descendants=False
        )

        ports = []
        for port in output_ports:
            ports.append(
                PortInfo(
                    id=port.id,
                    name=port.component.name,
                    state=port.component.state,
                    comments=port.component.comments
                    if hasattr(port.component, "comments")
                    else None,
                )
            )

        logger.info(f"Found {len(ports)} output ports")
        for port in ports:
            logger.debug(f"  - {port.name} (ID: {port.id}, State: {port.state})")

        return PortsResponse(
            process_group_id=process_group_id, process_group_name=pg_name, ports=ports
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get output ports: {error_msg}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get output ports: {error_msg}",
        )


@router.post("/{instance_id}/connection", response_model=ConnectionResponse)
async def create_connection(
    instance_id: int,
    connection_request: ConnectionRequest,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Create a connection between two components (ports, processors, etc).

    Typically used to connect an output port from a deployed process group
    to an output port of the parent process group.

    Args:
        instance_id: The NiFi instance ID
        connection_request: Connection details (source_id, target_id, optional name and relationships)

    Returns:
        Connection details including the connection ID
    """
    # Get the NiFi instance
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance, normalize_url=True)

        # Get source and target components
        # We need to get the actual component objects to pass to create_connection
        from nipyapi.nifi import ProcessGroupsApi

        pg_api = ProcessGroupsApi()

        # Try to get source as output port first
        try:
            source = pg_api.get_output_port(connection_request.source_id)
            source_name = source.component.name
            source_type = "Output Port"
        except Exception:
            # Try as processor or other component type
            try:
                from nipyapi.nifi import ProcessorsApi

                proc_api = ProcessorsApi()
                source = proc_api.get_processor(connection_request.source_id)
                source_name = source.component.name
                source_type = "Processor"
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source component with ID {connection_request.source_id} not found",
                )

        # Try to get target as output port first
        try:
            target = pg_api.get_output_port(connection_request.target_id)
            target_name = target.component.name
            target_type = "Output Port"
        except Exception:
            # Try as processor or other component type
            try:
                from nipyapi.nifi import ProcessorsApi

                proc_api = ProcessorsApi()
                target = proc_api.get_processor(connection_request.target_id)
                target_name = target.component.name
                target_type = "Processor"
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target component with ID {connection_request.target_id} not found",
                )

        logger.info("Creating connection:")
        logger.info(
            f"  Source: {source_name} ({source_type}, ID: {connection_request.source_id})"
        )
        logger.info(
            f"  Target: {target_name} ({target_type}, ID: {connection_request.target_id})"
        )

        # Create connection
        connection = canvas.create_connection(
            source=source,
            target=target,
            relationships=connection_request.relationships,
            name=connection_request.name,
        )

        logger.info(f"✓ Connection created: {connection.id}")

        return ConnectionResponse(
            status="success",
            message=f"Connection created from {source_name} to {target_name}",
            connection_id=connection.id,
            source_id=connection_request.source_id,
            source_name=source_name,
            target_id=connection_request.target_id,
            target_name=target_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to create connection: {error_msg}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {error_msg}",
        )


@router.delete("/{instance_id}/process-group/{process_group_id}")
async def delete_process_group(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete a process group from a NiFi instance.
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, canvas

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

        logger.info(f"Deleting process group {process_group_id}...")

        # Get the process group first
        from nipyapi.nifi import ProcessGroupsApi

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        # Delete the process group
        canvas.delete_process_group(pg, force=True, refresh=True)

        logger.info("✓ Process group deleted successfully")

        return {
            "status": "success",
            "message": "Process group deleted successfully",
            "process_group_id": process_group_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to delete process group: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete process group: {error_msg}",
        )


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
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

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


@router.post(
    "/{instance_id}/process-group/{process_group_id}/add-parameter",
    response_model=AssignParameterContextResponse,
)
async def assign_parameter_context_to_process_group(
    instance_id: int,
    process_group_id: str,
    request: AssignParameterContextRequest,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Assign a parameter context to a process group.

    Args:
        instance_id: NiFi instance ID
        process_group_id: Process group ID to assign parameter context to
        request: Request body containing parameter_context_id and cascade flag
        token_data: Authentication token data
        db: Database session

    Returns:
        Response with status and details of the assignment
    """
    try:
        # Get NiFi instance
        instance = (
            db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        )

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with ID {instance_id} not found",
            )

        logger.info(
            f"Assigning parameter context {request.parameter_context_id} to "
            f"process group {process_group_id} on instance {instance_id}"
        )
        logger.info(f"  Cascade: {request.cascade}")

        # Configure NiFi connection
        from app.services.nifi_auth import configure_nifi_connection

        configure_nifi_connection(instance)

        # Get the process group
        from nipyapi.nifi import ProcessGroupsApi
        from nipyapi import parameters

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group with ID {process_group_id} not found",
            )

        logger.info(f"Found process group: {pg.component.name if hasattr(pg, 'component') and hasattr(pg.component, 'name') else process_group_id}")

        # Assign parameter context to process group
        logger.info(f"Calling nipyapi.parameters.assign_context_to_process_group...")
        result = parameters.assign_context_to_process_group(
            pg=pg,
            context_id=request.parameter_context_id,
            cascade=request.cascade,
        )

        logger.info(f"✓ Parameter context assigned successfully")

        return AssignParameterContextResponse(
            status="success",
            message=f"Parameter context assigned to process group successfully",
            process_group_id=process_group_id,
            parameter_context_id=request.parameter_context_id,
            cascade=request.cascade,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to assign parameter context: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign parameter context: {error_msg}",
        )


@router.get(
    "/{instance_id}/process-group/{process_group_id}/processors",
    response_model=ProcessorsResponse,
)
async def get_process_group_processors(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get list of all processors in a process group.

    Args:
        instance_id: NiFi instance ID
        process_group_id: Process group ID to list processors from
        token_data: Authentication token data
        db: Database session

    Returns:
        Response with list of processors in the process group
    """
    try:
        # Get NiFi instance
        instance = (
            db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        )

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with ID {instance_id} not found",
            )

        logger.info(
            f"Getting processors for process group {process_group_id} "
            f"on instance {instance_id}"
        )

        # Configure NiFi connection
        from app.services.nifi_auth import configure_nifi_connection

        configure_nifi_connection(instance)

        # Get the process group to verify it exists and get its name
        from nipyapi.nifi import ProcessGroupsApi
        from nipyapi import canvas

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group with ID {process_group_id} not found",
            )

        pg_name = (
            pg.component.name
            if hasattr(pg, "component") and hasattr(pg.component, "name")
            else None
        )

        logger.info(f"Found process group: {pg_name or process_group_id}")

        # Get all processors in the process group
        logger.info(f"Fetching processors using nipyapi.canvas.list_all_processors...")
        processors_list = canvas.list_all_processors(pg_id=process_group_id)

        # Convert to our response model
        processors_info = []
        if processors_list:
            for processor in processors_list:
                processor_data = ProcessorInfo(
                    id=processor.id if hasattr(processor, "id") else "Unknown",
                    name=processor.component.name
                    if hasattr(processor, "component")
                    and hasattr(processor.component, "name")
                    else "Unknown",
                    type=processor.component.type
                    if hasattr(processor, "component")
                    and hasattr(processor.component, "type")
                    else "Unknown",
                    state=processor.status.run_status
                    if hasattr(processor, "status")
                    and hasattr(processor.status, "run_status")
                    else "Unknown",
                    parent_group_id=processor.component.parent_group_id
                    if hasattr(processor, "component")
                    and hasattr(processor.component, "parent_group_id")
                    else None,
                    comments=processor.component.config.comments
                    if hasattr(processor, "component")
                    and hasattr(processor.component, "config")
                    and hasattr(processor.component.config, "comments")
                    else None,
                )
                processors_info.append(processor_data)

        logger.info(f"✓ Found {len(processors_info)} processor(s)")

        return ProcessorsResponse(
            status="success",
            process_group_id=process_group_id,
            process_group_name=pg_name,
            processors=processors_info,
            count=len(processors_info),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get processors: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processors: {error_msg}",
        )


@router.get(
    "/{instance_id}/process-group/{process_group_id}/input-ports",
    response_model=InputPortsResponse,
)
async def get_process_group_input_ports(
    instance_id: int,
    process_group_id: str,
    descendants: bool = True,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get list of all input ports in a process group.

    Args:
        instance_id: NiFi instance ID
        process_group_id: Process group ID to list input ports from
        descendants: Whether to include input ports from descendant process groups (default: True)
        token_data: Authentication token data
        db: Database session

    Returns:
        Response with list of input ports in the process group
    """
    try:
        # Get NiFi instance
        instance = (
            db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        )

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NiFi instance with ID {instance_id} not found",
            )

        logger.info(
            f"Getting input ports for process group {process_group_id} "
            f"on instance {instance_id} (descendants={descendants})"
        )

        # Configure NiFi connection
        from app.services.nifi_auth import configure_nifi_connection

        configure_nifi_connection(instance)

        # Get the process group to verify it exists and get its name
        from nipyapi.nifi import ProcessGroupsApi
        from nipyapi import canvas

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group with ID {process_group_id} not found",
            )

        pg_name = (
            pg.component.name
            if hasattr(pg, "component") and hasattr(pg.component, "name")
            else None
        )

        logger.info(f"Found process group: {pg_name or process_group_id}")

        # Get all input ports in the process group
        logger.info(f"Fetching input ports using nipyapi.canvas.list_all_input_ports...")
        input_ports_list = canvas.list_all_input_ports(
            pg_id=process_group_id, descendants=descendants
        )

        # Convert to our response model
        input_ports_info = []
        if input_ports_list:
            for port in input_ports_list:
                port_data = InputPortInfo(
                    id=port.id if hasattr(port, "id") else "Unknown",
                    name=port.component.name
                    if hasattr(port, "component")
                    and hasattr(port.component, "name")
                    else "Unknown",
                    state=port.status.run_status
                    if hasattr(port, "status")
                    and hasattr(port.status, "run_status")
                    else "Unknown",
                    parent_group_id=port.component.parent_group_id
                    if hasattr(port, "component")
                    and hasattr(port.component, "parent_group_id")
                    else None,
                    comments=port.component.comments
                    if hasattr(port, "component")
                    and hasattr(port.component, "comments")
                    else None,
                    concurrent_tasks=port.component.concurrently_schedulable_task_count
                    if hasattr(port, "component")
                    and hasattr(port.component, "concurrently_schedulable_task_count")
                    else None,
                )
                input_ports_info.append(port_data)

        logger.info(f"✓ Found {len(input_ports_info)} input port(s)")

        return InputPortsResponse(
            status="success",
            process_group_id=process_group_id,
            process_group_name=pg_name,
            input_ports=input_ports_info,
            count=len(input_ports_info),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get input ports: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get input ports: {error_msg}",
        )


@router.get(
    "/{instance_id}/processor/{processor_id}/configuration",
    response_model=ProcessorConfigurationResponse,
)
def get_processor_configuration(
    instance_id: int,
    processor_id: str,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get processor configuration details.

    This endpoint retrieves the configuration of a specific processor including:
    - Processor properties (key-value pairs)
    - Scheduling configuration (period, strategy, execution node)
    - Runtime settings (penalty, yield duration)
    - Auto-terminated relationships
    - Concurrent tasks and run duration

    Args:
        instance_id: ID of the NiFi instance
        processor_id: ID of the processor
        current_user: Authenticated user
        db: Database session

    Returns:
        ProcessorConfigurationResponse: Processor configuration details

    Raises:
        HTTPException:
            - 404: Instance or processor not found
            - 403: Insufficient permissions
            - 500: Configuration retrieval failed
    """
    logger.info("=" * 80)
    logger.info(f"GET PROCESSOR CONFIGURATION REQUEST")
    logger.info(f"User: {current_user.get('sub', 'unknown')}")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"Processor ID: {processor_id}")
    logger.info("=" * 80)

    try:
        # Get instance from DB
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instance {instance_id} not found",
            )

        logger.info(f"Found instance: {instance.hierarchy_value}")

        # Initialize NiFi connection
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        configure_nifi_connection(instance)

        logger.info(f"Retrieving processor {processor_id} configuration")

        # Get processor object
        processor = canvas.get_processor(processor_id, "id")

        if not processor:
            logger.warning(f"Processor {processor_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processor {processor_id} not found",
            )

        logger.info(f"Found processor: {processor.component.name}")
        logger.info(f"Processor type: {processor.component.type}")
        logger.info(f"Processor state: {processor.component.state}")

        # Extract configuration details
        component = processor.component
        config_obj = component.config

        # Build properties dict
        properties = {}
        if config_obj and config_obj.properties:
            properties = dict(config_obj.properties)
            logger.info(f"Processor has {len(properties)} properties")

        # Extract scheduling and runtime configuration
        scheduling_period = config_obj.scheduling_period if config_obj else None
        scheduling_strategy = config_obj.scheduling_strategy if config_obj else None
        execution_node = config_obj.execution_node if config_obj else None
        penalty_duration = config_obj.penalty_duration if config_obj else None
        yield_duration = config_obj.yield_duration if config_obj else None
        bulletin_level = config_obj.bulletin_level if config_obj else None
        comments = config_obj.comments if config_obj else None
        auto_terminated_relationships = (
            list(config_obj.auto_terminated_relationships)
            if config_obj and config_obj.auto_terminated_relationships
            else []
        )
        run_duration_millis = config_obj.run_duration_millis if config_obj else None
        concurrent_tasks = (
            config_obj.concurrently_schedulable_task_count if config_obj else None
        )

        logger.info(f"Scheduling: {scheduling_strategy} - {scheduling_period}")
        logger.info(f"Concurrent tasks: {concurrent_tasks}")
        logger.info(f"Auto-terminated relationships: {auto_terminated_relationships}")

        # Create configuration model
        processor_config = ProcessorConfiguration(
            id=component.id,
            name=component.name,
            type=component.type,
            state=component.state,
            properties=properties,
            scheduling_period=scheduling_period,
            scheduling_strategy=scheduling_strategy,
            execution_node=execution_node,
            penalty_duration=penalty_duration,
            yield_duration=yield_duration,
            bulletin_level=bulletin_level,
            comments=comments,
            auto_terminated_relationships=auto_terminated_relationships,
            run_duration_millis=run_duration_millis,
            concurrent_tasks=concurrent_tasks,
        )

        logger.info("Successfully retrieved processor configuration")
        logger.info("=" * 80)

        return ProcessorConfigurationResponse(
            status="success",
            processor=processor_config,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get processor configuration: {error_msg}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processor configuration: {error_msg}",
        )


@router.put(
    "/{instance_id}/processor/{processor_id}/configuration",
    response_model=ProcessorConfigurationUpdateResponse,
)
def update_processor_configuration(
    instance_id: int,
    processor_id: str,
    config_update: ProcessorConfigurationUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Update processor configuration.

    This endpoint updates the configuration of a specific processor. You can update:
    - Processor properties (key-value pairs)
    - Scheduling configuration (period, strategy, execution node)
    - Runtime settings (penalty, yield duration)
    - Auto-terminated relationships
    - Concurrent tasks and run duration
    - Processor name and comments

    Only the fields provided in the request will be updated. Omitted fields remain unchanged.

    Args:
        instance_id: ID of the NiFi instance
        processor_id: ID of the processor
        config_update: Configuration updates to apply
        current_user: Authenticated user
        db: Database session

    Returns:
        ProcessorConfigurationUpdateResponse: Update status and processor details

    Raises:
        HTTPException:
            - 404: Instance or processor not found
            - 403: Insufficient permissions
            - 500: Configuration update failed
    """
    logger.info("=" * 80)
    logger.info(f"UPDATE PROCESSOR CONFIGURATION REQUEST")
    logger.info(f"User: {current_user.get('sub', 'unknown')}")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"Processor ID: {processor_id}")
    logger.info(f"Config update: {config_update.dict(exclude_none=True)}")
    logger.info("=" * 80)

    try:
        # Get instance from DB
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

        if not instance:
            logger.warning(f"Instance {instance_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instance {instance_id} not found",
            )

        logger.info(f"Found instance: {instance.hierarchy_value}")

        # Initialize NiFi connection
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import canvas

        configure_nifi_connection(instance)

        logger.info(f"Retrieving processor {processor_id} for update")

        # Get current processor object
        processor = canvas.get_processor(processor_id, "id")

        if not processor:
            logger.warning(f"Processor {processor_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processor {processor_id} not found",
            )

        logger.info(f"Found processor: {processor.component.name}")
        logger.info(f"Current state: {processor.component.state}")

        # Build update payload - only include fields that are provided
        update_dict = config_update.dict(exclude_none=True)
        logger.info(f"Updating {len(update_dict)} configuration fields")

        # Use nipyapi.canvas.update_processor
        updated_processor = canvas.update_processor(
            processor=processor,
            update=update_dict,
        )

        if not updated_processor:
            logger.error("Processor update returned None")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update processor configuration",
            )

        logger.info(f"Successfully updated processor: {updated_processor.component.name}")
        logger.info("=" * 80)

        return ProcessorConfigurationUpdateResponse(
            status="success",
            message=f"Processor configuration updated successfully",
            processor_id=updated_processor.component.id,
            processor_name=updated_processor.component.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to update processor configuration: {error_msg}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update processor configuration: {error_msg}",
        )
