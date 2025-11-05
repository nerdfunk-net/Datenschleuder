"""NiFi process group management API endpoints"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.deployment import (
    PortsResponse,
    PortInfo,
    ConnectionRequest,
    ConnectionResponse,
    ProcessorInfo,
    ProcessorsResponse,
    InputPortInfo,
    InputPortsResponse,
)
from app.models.parameter_context import (
    AssignParameterContextRequest,
    AssignParameterContextResponse,
)
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection, extract_pg_info
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


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

    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance, normalize_url=True)

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
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas

        # Configure nipyapi with authentication
        setup_nifi_connection(instance, normalize_url=True)

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


@router.post("/{instance_id}/process-group/{process_group_id}/start")
async def start_process_group(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Start all components in a process group.

    This sets all processors, input ports, and output ports to RUNNING state.
    This recursively starts all components within the process group and its child process groups.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas
        from nipyapi.nifi import (
            ProcessorsApi, ProcessorRunStatusEntity, RevisionDTO,
            InputPortsApi, OutputPortsApi, PortRunStatusEntity
        )

        # Configure nipyapi connection with proper SSL handling
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Starting process group {process_group_id}...")

        # Verify the process group exists first
        pg = canvas.get_process_group(process_group_id, 'id')

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group {process_group_id} not found"
            )

        # Get all processors in the process group (recursively)
        processors = canvas.list_all_processors(process_group_id)
        logger.info(f"Found {len(processors)} processor(s) to start")

        processors_api = ProcessorsApi()
        started_processors = 0

        for processor in processors:
            try:
                processor_id = processor.id
                current_revision = processor.revision

                run_status = ProcessorRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="RUNNING"
                )

                processors_api.update_run_status4(body=run_status, id=processor_id)
                started_processors += 1
                logger.debug(f"  Started processor: {processor.component.name} ({processor_id})")

            except Exception as e:
                logger.warning(f"  Failed to start processor {processor_id}: {e}")

        # Get all input ports in the process group (recursively)
        input_ports = canvas.list_all_input_ports(process_group_id)
        logger.info(f"Found {len(input_ports)} input port(s) to start")

        input_ports_api = InputPortsApi()
        started_input_ports = 0

        for port in input_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="RUNNING"
                )

                input_ports_api.update_run_status2(body=run_status, id=port_id)
                started_input_ports += 1
                logger.debug(f"  Started input port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to start input port {port_id}: {e}")

        # Get all output ports in the process group (recursively)
        output_ports = canvas.list_all_output_ports(process_group_id)
        logger.info(f"Found {len(output_ports)} output port(s) to start")

        output_ports_api = OutputPortsApi()
        started_output_ports = 0

        for port in output_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="RUNNING"
                )

                output_ports_api.update_run_status3(body=run_status, id=port_id)
                started_output_ports += 1
                logger.debug(f"  Started output port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to start output port {port_id}: {e}")

        total_started = started_processors + started_input_ports + started_output_ports
        logger.info(f"✓ Started {started_processors} processor(s), {started_input_ports} input port(s), {started_output_ports} output port(s)")

        return {
            "status": "success",
            "message": f"Process group started successfully ({total_started} components)",
            "process_group_id": process_group_id,
            "started_count": {
                "processors": started_processors,
                "input_ports": started_input_ports,
                "output_ports": started_output_ports,
                "total": total_started
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to start process group: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start process group: {error_msg}",
        )


@router.post("/{instance_id}/process-group/{process_group_id}/stop")
async def stop_process_group(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stop all components in a process group.

    This sets all processors, input ports, and output ports to STOPPED state.
    This recursively stops all components within the process group and its child process groups.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas
        from nipyapi.nifi import (
            ProcessorsApi, ProcessorRunStatusEntity, RevisionDTO,
            InputPortsApi, OutputPortsApi, PortRunStatusEntity
        )

        # Configure nipyapi connection with proper SSL handling
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Stopping process group {process_group_id}...")

        # Verify the process group exists first
        pg = canvas.get_process_group(process_group_id, 'id')

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group {process_group_id} not found"
            )

        # Get all processors in the process group (recursively)
        processors = canvas.list_all_processors(process_group_id)
        logger.info(f"Found {len(processors)} processor(s) to stop")

        processors_api = ProcessorsApi()
        stopped_processors = 0

        for processor in processors:
            try:
                processor_id = processor.id
                current_revision = processor.revision

                run_status = ProcessorRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                processors_api.update_run_status4(body=run_status, id=processor_id)
                stopped_processors += 1
                logger.debug(f"  Stopped processor: {processor.component.name} ({processor_id})")

            except Exception as e:
                logger.warning(f"  Failed to stop processor {processor_id}: {e}")

        # Get all input ports in the process group (recursively)
        input_ports = canvas.list_all_input_ports(process_group_id)
        logger.info(f"Found {len(input_ports)} input port(s) to stop")

        input_ports_api = InputPortsApi()
        stopped_input_ports = 0

        for port in input_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                input_ports_api.update_run_status2(body=run_status, id=port_id)
                stopped_input_ports += 1
                logger.debug(f"  Stopped input port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to stop input port {port_id}: {e}")

        # Get all output ports in the process group (recursively)
        output_ports = canvas.list_all_output_ports(process_group_id)
        logger.info(f"Found {len(output_ports)} output port(s) to stop")

        output_ports_api = OutputPortsApi()
        stopped_output_ports = 0

        for port in output_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                output_ports_api.update_run_status3(body=run_status, id=port_id)
                stopped_output_ports += 1
                logger.debug(f"  Stopped output port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to stop output port {port_id}: {e}")

        total_stopped = stopped_processors + stopped_input_ports + stopped_output_ports
        logger.info(f"✓ Stopped {stopped_processors} processor(s), {stopped_input_ports} input port(s), {stopped_output_ports} output port(s)")

        return {
            "status": "success",
            "message": f"Process group stopped successfully ({total_stopped} components)",
            "process_group_id": process_group_id,
            "stopped_count": {
                "processors": stopped_processors,
                "input_ports": stopped_input_ports,
                "output_ports": stopped_output_ports,
                "total": total_stopped
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to stop process group: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop process group: {error_msg}",
        )


@router.post("/{instance_id}/process-group/{process_group_id}/enable")
async def enable_process_group(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Enable (start) all components in a process group.

    This recursively starts all processors, input ports, and output ports
    within the process group and its child process groups.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas
        from nipyapi.nifi import (
            ProcessorsApi, ProcessorRunStatusEntity, RevisionDTO,
            InputPortsApi, OutputPortsApi, PortRunStatusEntity
        )

        # Configure nipyapi connection with proper SSL handling
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Enabling process group {process_group_id}...")

        # Verify the process group exists first
        pg = canvas.get_process_group(process_group_id, 'id')

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group {process_group_id} not found"
            )

        # Get all processors in the process group (recursively)
        processors = canvas.list_all_processors(process_group_id)
        logger.info(f"Found {len(processors)} processor(s) to enable")

        processors_api = ProcessorsApi()
        enabled_processors = 0

        for processor in processors:
            try:
                processor_id = processor.id
                current_revision = processor.revision

                run_status = ProcessorRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                processors_api.update_run_status4(body=run_status, id=processor_id)
                enabled_processors += 1
                logger.debug(f"  Enabled processor: {processor.component.name} ({processor_id})")

            except Exception as e:
                logger.warning(f"  Failed to enable processor {processor_id}: {e}")

        # Get all input ports in the process group (recursively)
        input_ports = canvas.list_all_input_ports(process_group_id)
        logger.info(f"Found {len(input_ports)} input port(s) to enable")

        input_ports_api = InputPortsApi()
        enabled_input_ports = 0

        for port in input_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                input_ports_api.update_run_status2(body=run_status, id=port_id)
                enabled_input_ports += 1
                logger.debug(f"  Enabled input port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to enable input port {port_id}: {e}")

        # Get all output ports in the process group (recursively)
        output_ports = canvas.list_all_output_ports(process_group_id)
        logger.info(f"Found {len(output_ports)} output port(s) to enable")

        output_ports_api = OutputPortsApi()
        enabled_output_ports = 0

        for port in output_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                output_ports_api.update_run_status3(body=run_status, id=port_id)
                enabled_output_ports += 1
                logger.debug(f"  Enabled output port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to enable output port {port_id}: {e}")

        total_enabled = enabled_processors + enabled_input_ports + enabled_output_ports
        logger.info(f"✓ Enabled {enabled_processors} processor(s), {enabled_input_ports} input port(s), {enabled_output_ports} output port(s)")

        return {
            "status": "success",
            "message": f"Process group enabled successfully ({total_enabled} components)",
            "process_group_id": process_group_id,
            "enabled_count": {
                "processors": enabled_processors,
                "input_ports": enabled_input_ports,
                "output_ports": enabled_output_ports,
                "total": total_enabled
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to enable process group: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable process group: {error_msg}",
        )


@router.post("/{instance_id}/process-group/{process_group_id}/disable")
async def disable_process_group(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Disable all processors in a process group.

    This sets all processors to DISABLED state, which prevents them from being started.
    This recursively disables all processors within the process group and its child process groups.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi import canvas
        from nipyapi.nifi import (
            ProcessorsApi, ProcessorRunStatusEntity, RevisionDTO,
            InputPortsApi, OutputPortsApi, PortRunStatusEntity
        )

        # Configure nipyapi connection with proper SSL handling
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Disabling process group {process_group_id}...")

        # Verify the process group exists first
        pg = canvas.get_process_group(process_group_id, 'id')

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group {process_group_id} not found"
            )

        # Get all processors in the process group (recursively)
        processors = canvas.list_all_processors(process_group_id)
        logger.info(f"Found {len(processors)} processor(s) to disable")

        processors_api = ProcessorsApi()
        disabled_processors = 0

        for processor in processors:
            try:
                processor_id = processor.id
                current_revision = processor.revision

                run_status = ProcessorRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="DISABLED"
                )

                processors_api.update_run_status4(body=run_status, id=processor_id)
                disabled_processors += 1
                logger.debug(f"  Disabled processor: {processor.component.name} ({processor_id})")

            except Exception as e:
                logger.warning(f"  Failed to disable processor {processor_id}: {e}")

        # Get all input ports in the process group (recursively)
        input_ports = canvas.list_all_input_ports(process_group_id)
        logger.info(f"Found {len(input_ports)} input port(s) to disable")

        input_ports_api = InputPortsApi()
        disabled_input_ports = 0

        for port in input_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="DISABLED"
                )

                input_ports_api.update_run_status2(body=run_status, id=port_id)
                disabled_input_ports += 1
                logger.debug(f"  Disabled input port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to disable input port {port_id}: {e}")

        # Get all output ports in the process group (recursively)
        output_ports = canvas.list_all_output_ports(process_group_id)
        logger.info(f"Found {len(output_ports)} output port(s) to disable")

        output_ports_api = OutputPortsApi()
        disabled_output_ports = 0

        for port in output_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="DISABLED"
                )

                output_ports_api.update_run_status3(body=run_status, id=port_id)
                disabled_output_ports += 1
                logger.debug(f"  Disabled output port: {port.component.name} ({port_id})")

            except Exception as e:
                logger.warning(f"  Failed to disable output port {port_id}: {e}")

        total_disabled = disabled_processors + disabled_input_ports + disabled_output_ports
        logger.info(f"✓ Disabled {disabled_processors} processor(s), {disabled_input_ports} input port(s), {disabled_output_ports} output port(s)")

        return {
            "status": "success",
            "message": f"Process group disabled successfully ({total_disabled} components)",
            "process_group_id": process_group_id,
            "disabled_count": {
                "processors": disabled_processors,
                "input_ports": disabled_input_ports,
                "output_ports": disabled_output_ports,
                "total": total_disabled
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to disable process group: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable process group: {error_msg}",
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
    instance = get_instance_or_404(db, instance_id)

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
        instance = get_instance_or_404(db, instance_id)

        logger.info(
            f"Getting processors for process group {process_group_id} on instance {instance_id}"
        )

        # Configure NiFi connection
        setup_nifi_connection(instance)

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
        instance = get_instance_or_404(db, instance_id)

        logger.info(
            f"Getting input ports for process group {process_group_id} "
            f"on instance {instance_id} (descendants={descendants})"
        )

        # Configure NiFi connection
        setup_nifi_connection(instance)

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
        Response with assignment status
    """
    try:
        # Get NiFi instance
        instance = get_instance_or_404(db, instance_id)

        logger.info(
            f"Assigning parameter context {request.parameter_context_id} "
            f"to process group {process_group_id} (cascade={request.cascade})"
        )

        # Configure NiFi connection
        setup_nifi_connection(instance)

        # Get the process group to verify it exists
        from nipyapi.nifi import ProcessGroupsApi

        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group with ID {process_group_id} not found",
            )

        # Build the request body for parameter context assignment
        from nipyapi.nifi.models import ProcessGroupEntity, ProcessGroupDTO

        # Create a DTO with only the parameter context reference
        pg_dto = ProcessGroupDTO(
            id=process_group_id,
            parameter_context={"id": request.parameter_context_id}
            if request.parameter_context_id
            else None,
        )

        # Create entity with current revision
        pg_entity = ProcessGroupEntity(
            component=pg_dto,
            revision=pg.revision,
        )

        # Update the process group
        updated_pg = pg_api.update_process_group(
            id=process_group_id,
            body=pg_entity,
        )

        # Verify the assignment
        assigned_context_id = None
        if (
            hasattr(updated_pg, "component")
            and hasattr(updated_pg.component, "parameter_context")
            and updated_pg.component.parameter_context
        ):
            assigned_context_id = updated_pg.component.parameter_context.get("id")

        logger.info(
            f"✓ Parameter context assigned successfully (assigned ID: {assigned_context_id})"
        )

        return AssignParameterContextResponse(
            status="success",
            message=f"Parameter context assigned to process group successfully",
            process_group_id=process_group_id,
            parameter_context_id=assigned_context_id,
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
