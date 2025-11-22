"""Flow deployment API endpoints"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance
from app.models.setting import Setting
from app.models.deployment import (
    DeploymentRequest,
    DeploymentResponse,
)
from app.services.nifi_deployment_service import NiFiDeploymentService

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
    root_pg = canvas.get_process_group(root_pg_id, "id")
    root_pg_name = (
        root_pg.component.name
        if hasattr(root_pg, "component") and hasattr(root_pg.component, "name")
        else None
    )

    logger.debug(f"  Root PG: '{root_pg_name}' (ID: {root_pg_id})")

    # Check if first part of path matches root PG name
    if root_pg_name and path_parts[0] == root_pg_name:
        logger.debug(
            f"  ✓ First part '{path_parts[0]}' matches root PG name, skipping it"
        )
        path_parts = path_parts[1:]

        # If only root was specified, return root ID
        if not path_parts:
            logger.debug("  Path is just root, returning root ID")
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
            logger.info(
                f"  ✓ Found existing process group at path: /{'/'.join(path_parts)}"
            )
            return pg_id

    # Path doesn't exist - need to create missing process groups
    logger.info(f"  Path '{path}' not found, will create missing process groups...")

    # Find the deepest existing parent
    current_parent_id = root_pg_id
    existing_depth = 0

    for i in range(len(path_parts)):
        partial_path = path_parts[: i + 1]
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
        logger.debug(
            f"  ✓ Found existing parent at depth {existing_depth}: /{'/'.join(path_parts[:existing_depth])}"
        )
    else:
        logger.debug("  Starting from root process group")

    # Create missing process groups
    for i in range(existing_depth, len(path_parts)):
        pg_name = path_parts[i]
        logger.info(
            f"  Creating process group '{pg_name}' in parent {current_parent_id}..."
        )

        try:
            new_pg = canvas.create_process_group(
                parent_pg=canvas.get_process_group(current_parent_id, "id"),
                new_pg_name=pg_name,
                location=(0.0, 0.0),
            )
            current_parent_id = new_pg.id
            logger.info(
                f"  ✓ Created process group '{pg_name}' (ID: {current_parent_id})"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create process group '{pg_name}': {str(e)}",
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
    logger.info(f"Hierarchy Attribute (from request): {deployment.hierarchy_attribute}")
    logger.info(f"Parameter Context Name: {deployment.parameter_context_name}")
    logger.info(f"Parameter Context ID: {deployment.parameter_context_id}")
    logger.info(
        f"Stop Versioning After Deploy: {deployment.stop_versioning_after_deploy}"
    )
    logger.info(f"Disable After Deploy: {deployment.disable_after_deploy}")
    logger.info(f"Start After Deploy: {deployment.start_after_deploy}")

    # Get the NiFi instance
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    # Validate parent process group requirement
    if (
        not deployment.parent_process_group_id
        and not deployment.parent_process_group_path
    ):
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

        # Fetch hierarchy configuration from settings
        hierarchy_setting = (
            db.query(Setting).filter(Setting.key == "hierarchy_config").first()
        )
        last_hierarchy_attr = "cn"  # Default fallback

        logger.info(f"DEBUG: hierarchy_setting found: {hierarchy_setting is not None}")
        if hierarchy_setting:
            logger.info(
                f"DEBUG: hierarchy_setting.value type: {type(hierarchy_setting.value)}"
            )
            logger.info(
                f"DEBUG: hierarchy_setting.value: {hierarchy_setting.value[:200] if hierarchy_setting.value else 'None'}"
            )

        if hierarchy_setting and hierarchy_setting.value:
            try:
                hierarchy_config = json.loads(hierarchy_setting.value)
                logger.info(
                    f"DEBUG: Parsed hierarchy_config type: {type(hierarchy_config)}"
                )
                logger.info(f"DEBUG: Parsed hierarchy_config: {hierarchy_config}")

                # Handle both formats: direct list or wrapped in {"hierarchy": [...]}
                hierarchy_list = None
                if (
                    isinstance(hierarchy_config, dict)
                    and "hierarchy" in hierarchy_config
                ):
                    hierarchy_list = hierarchy_config["hierarchy"]
                    logger.info("DEBUG: Found 'hierarchy' key in dict, extracted list")
                elif isinstance(hierarchy_config, list):
                    hierarchy_list = hierarchy_config
                    logger.info("DEBUG: hierarchy_config is already a list")

                if (
                    hierarchy_list
                    and isinstance(hierarchy_list, list)
                    and len(hierarchy_list) > 0
                ):
                    logger.info(
                        f"DEBUG: hierarchy_list has {len(hierarchy_list)} items"
                    )
                    # Get the last item's name from the hierarchy
                    last_item = hierarchy_list[-1]
                    logger.info(f"DEBUG: Last item: {last_item}")
                    logger.info(f"DEBUG: Last item type: {type(last_item)}")

                    if isinstance(last_item, dict) and "name" in last_item:
                        last_hierarchy_attr = last_item["name"]
                        logger.info(
                            f"Using hierarchy attribute from config: '{last_hierarchy_attr}'"
                        )
                    else:
                        logger.warning(
                            "Invalid hierarchy config format, using default: 'cn'"
                        )
                        logger.warning(
                            "DEBUG: Last item doesn't have 'name' key or isn't a dict"
                        )
                else:
                    logger.warning("Empty hierarchy config, using default: 'cn'")
                    logger.warning("DEBUG: hierarchy_list is empty or invalid")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(
                    f"Failed to parse hierarchy config: {e}, using default: 'cn'"
                )
                logger.error(f"DEBUG: Exception details: {type(e).__name__}: {str(e)}")
        else:
            logger.info("No hierarchy config found, using default: 'cn'")

        # Use hierarchy_attribute from request if provided, otherwise use the last from config
        hierarchy_attr_to_use = deployment.hierarchy_attribute or last_hierarchy_attr
        logger.info(
            f"Using hierarchy attribute: '{hierarchy_attr_to_use}' (from {'request' if deployment.hierarchy_attribute else 'config'})"
        )

        # Initialize deployment service with hierarchy info
        service = NiFiDeploymentService(instance, hierarchy_attr_to_use)

        # Step 1: Get registry information (from template or direct parameters)
        bucket_id, flow_id, registry_client_id, template_name = (
            service.get_registry_info(deployment, db)
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
            parent_pg_id,
            deployment,
            bucket_identifier,
            flow_identifier,
            registry_client_id,
            deploy_version,
        )

        pg_id = deployed_pg.id if hasattr(deployed_pg, "id") else None
        logger.info(f"✓ Successfully deployed process group: {pg_id}")

        # Step 7: Rename process group if requested
        # Note: rename_process_group returns (pg_id, pg_name)
        _, pg_name = service.rename_process_group(
            deployed_pg, deployment.process_group_name
        )

        # Extract deployed version
        deployed_version = service.extract_deployed_version(deployed_pg)

        # Step 8: Assign parameter context if specified
        # Priority: parameter_context_name (lookup by name) > parameter_context_id (direct ID)
        if pg_id and deployment.parameter_context_name:
            logger.info(
                f"Assigning parameter context by name: '{deployment.parameter_context_name}'"
            )
            service.assign_parameter_context(pg_id, deployment.parameter_context_name)
        elif pg_id and deployment.parameter_context_id:
            logger.info(
                f"Assigning parameter context by ID: {deployment.parameter_context_id}"
            )
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
                logger.info("✓ Parameter context assigned successfully")
            except Exception as param_error:
                logger.warning(
                    f"⚠ Warning: Could not assign parameter context: {param_error}"
                )
                # Don't fail the deployment if parameter context assignment fails

        # Step 9: Auto-connect ports if parent PG specified
        # Use parent_pg_id that was resolved (could be from ID or path)
        logger.info("DEBUG: Checking auto-connect conditions:")
        logger.info(f"  pg_id exists: {pg_id is not None}")
        logger.info(f"  parent_pg_id resolved: {parent_pg_id}")
        logger.info(
            f"  deployment.parent_process_group_id: {deployment.parent_process_group_id}"
        )
        logger.info(
            f"  deployment.parent_process_group_path: {deployment.parent_process_group_path}"
        )

        if pg_id and parent_pg_id:
            logger.info(
                f"✓ Triggering auto-connect between child={pg_id} and parent={parent_pg_id}"
            )
            service.auto_connect_ports(pg_id, parent_pg_id)
        else:
            logger.warning(
                f"⚠ Skipping auto-connect: pg_id={pg_id}, parent_pg_id={parent_pg_id}"
            )

        # Step 10: Stop version control if requested
        if pg_id and deployment.stop_versioning_after_deploy:
            logger.info(
                "Stopping version control after deployment (stop_versioning_after_deploy=True)"
            )
            service.stop_version_control(pg_id)

        # Step 11: Disable the process group if requested
        if pg_id and deployment.disable_after_deploy:
            logger.info(
                "Disabling process group after deployment (disable_after_deploy=True)"
            )
            logger.info(
                "Note: NiFi deploys flows in STOPPED state by default. This will DISABLE (lock) them."
            )
            try:
                # Disable all components in the process group (sets to DISABLED state)
                # DISABLED = locked, cannot be started (prevents accidental starting)
                # Note: NiFi already deploys in STOPPED state, this goes further to DISABLE
                service.stop_process_group(pg_id)
                logger.info(
                    "✓ Process group disabled successfully (locked - cannot be started)"
                )
            except Exception as e:
                logger.warning(f"Failed to disable process group after deployment: {e}")

        # Step 12: Start the process group if requested
        if pg_id and deployment.start_after_deploy:
            logger.info(
                "Starting process group after deployment (start_after_deploy=True)"
            )
            logger.info(
                "Note: NiFi deploys flows in STOPPED state by default. This will START them."
            )
            try:
                # Start the process group (sets to RUNNING state)
                service.start_process_group(pg_id)
                logger.info("✓ Process group started successfully")
            except Exception as e:
                logger.warning(f"Failed to start process group after deployment: {e}")

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
