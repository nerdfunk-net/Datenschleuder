"""Flow deployment API endpoints"""

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

router = APIRouter()


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
    
    print(f"  Root PG: '{root_pg_name}' (ID: {root_pg_id})")
    
    # Check if first part of path matches root PG name
    if root_pg_name and path_parts[0] == root_pg_name:
        print(f"  ✓ First part '{path_parts[0]}' matches root PG name, skipping it")
        path_parts = path_parts[1:]
        
        # If only root was specified, return root ID
        if not path_parts:
            print(f"  Path is just root, returning root ID")
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
            print(f"  ✓ Found existing process group at path: /{'/'.join(path_parts)}")
            return pg_id
    
    # Path doesn't exist - need to create missing process groups
    print(f"  Path '{path}' not found, will create missing process groups...")
    
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
        print(f"  ✓ Found existing parent at depth {existing_depth}: /{'/'.join(path_parts[:existing_depth])}")
    else:
        print(f"  Starting from root process group")
    
    # Create missing process groups
    for i in range(existing_depth, len(path_parts)):
        pg_name = path_parts[i]
        print(f"  Creating process group '{pg_name}' in parent {current_parent_id}...")
        
        try:
            new_pg = canvas.create_process_group(
                parent_pg=canvas.get_process_group(current_parent_id, 'id'),
                new_pg_name=pg_name,
                location=(0.0, 0.0)
            )
            current_parent_id = new_pg.id
            print(f"  ✓ Created process group '{pg_name}' (ID: {current_parent_id})")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create process group '{pg_name}': {str(e)}"
            )
    
    print(f"  ✓ Full path created: /{'/'.join(path_parts)}")
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
    print(f"=== DEPLOY FLOW REQUEST ===")
    print(f"Instance ID: {instance_id}")
    print(f"Template ID: {deployment.template_id}")
    print(f"Parent PG ID: {deployment.parent_process_group_id}")
    print(f"Parent PG Path: {deployment.parent_process_group_path}")
    print(f"Process Group Name: {deployment.process_group_name}")
    
    # Get the NiFi instance
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    # Determine registry information from template or direct parameters
    if deployment.template_id:
        template = (
            db.query(RegistryFlow)
            .filter(RegistryFlow.id == deployment.template_id)
            .first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {deployment.template_id} not found",
            )

        bucket_id = template.bucket_id
        flow_id = template.flow_id
        registry_client_id = template.registry_id
        template_name = template.flow_name

        print(f"Using template '{template_name}' (ID: {deployment.template_id})")
        print(f"  Registry: {template.registry_name} ({registry_client_id})")
        print(f"  Bucket: {template.bucket_name} ({bucket_id})")
        print(f"  Flow: {template.flow_name} ({flow_id})")
    else:
        if (
            not deployment.bucket_id
            or not deployment.flow_id
            or not deployment.registry_client_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either template_id or (bucket_id, flow_id, registry_client_id) must be provided",
            )

        bucket_id = deployment.bucket_id
        flow_id = deployment.flow_id
        registry_client_id = deployment.registry_client_id
        template_name = None

    # Validate and resolve parent process group
    if not deployment.parent_process_group_id and not deployment.parent_process_group_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either parent_process_group_id or parent_process_group_path is required",
        )

    try:
        from app.services.nifi_auth import configure_nifi_connection
        from nipyapi import versioning, canvas

        # Configure nipyapi with authentication
        configure_nifi_connection(instance, normalize_url=True)

        # Check if we got an access token (only when using username/password)
        if instance.username and instance.password_encrypted:
            print("Successfully configured authentication")

        # Resolve parent process group ID
        if deployment.parent_process_group_id:
            parent_pg_id = deployment.parent_process_group_id
            print(f"Using provided parent_process_group_id: {parent_pg_id}")
        else:
            print(f"Resolving path: '{deployment.parent_process_group_path}'")
            try:
                # Find or create the process group path
                parent_pg_id = find_or_create_process_group_by_path(
                    deployment.parent_process_group_path or ""
                )
                print(f"✓ Resolved to parent_pg_id: {parent_pg_id}")
            except HTTPException as e:
                print(f"✗ ERROR: Failed to resolve/create path '{deployment.parent_process_group_path}'")
                print(f"  Error: {e.detail}")
                print(f"  Status Code: {e.status_code}")
                raise
            except Exception as e:
                print(f"✗ UNEXPECTED ERROR during path resolution: {e}")
                import traceback
                traceback.print_exc()
                raise

        print(
            f"Deploying flow to NiFi instance {instance_id} ({instance.hierarchy_attribute}={instance.hierarchy_value})"
        )

        # Get registry client
        reg_client = versioning.get_registry_client(registry_client_id, "id")
        reg_client_name = (
            reg_client.component.name
            if hasattr(reg_client, "component")
            else registry_client_id
        )
        print(f"  Registry Client: {reg_client_name}")

        # Get bucket and flow identifiers
        # Skip lookup for GitHub registries (they don't support bucket/flow lookup API)
        is_github_registry = (
            "github" in reg_client_name.lower() if reg_client_name else False
        )

        if is_github_registry:
            print("GitHub registry detected, using provided bucket/flow IDs directly")
            bucket_identifier = bucket_id
            flow_identifier = flow_id
        else:
            print("Getting bucket and flow identifiers from NiFi Registry...")
            try:
                bucket = versioning.get_registry_bucket(bucket_id)
                print(f"  Bucket: {bucket.name} ({bucket.identifier})")

                flow = versioning.get_flow_in_bucket(
                    bucket.identifier, identifier=flow_id
                )
                print(f"  Flow: {flow.name} ({flow.identifier})")

                bucket_identifier = bucket.identifier
                flow_identifier = flow.identifier
            except Exception as lookup_error:
                print(
                    f"  Could not lookup bucket/flow, using provided values: {lookup_error}"
                )
                bucket_identifier = bucket_id
                flow_identifier = flow_id

        # Determine version to deploy
        # For GitHub registries: need actual commit hash (last in list = latest)
        # For NiFi Registry: can use integer version number
        deploy_version = deployment.version

        if deploy_version is None:
            # Fetch available versions to get the latest
            print("Fetching latest version for flow...")
            try:
                # Use NiFi's FlowApi to get versions (works with GitHub registries)
                from nipyapi.nifi import FlowApi

                flow_api = FlowApi()

                versions = flow_api.get_versions(
                    registry_id=reg_client.id,
                    bucket_id=bucket_identifier,
                    flow_id=flow_identifier,
                )

                # VersionedFlowSnapshotMetadataSetEntity has 'versioned_flow_snapshot_metadata_set'
                if versions and hasattr(
                    versions, "versioned_flow_snapshot_metadata_set"
                ):
                    metadata_set = versions.versioned_flow_snapshot_metadata_set
                    if metadata_set and len(metadata_set) > 0:
                        # Last version in the set is the latest (newest commit)
                        last_version_entity = metadata_set[-1]
                        # The version info is nested inside versioned_flow_snapshot_metadata
                        snapshot_metadata = (
                            last_version_entity.versioned_flow_snapshot_metadata
                        )
                        # Get the version (commit hash for GitHub registries, int for NiFi Registry)
                        deploy_version = snapshot_metadata.version
                        print(f"  Latest version: {deploy_version}")
                    else:
                        raise ValueError("No versions found for this flow")
                else:
                    raise ValueError("No versions found for this flow")
            except Exception as e:
                print(f"  Warning: Could not fetch versions: {e}")
                print("  Falling back to version=None")
                deploy_version = None

        # Pre-deployment check: Check if process group with same name already exists
        if deployment.process_group_name:
            print(
                f"Checking if process group '{deployment.process_group_name}' already exists in parent..."
            )

            from nipyapi.nifi import ProcessGroupsApi

            pg_api = ProcessGroupsApi()

            try:
                parent_pg_response = pg_api.get_process_groups(
                    id=deployment.parent_process_group_id
                )

                existing_pg = None
                if hasattr(parent_pg_response, "process_groups"):
                    for pg in parent_pg_response.process_groups:
                        if hasattr(pg, "component") and hasattr(pg.component, "name"):
                            if pg.component.name == deployment.process_group_name:
                                existing_pg = pg
                                break

                if existing_pg:
                    print(
                        f"  ⚠ Process group '{deployment.process_group_name}' already exists (ID: {existing_pg.id})"
                    )

                    # Check if there's version control information
                    has_version_control = False
                    if hasattr(existing_pg, "component") and hasattr(
                        existing_pg.component, "version_control_information"
                    ):
                        vci = existing_pg.component.version_control_information
                        if vci:
                            has_version_control = True

                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": f"Process group '{deployment.process_group_name}' already exists",
                            "existing_process_group": {
                                "id": existing_pg.id,
                                "name": existing_pg.component.name
                                if hasattr(existing_pg, "component")
                                else None,
                                "has_version_control": has_version_control,
                                "running_count": existing_pg.running_count
                                if hasattr(existing_pg, "running_count")
                                else 0,
                                "stopped_count": existing_pg.stopped_count
                                if hasattr(existing_pg, "stopped_count")
                                else 0,
                            },
                        },
                    )
                else:
                    print(
                        f"  ✓ No existing process group found with name '{deployment.process_group_name}'"
                    )

            except HTTPException:
                raise
            except Exception as check_error:
                print(
                    f"  Warning: Could not check for existing process group: {check_error}"
                )
                # Continue with deployment if check fails

        # Deploy using nipyapi.versioning.deploy_flow_version
        print("Deploying flow using nipyapi.versioning.deploy_flow_version:")
        print(f"  Parent PG: {parent_pg_id}")
        print(f"  Bucket ID: {bucket_identifier}")
        print(f"  Flow ID: {flow_identifier}")
        print(f"  Registry Client ID: {reg_client.id}")
        print(f"  Version: {deploy_version}")
        print(f"  Position: ({deployment.x_position}, {deployment.y_position})")

        deployed_pg = versioning.deploy_flow_version(
            parent_id=parent_pg_id,
            location=(float(deployment.x_position), float(deployment.y_position)),
            bucket_id=bucket_identifier,
            flow_id=flow_identifier,
            reg_client_id=reg_client.id,
            version=deploy_version,
        )

        print(f"✓ Successfully deployed process group: {deployed_pg.id}")

        # Extract process group information
        pg_id = deployed_pg.id if hasattr(deployed_pg, "id") else None
        pg_name = (
            deployed_pg.component.name
            if hasattr(deployed_pg, "component")
            and hasattr(deployed_pg.component, "name")
            else None
        )
        deployed_version = None

        if hasattr(deployed_pg, "component") and hasattr(
            deployed_pg.component, "version_control_information"
        ):
            vci = deployed_pg.component.version_control_information
            if vci and hasattr(vci, "version"):
                deployed_version = vci.version

        # Rename process group if requested
        if deployment.process_group_name and pg_id:
            try:
                print(
                    f"Renaming process group from '{pg_name}' to '{deployment.process_group_name}'..."
                )

                # Use nipyapi.canvas.update_process_group to rename
                # The update parameter should be a dictionary with key:value pairs
                updated_pg = canvas.update_process_group(
                    pg=deployed_pg, update={"name": deployment.process_group_name}
                )

                pg_name = updated_pg.component.name
                print(f"✓ Successfully renamed process group to '{pg_name}'")

            except Exception as rename_error:
                print(f"⚠ Warning: Could not rename process group: {rename_error}")
                # Continue anyway, renaming is not critical

        # Auto-connect ports if they exist
        if pg_id and deployment.parent_process_group_id:
            from nipyapi.nifi import ProcessGroupsApi

            pg_api = ProcessGroupsApi()

            # Connect output ports
            try:
                print("Checking for output ports to auto-connect...")

                # Get output ports of the newly deployed process group
                child_output_response = pg_api.get_output_ports(id=pg_id)
                child_output_ports = (
                    child_output_response.output_ports
                    if hasattr(child_output_response, "output_ports")
                    else []
                )

                if child_output_ports:
                    print(
                        f"  Found {len(child_output_ports)} output port(s) in deployed process group"
                    )

                    # Get output ports of the parent process group
                    parent_output_response = pg_api.get_output_ports(
                        id=deployment.parent_process_group_id
                    )
                    parent_output_ports = (
                        parent_output_response.output_ports
                        if hasattr(parent_output_response, "output_ports")
                        else []
                    )

                    if parent_output_ports:
                        print(
                            f"  Found {len(parent_output_ports)} output port(s) in parent process group"
                        )

                        # Connect the first output port of child to first output port of parent
                        child_port = child_output_ports[0]
                        parent_port = parent_output_ports[0]

                        print(
                            f"  Connecting output: '{child_port.component.name}' -> '{parent_port.component.name}'..."
                        )

                        # Use nipyapi.canvas.create_connection which handles the details correctly
                        created_conn = canvas.create_connection(
                            source=child_port,
                            target=parent_port,
                            name=f"{child_port.component.name} to {parent_port.component.name}",
                        )

                        print(
                            f"  ✓ Successfully created output connection (ID: {created_conn.id})"
                        )
                    else:
                        print(
                            "  No output ports found in parent process group - skipping output auto-connect"
                        )
                else:
                    print(
                        "  No output ports found in deployed process group - skipping output auto-connect"
                    )

            except Exception as connect_error:
                print(
                    f"⚠ Warning: Could not auto-connect output ports: {connect_error}"
                )
                # Continue anyway, auto-connection is not critical

            # Connect input ports
            try:
                print("Checking for input ports to auto-connect...")

                # Get input ports of the newly deployed process group
                child_input_response = pg_api.get_input_ports(id=pg_id)
                child_input_ports = (
                    child_input_response.input_ports
                    if hasattr(child_input_response, "input_ports")
                    else []
                )

                if child_input_ports:
                    print(
                        f"  Found {len(child_input_ports)} input port(s) in deployed process group"
                    )

                    # Get input ports of the parent process group
                    parent_input_response = pg_api.get_input_ports(
                        id=deployment.parent_process_group_id
                    )
                    parent_input_ports = (
                        parent_input_response.input_ports
                        if hasattr(parent_input_response, "input_ports")
                        else []
                    )

                    if parent_input_ports:
                        print(
                            f"  Found {len(parent_input_ports)} input port(s) in parent process group"
                        )

                        # Connect the first input port of parent to first input port of child
                        parent_port = parent_input_ports[0]
                        child_port = child_input_ports[0]

                        print(
                            f"  Connecting input: '{parent_port.component.name}' -> '{child_port.component.name}'..."
                        )

                        # Use nipyapi.canvas.create_connection which handles the details correctly
                        created_conn = canvas.create_connection(
                            source=parent_port,
                            target=child_port,
                            name=f"{parent_port.component.name} to {child_port.component.name}",
                        )

                        print(
                            f"  ✓ Successfully created input connection (ID: {created_conn.id})"
                        )
                    else:
                        print(
                            "  No input ports found in parent process group - skipping input auto-connect"
                        )
                else:
                    print(
                        "  No input ports found in deployed process group - skipping input auto-connect"
                    )

            except Exception as connect_error:
                print(f"⚠ Warning: Could not auto-connect input ports: {connect_error}")
                # Continue anyway, auto-connection is not critical

        success_message = f"Flow deployed successfully to {instance.hierarchy_attribute}={instance.hierarchy_value}"
        if template_name:
            success_message += f" using template '{template_name}'"

        print(f"  Process Group: {pg_name} (ID: {pg_id})")
        print(f"  Version: {deployed_version}")

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
        print(f"✗ Deployment failed: {error_msg}")
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
):
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
            print(f"Searching for process group with ID: {id} (greedy={greedy})")
            process_group_result = canvas.get_process_group(
                identifier=id, identifier_type="id", greedy=greedy
            )
        elif name:
            print(f"Searching for process group with name: {name} (greedy={greedy})")
            process_group_result = canvas.get_process_group(
                identifier=name, identifier_type="name", greedy=greedy
            )

        if process_group_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group not found with {'ID' if id else 'name'}: {id or name}",
            )

        # Helper function to extract process group info
        def extract_pg_info(pg):
            return {
                "id": pg.id if hasattr(pg, "id") else None,
                "name": pg.component.name
                if hasattr(pg, "component") and hasattr(pg.component, "name")
                else None,
                "parent_group_id": pg.component.parent_group_id
                if hasattr(pg, "component") and hasattr(pg.component, "parent_group_id")
                else None,
                "comments": pg.component.comments
                if hasattr(pg, "component") and hasattr(pg.component, "comments")
                else None,
                "running_count": pg.running_count
                if hasattr(pg, "running_count")
                else 0,
                "stopped_count": pg.stopped_count
                if hasattr(pg, "stopped_count")
                else 0,
                "invalid_count": pg.invalid_count
                if hasattr(pg, "invalid_count")
                else 0,
            }

        # Handle different return types
        if isinstance(process_group_result, list):
            if len(process_group_result) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group not found with {'ID' if id else 'name'}: {id or name}",
                )

            # Multiple matches - return as list
            pg_list = [extract_pg_info(pg) for pg in process_group_result]
            print(f"Found {len(pg_list)} process groups")

            return {
                "status": "success",
                "process_groups": pg_list,
                "count": len(pg_list),
            }
        else:
            # Single match
            pg_info = extract_pg_info(process_group_result)
            print(f"Found process group: {pg_info['name']} (ID: {pg_info['id']})")

            return {
                "status": "success",
                "process_group": pg_info,
            }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get process group: {error_msg}")
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
):
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
            print(
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
            print(f"Listing all child process groups of parent '{parent_id}'")

            from nipyapi.nifi import ProcessGroupsApi

            pg_api = ProcessGroupsApi()
            parent_pg_response = pg_api.get_process_groups(id=parent_id)

            if hasattr(parent_pg_response, "process_groups"):
                process_groups = parent_pg_response.process_groups
        elif name:
            # Search for process groups by name (globally)
            print(f"Searching for process groups with name: {name}")
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
            print("Listing all process groups")
            process_groups = canvas.list_all_process_groups()

        # Format the response
        pg_list = []
        for pg in process_groups:
            pg_info = {
                "id": pg.id if hasattr(pg, "id") else None,
                "name": pg.component.name
                if hasattr(pg, "component") and hasattr(pg.component, "name")
                else None,
                "parent_group_id": pg.component.parent_group_id
                if hasattr(pg, "component") and hasattr(pg.component, "parent_group_id")
                else None,
                "comments": pg.component.comments
                if hasattr(pg, "component") and hasattr(pg.component, "comments")
                else None,
                "running_count": pg.running_count
                if hasattr(pg, "running_count")
                else 0,
                "stopped_count": pg.stopped_count
                if hasattr(pg, "stopped_count")
                else 0,
                "invalid_count": pg.invalid_count
                if hasattr(pg, "invalid_count")
                else 0,
            }
            pg_list.append(pg_info)

        print(f"Found {len(pg_list)} process groups")

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
        print(f"Failed to search process groups: {error_msg}")
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
):
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
        print(f"Root process group ID: {root_pg_id}")

        # Build path from process_group_id to root
        path = []
        current_pg_id = process_group_id
        visited_ids = set()  # Prevent infinite loops

        print(f"Building path from process group ID: {process_group_id}")

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
            pg_info = {
                "id": current_pg.id if hasattr(current_pg, "id") else None,
                "name": current_pg.component.name
                if hasattr(current_pg, "component")
                and hasattr(current_pg.component, "name")
                else None,
                "parent_group_id": current_pg.component.parent_group_id
                if hasattr(current_pg, "component")
                and hasattr(current_pg.component, "parent_group_id")
                else None,
            }

            path.append(pg_info)
            print(
                f"Added to path: {pg_info['name']} (ID: {pg_info['id']}, Parent: {pg_info['parent_group_id']})"
            )

            # Check if we've reached the root
            if current_pg_id == root_pg_id:
                print("Reached root process group")
                break

            # Move to parent
            parent_id = pg_info["parent_group_id"]
            if not parent_id:
                # No parent means we're at root
                print("No parent ID - reached root")
                break

            current_pg_id = parent_id

        print(f"Path built successfully with {len(path)} levels")

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
        print(f"Failed to get process group path: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group path: {error_msg}",
        )


@router.get("/{instance_id}/get-all-paths")
async def get_all_process_group_paths(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
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
        print(f"Root process group ID: {root_pg_id}")

        # Get all process groups using nipyapi's recursive function
        print("Fetching all process groups...")
        all_process_groups = canvas.list_all_process_groups(pg_id=root_pg_id)
        print(f"Found {len(all_process_groups)} process groups")

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

        print(f"Built paths for {len(result)} process groups")

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
        print(f"Failed to get all process group paths: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all process group paths: {error_msg}",
        )


@router.get("/{instance_id}/get-root")
async def get_root_process_group(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
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
        print(f"Root process group ID: {root_pg_id}")

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
        print(f"Failed to get root process group: {error_msg}")
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
        print(f"Getting output ports for process group {process_group_id} ({pg_name})")
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

        print(f"Found {len(ports)} output ports")
        for port in ports:
            print(f"  - {port.name} (ID: {port.id}, State: {port.state})")

        return PortsResponse(
            process_group_id=process_group_id, process_group_name=pg_name, ports=ports
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get output ports: {error_msg}")
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

        print("Creating connection:")
        print(
            f"  Source: {source_name} ({source_type}, ID: {connection_request.source_id})"
        )
        print(
            f"  Target: {target_name} ({target_type}, ID: {connection_request.target_id})"
        )

        # Create connection
        connection = canvas.create_connection(
            source=source,
            target=target,
            relationships=connection_request.relationships,
            name=connection_request.name,
        )

        print(f"✓ Connection created: {connection.id}")

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
        print(f"Failed to create connection: {error_msg}")
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
):
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

        print(f"Deleting process group {process_group_id}...")

        # Get the process group first
        from nipyapi.nifi import ProcessGroupsApi

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        # Delete the process group
        canvas.delete_process_group(pg, force=True, refresh=True)

        print("✓ Process group deleted successfully")

        return {
            "status": "success",
            "message": "Process group deleted successfully",
            "process_group_id": process_group_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to delete process group: {error_msg}")
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
):
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

        print(f"Updating process group {process_group_id} to new version...")

        # Get the process group
        from nipyapi.nifi import ProcessGroupsApi

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        # Update to latest version
        target_version = version_request.get("version")  # None = latest
        versioning.update_flow_version(process_group=pg, target_version=target_version)

        print("✓ Process group updated successfully")

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
        print(f"Failed to update process group version: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update process group version: {error_msg}",
        )
