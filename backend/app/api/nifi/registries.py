"""NiFi registry operations API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.get("/{instance_id}/get-registries")
async def get_registry_clients(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of registry clients configured in NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import versioning

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import versioning
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import versioning

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # Get the registry client
        registry_client = versioning.get_registry_client(
            registry_id, identifier_type="id"
        )

        if not registry_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registry client with id {registry_id} not found",
            )

        # Extract registry details
        registry_name = (
            registry_client.component.name
            if hasattr(registry_client, "component")
            and hasattr(registry_client.component, "name")
            else "Unknown"
        )
        registry_type = (
            registry_client.component.type
            if hasattr(registry_client, "component")
            and hasattr(registry_client.component, "type")
            else "Unknown"
        )

        # Extract properties
        properties = {}
        github_url = None

        if hasattr(registry_client, "component") and hasattr(
            registry_client.component, "properties"
        ):
            properties = registry_client.component.properties

            # For GitHub registries, construct the repository URL
            if "github" in registry_type.lower():
                repo_owner = properties.get("Repository Owner")
                repo_name = properties.get("Repository Name")
                repo_path = properties.get("Repository Path", "")

                if repo_owner and repo_name:
                    github_url = f"https://github.com/{repo_owner}/{repo_name}"
                    if repo_path:
                        github_url += f"/tree/main/{repo_path}"

        return {
            "status": "success",
            "registry_id": registry_id,
            "name": registry_name,
            "type": registry_type,
            "is_github": "github" in registry_type.lower(),
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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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


@router.get("/{instance_id}/registry/{registry_id}/{bucket_id}/{flow_id}/get-versions")
async def get_flow_versions(
    instance_id: int,
    registry_id: str,
    bucket_id: str,
    flow_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of all versions for a specific flow"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import versioning

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # List all versions using NiFi's FlowAPI (goes through registry client)
        flow_versions = versioning.list_flow_versions(
            bucket_id=bucket_id,
            flow_id=flow_id,
            registry_id=registry_id,
            service="nifi",
        )

        # Convert to serializable format
        versions_list = []
        if flow_versions and hasattr(
            flow_versions, "versioned_flow_snapshot_metadata_set"
        ):
            for version_item in flow_versions.versioned_flow_snapshot_metadata_set:
                if hasattr(version_item, "versioned_flow_snapshot_metadata"):
                    metadata = version_item.versioned_flow_snapshot_metadata
                    version_data = {
                        "version": metadata.version
                        if hasattr(metadata, "version")
                        else None,
                        "timestamp": metadata.timestamp
                        if hasattr(metadata, "timestamp")
                        else None,
                        "comments": metadata.comments
                        if hasattr(metadata, "comments")
                        else "",
                        "author": metadata.author
                        if hasattr(metadata, "author")
                        else "Unknown",
                        "bucket_identifier": metadata.bucket_identifier
                        if hasattr(metadata, "bucket_identifier")
                        else bucket_id,
                        "flow_identifier": metadata.flow_identifier
                        if hasattr(metadata, "flow_identifier")
                        else flow_id,
                    }
                    versions_list.append(version_data)

        # Sort by timestamp descending (newest first)
        versions_list.sort(
            key=lambda x: x["timestamp"] if x["timestamp"] else 0, reverse=True
        )

        return {
            "status": "success",
            "versions": versions_list,
            "count": len(versions_list),
            "registry_id": registry_id,
            "bucket_id": bucket_id,
            "flow_id": flow_id,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get flow versions: {error_msg}")
        import traceback

        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to get flow versions: {error_msg}",
            "versions": [],
            "count": 0,
        }
