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
    PortsResponse,
    PortInfo,
    ConnectionRequest,
    ConnectionResponse,
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
        
        # Step 8: Auto-connect ports if parent PG specified
        if pg_id and deployment.parent_process_group_id:
            service.auto_connect_ports(pg_id, deployment.parent_process_group_id)
        
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
