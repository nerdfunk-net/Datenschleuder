"""Flow deployment API endpoints"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance
from app.models.registry_flow import RegistryFlow
from app.models.deployment import (
    DeploymentRequest,
    DeploymentResponse,
)
from app.models.parameter_context import (
    AssignParameterContextRequest,
    AssignParameterContextResponse,
)
from app.services.encryption_service import encryption_service
from app.services.nifi_deployment_service import NiFiDeploymentService
from app.utils.nifi_helpers import extract_pg_info

router = APIRouter()
logger = logging.getLogger(__name__)


def find_or_create_process_group_by_path(path: str) -> str:
    """
    Find process group ID by path, creating missing parent process groups if needed.
    Returns the process group ID for the given path, or root PG ID if path is empty.

    If the path doesn't exist, this function will:
    1. Find the deepest existing parent in the path
    2. Create all missing process groups from that point
    3. Return the ID of the final (target) process group

    Args:
        path: The process group path to find or create

    Returns:
        Process group ID of the target path
    """
    from nipyapi import canvas

    if not path or path == "/" or path == "":
        return canvas.get_root_pg_id()

    # Split path and remove empty parts
    path_parts = [p.strip() for p in path.split("/") if p.strip()]

    if not path_parts:
        return canvas.get_root_pg_id()

    # Get root process group info
    root_pg_id = canvas.get_root_pg_id()
    root_pg = canvas.get_process_group(root_pg_id, 'id')
    root_pg_name = root_pg.component.name if hasattr(root_pg, 'component') and hasattr(root_pg.component, 'name') else None

    logger.debug(f"  Root PG: '{root_pg_name}' (ID: {root_pg_id})")

    # Check if first part of path matches root PG name
    if root_pg_name and path_parts[0] == root_pg_name:
        logger.debug(f"  ✓ First part '{path_parts[0]}' matches root PG name, skipping it")
        path_parts = path_parts[1:]

        # If only root was specified, return root ID
        if not path_parts:
            logger.debug(f"  Path is just root, returning root ID")
            return root_pg_id

    # Get all process groups
    all_pgs = canvas.list_all_process_groups(root_pg_id)

    # Build a map of PG id -> PG info
    pg_map = {}
    for pg in all_pgs:
        pg_map[pg.id] = {
            "id": pg.id,
            "name": pg.component.name,
            "parent_group_id": pg.component.parent_group_id,
        }

    # Build full paths for each PG
    def build_path_parts(pg_id):
        """Build path parts from root to this PG"""
        parts = []
        current_id = pg_id
        while current_id in pg_map and current_id != root_pg_id:
            pg_info = pg_map[current_id]
            parts.insert(0, pg_info["name"])
            current_id = pg_info["parent_group_id"]
        return parts

    # First, check if the full path already exists
    for pg_id, pg_info in pg_map.items():
        pg_path_parts = build_path_parts(pg_id)
        if pg_path_parts == path_parts:
            logger.info(f"  ✓ Found existing process group at path: /{'/'.join(path_parts)}")
            return pg_id

    # Path doesn't exist - need to create missing process groups
    logger.info(f"  Path '{path}' not found, will create missing process groups...")

    # Find the deepest existing parent
    current_parent_id = root_pg_id
    existing_depth = 0

    for i in range(len(path_parts)):
        partial_path = path_parts[:i+1]
        found = False

        for pg_id, pg_info in pg_map.items():
            pg_path_parts = build_path_parts(pg_id)
            if pg_path_parts == partial_path:
                current_parent_id = pg_id
                existing_depth = i + 1
                found = True
                break

        if not found:
            break

    if existing_depth > 0:
        logger.debug(f"  ✓ Found existing parent at depth {existing_depth}: /{'/'.join(path_parts[:existing_depth])}")
    else:
        logger.debug(f"  Starting from root process group")

    # Create missing process groups
    for i in range(existing_depth, len(path_parts)):
        pg_name = path_parts[i]
        logger.info(f"  Creating process group '{pg_name}' in parent {current_parent_id}...")

        try:
            new_pg = canvas.create_process_group(
                parent_pg=canvas.get_process_group(current_parent_id, 'id'),
                new_pg_name=pg_name,
                location=(0.0, 0.0)
            )
            current_parent_id = new_pg.id
            logger.info(f"  ✓ Created process group '{pg_name}' (ID: {current_parent_id})")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create process group '{pg_name}': {str(e)}"
            )

    logger.info(f"  ✓ Full path created: /{'/'.join(path_parts)}")
    return current_parent_id


@router.post("/{instance_id}/flow", response_model=DeploymentResponse)
async def deploy_flow(
    instance_id: int,
    deployment: DeploymentRequest,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Deploy a flow from registry to a NiFi instance.

    Uses nipyapi.versioning.deploy_flow_version() to handle deployment.
    """
    logger.info("=== DEPLOY FLOW REQUEST ===")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"Template ID: {deployment.template_id}")
    logger.info(f"Parent PG ID: {deployment.parent_process_group_id}")
    logger.info(f"Parent PG Path: {deployment.parent_process_group_path}")
    logger.info(f"Process Group Name: {deployment.process_group_name}")

    # Get the NiFi instance
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    # Validate parent process group requirement
    if not deployment.parent_process_group_id and not deployment.parent_process_group_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either parent_process_group_id or parent_process_group_path is required",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection

        # Configure nipyapi with authentication
        configure_nifi_connection(instance, normalize_url=True)

        if instance.username and instance.password_encrypted:
            logger.info("Successfully configured authentication")

        # Initialize deployment service
        service = NiFiDeploymentService(instance)

        # Step 1: Get registry information (from template or direct parameters)
        bucket_id, flow_id, registry_client_id, template_name = service.get_registry_info(
            deployment, db
        )

        # Step 2: Resolve parent process group (by ID or path)
        parent_pg_id = service.resolve_parent_process_group(
            deployment, find_or_create_process_group_by_path
        )

        logger.info(
            f"Deploying flow to NiFi instance {instance_id} "
            f"({instance.hierarchy_attribute}={instance.hierarchy_value})"
        )

        # Step 3: Get bucket and flow identifiers (handles GitHub registries)
        bucket_identifier, flow_identifier = service.get_bucket_and_flow_identifiers(
            bucket_id, flow_id, registry_client_id
        )

        # Step 4: Determine version to deploy (fetch latest if not specified)
        deploy_version = service.get_deploy_version(
            deployment, registry_client_id, bucket_identifier, flow_identifier
        )

        # Step 5: Pre-deployment check for existing process group
        service.check_existing_process_group(deployment, parent_pg_id)

        # Step 6: Deploy the flow
        deployed_pg = service.deploy_flow_version(
            parent_pg_id, deployment, bucket_identifier,
            flow_identifier, registry_client_id, deploy_version
        )

        pg_id = deployed_pg.id if hasattr(deployed_pg, "id") else None
        logger.info(f"✓ Successfully deployed process group: {pg_id}")

        # Step 7: Rename process group if requested
        pg_name, deployed_version = service.rename_process_group(
            deployed_pg, deployment.process_group_name
        )

        # Step 8: Assign parameter context if specified
        if pg_id and deployment.parameter_context_id:
            logger.info(f"Assigning parameter context {deployment.parameter_context_id} to process group {pg_id}")
            try:
                from nipyapi import parameters

                # Re-fetch the process group to get the latest state after rename
                from nipyapi.nifi import ProcessGroupsApi
                pg_api = ProcessGroupsApi()
                pg = pg_api.get_process_group(id=pg_id)

                parameters.assign_context_to_process_group(
                    pg=pg,
                    context_id=deployment.parameter_context_id,
                    cascade=False,
                )
                logger.info(f"✓ Parameter context assigned successfully")
            except Exception as param_error:
                logger.warning(f"⚠ Warning: Could not assign parameter context: {param_error}")
                # Don't fail the deployment if parameter context assignment fails

        # Step 9: Auto-connect ports if parent PG specified
        # Use parent_pg_id that was resolved (could be from ID or path)
        logger.info(f"DEBUG: Checking auto-connect conditions:")
        logger.info(f"  pg_id exists: {pg_id is not None}")
        logger.info(f"  parent_pg_id resolved: {parent_pg_id}")
        logger.info(f"  deployment.parent_process_group_id: {deployment.parent_process_group_id}")
        logger.info(f"  deployment.parent_process_group_path: {deployment.parent_process_group_path}")

        if pg_id and parent_pg_id:
            logger.info(f"✓ Triggering auto-connect between child={pg_id} and parent={parent_pg_id}")
            service.auto_connect_ports(pg_id, parent_pg_id)
        else:
            logger.warning(f"⚠ Skipping auto-connect: pg_id={pg_id}, parent_pg_id={parent_pg_id}")

        # Build success response
        success_message = (
            f"Flow deployed successfully to "
            f"{instance.hierarchy_attribute}={instance.hierarchy_value}"
        )
        if template_name:
            success_message += f" using template '{template_name}'"

        logger.info(f"  Process Group: {pg_name} (ID: {pg_id})")
        logger.info(f"  Version: {deployed_version}")

        return DeploymentResponse(
            status="success",
            message=success_message,
            process_group_id=pg_id,
            process_group_name=pg_name,
            instance_id=instance_id,
            bucket_id=bucket_identifier,
            flow_id=flow_identifier,
            version=deployed_version or deployment.version,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"✗ Deployment failed: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy flow: {error_msg}",
        )
