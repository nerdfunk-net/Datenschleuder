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

    This endpoint will automatically stop the process group before deleting it
    to avoid deletion errors for running process groups.
    """
    instance = get_instance_or_404(db, instance_id)

    try:
        import nipyapi
        from nipyapi import config, security, canvas
        from nipyapi.nifi import (
            ProcessorsApi, ProcessorRunStatusEntity, RevisionDTO,
            InputPortsApi, OutputPortsApi, PortRunStatusEntity,
            ProcessGroupsApi
        )

        # Configure nipyapi
        setup_nifi_connection(instance, normalize_url=True)

        logger.info(f"Preparing to delete process group {process_group_id}...")

        # Get the process group first to verify it exists
        pg_api = ProcessGroupsApi()
        pg = pg_api.get_process_group(id=process_group_id)

        if not pg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group {process_group_id} not found"
            )

        pg_name = pg.component.name if hasattr(pg, 'component') and hasattr(pg.component, 'name') else process_group_id
        logger.info(f"Found process group: {pg_name}")

        # Step 1: Stop all components in the process group
        logger.info(f"Step 1: Stopping all components in process group {pg_name}...")

        # Stop all processors
        processors = canvas.list_all_processors(process_group_id)
        logger.info(f"  Stopping {len(processors)} processor(s)...")

        processors_api = ProcessorsApi()
        for processor in processors:
            try:
                processor_id = processor.id
                current_revision = processor.revision

                run_status = ProcessorRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                processors_api.update_run_status4(body=run_status, id=processor_id)
                logger.debug(f"    Stopped processor: {processor.component.name}")

            except Exception as e:
                logger.warning(f"    Failed to stop processor {processor_id}: {e}")

        # Stop all input ports
        input_ports = canvas.list_all_input_ports(process_group_id)
        logger.info(f"  Stopping {len(input_ports)} input port(s)...")

        input_ports_api = InputPortsApi()
        for port in input_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                input_ports_api.update_run_status2(body=run_status, id=port_id)
                logger.debug(f"    Stopped input port: {port.component.name}")

            except Exception as e:
                logger.warning(f"    Failed to stop input port {port_id}: {e}")

        # Stop all output ports
        output_ports = canvas.list_all_output_ports(process_group_id)
        logger.info(f"  Stopping {len(output_ports)} output port(s)...")

        output_ports_api = OutputPortsApi()
        for port in output_ports:
            try:
                port_id = port.id
                current_revision = port.revision

                run_status = PortRunStatusEntity(
                    revision=RevisionDTO(version=current_revision.version),
                    state="STOPPED"
                )

                output_ports_api.update_run_status3(body=run_status, id=port_id)
                logger.debug(f"    Stopped output port: {port.component.name}")

            except Exception as e:
                logger.warning(f"    Failed to stop output port {port_id}: {e}")

        logger.info(f"✓ All components stopped successfully")

        # Step 2: Stop destinations of all outgoing connections (including connections in parent PG)
        # Track original states to restore them later
        logger.info(f"Step 2: Checking and stopping outgoing connection destinations...")

        components_to_restore = []  # List of (component_type, component_id, original_state, api)

        try:
            # Get parent process group ID to search for connections there as well
            parent_pg_id = pg.component.parent_group_id if hasattr(pg, 'component') and hasattr(pg.component, 'parent_group_id') else None

            if parent_pg_id:
                logger.info(f"  Checking connections in parent process group: {parent_pg_id}")

                # Get all connections from the parent process group (this includes connections FROM our PG TO parent)
                parent_connections = canvas.list_all_connections(parent_pg_id, descendants=False)
                logger.info(f"  Found {len(parent_connections)} connection(s) in parent process group")

                # Find connections that originate from within our process group
                for connection in parent_connections:
                    try:
                        source = connection.component.source if hasattr(connection, 'component') and hasattr(connection.component, 'source') else None
                        dest = connection.component.destination if hasattr(connection, 'component') and hasattr(connection.component, 'destination') else None

                        if source and dest and hasattr(source, 'group_id') and hasattr(dest, 'group_id'):
                            source_group_id = source.group_id
                            dest_group_id = dest.group_id
                            dest_id = dest.id
                            dest_type = dest.type if hasattr(dest, 'type') else 'unknown'
                            dest_name = dest.name if hasattr(dest, 'name') else dest_id

                            # Check if source is from our process group and destination is in parent (outgoing connection)
                            if source_group_id == process_group_id and dest_group_id == parent_pg_id:
                                logger.info(f"    Found outgoing connection to {dest_type} '{dest_name}' (ID: {dest_id}) in parent group")

                                # Stop the destination component based on its type and track original state
                                if dest_type == 'OUTPUT_PORT':
                                    try:
                                        dest_port = output_ports_api.get_output_port(dest_id)
                                        if dest_port:
                                            original_state = dest_port.component.state if hasattr(dest_port, 'component') and hasattr(dest_port.component, 'state') else None
                                            logger.info(f"      Original state of output port '{dest_name}': {original_state}")

                                            # Only stop if it's running
                                            if original_state == 'RUNNING':
                                                run_status = PortRunStatusEntity(
                                                    revision=RevisionDTO(version=dest_port.revision.version),
                                                    state="STOPPED"
                                                )
                                                output_ports_api.update_run_status3(body=run_status, id=dest_id)
                                                logger.info(f"      ✓ Stopped destination output port: {dest_name}")

                                                # Track for restoration
                                                components_to_restore.append(('OUTPUT_PORT', dest_id, dest_name, original_state))
                                    except Exception as e:
                                        logger.warning(f"      Failed to stop destination output port {dest_id}: {e}")

                                elif dest_type == 'INPUT_PORT':
                                    try:
                                        dest_port = input_ports_api.get_input_port(dest_id)
                                        if dest_port:
                                            original_state = dest_port.component.state if hasattr(dest_port, 'component') and hasattr(dest_port.component, 'state') else None
                                            logger.info(f"      Original state of input port '{dest_name}': {original_state}")

                                            # Only stop if it's running
                                            if original_state == 'RUNNING':
                                                run_status = PortRunStatusEntity(
                                                    revision=RevisionDTO(version=dest_port.revision.version),
                                                    state="STOPPED"
                                                )
                                                input_ports_api.update_run_status2(body=run_status, id=dest_id)
                                                logger.info(f"      ✓ Stopped destination input port: {dest_name}")

                                                # Track for restoration
                                                components_to_restore.append(('INPUT_PORT', dest_id, dest_name, original_state))
                                    except Exception as e:
                                        logger.warning(f"      Failed to stop destination input port {dest_id}: {e}")

                                elif dest_type == 'PROCESSOR':
                                    try:
                                        dest_proc = processors_api.get_processor(dest_id)
                                        if dest_proc:
                                            original_state = dest_proc.component.state if hasattr(dest_proc, 'component') and hasattr(dest_proc.component, 'state') else None
                                            logger.info(f"      Original state of processor '{dest_name}': {original_state}")

                                            # Only stop if it's running
                                            if original_state == 'RUNNING':
                                                run_status = ProcessorRunStatusEntity(
                                                    revision=RevisionDTO(version=dest_proc.revision.version),
                                                    state="STOPPED"
                                                )
                                                processors_api.update_run_status4(body=run_status, id=dest_id)
                                                logger.info(f"      ✓ Stopped destination processor: {dest_name}")

                                                # Track for restoration
                                                components_to_restore.append(('PROCESSOR', dest_id, dest_name, original_state))
                                    except Exception as e:
                                        logger.warning(f"      Failed to stop destination processor {dest_id}: {e}")

                    except Exception as e:
                        logger.warning(f"    Failed to process connection: {e}")
            else:
                logger.info(f"  No parent process group found - skipping parent connection check")

        except Exception as e:
            logger.warning(f"  Failed to stop outgoing connection destinations: {e}")

        logger.info(f"✓ Outgoing connection destinations stopped")

        # Step 3: Delete the process group (wrapped in try/finally to ensure restoration)
        deletion_error = None
        try:
            logger.info(f"Step 3: Deleting process group {pg_name}...")
            canvas.delete_process_group(pg, force=True, refresh=True)
            logger.info(f"✓ Process group '{pg_name}' deleted successfully")
        except Exception as e:
            deletion_error = e
            logger.error(f"Failed to delete process group: {str(e)}")
        finally:
            # Step 4: ALWAYS restore components that were stopped (regardless of success/failure)
            if components_to_restore:
                logger.info(f"Step 4: Restoring {len(components_to_restore)} component(s) to original state...")

                for comp_type, comp_id, comp_name, original_state in components_to_restore:
                    try:
                        if comp_type == 'OUTPUT_PORT':
                            # Get fresh component to get current revision
                            dest_port = output_ports_api.get_output_port(comp_id)
                            if dest_port and original_state == 'RUNNING':
                                run_status = PortRunStatusEntity(
                                    revision=RevisionDTO(version=dest_port.revision.version),
                                    state="RUNNING"
                                )
                                output_ports_api.update_run_status3(body=run_status, id=comp_id)
                                logger.info(f"      ✓ Restored output port '{comp_name}' to {original_state}")

                        elif comp_type == 'INPUT_PORT':
                            dest_port = input_ports_api.get_input_port(comp_id)
                            if dest_port and original_state == 'RUNNING':
                                run_status = PortRunStatusEntity(
                                    revision=RevisionDTO(version=dest_port.revision.version),
                                    state="RUNNING"
                                )
                                input_ports_api.update_run_status2(body=run_status, id=comp_id)
                                logger.info(f"      ✓ Restored input port '{comp_name}' to {original_state}")

                        elif comp_type == 'PROCESSOR':
                            dest_proc = processors_api.get_processor(comp_id)
                            if dest_proc and original_state == 'RUNNING':
                                run_status = ProcessorRunStatusEntity(
                                    revision=RevisionDTO(version=dest_proc.revision.version),
                                    state="RUNNING"
                                )
                                processors_api.update_run_status4(body=run_status, id=comp_id)
                                logger.info(f"      ✓ Restored processor '{comp_name}' to {original_state}")

                    except Exception as e:
                        logger.error(f"      Failed to restore {comp_type} '{comp_name}' (ID: {comp_id}): {e}")

                logger.info(f"✓ Component restoration completed")

        # If deletion failed, raise the error now (after restoration)
        if deletion_error:
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete process group: {str(deletion_error)}",
            )

        return {
            "status": "success",
            "message": f"Process group '{pg_name}' stopped and deleted successfully",
            "process_group_id": process_group_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to delete process group: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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


@router.get("/{instance_id}/list-all-by-kind")
async def list_all_by_kind(
    instance_id: int,
    kind: str,
    pg_id: str = 'root',
    descendants: bool = True,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    List all components of a specific kind on a NiFi instance.

    Args:
        instance_id: NiFi instance ID
        kind: Component kind to list (e.g., 'processors', 'input_ports', 'output_ports',
              'process_groups', 'connections', 'funnels', 'labels', 'controller_services')
        pg_id: Process group ID to search within (default: 'root')
        descendants: Whether to include descendants (default: True)
        token_data: Authentication token data
        db: Database session

    Returns:
        List of all components of the specified kind
    """
    try:
        # Get NiFi instance
        instance = get_instance_or_404(db, instance_id)

        logger.info(
            f"Listing all components of kind '{kind}' on instance {instance_id} "
            f"(pg_id={pg_id}, descendants={descendants})"
        )

        # Configure NiFi connection
        setup_nifi_connection(instance)

        # Get all components by kind using nipyapi
        from nipyapi import canvas

        components_list = canvas.list_all_by_kind(
            kind=kind,
            pg_id=pg_id,
            descendants=descendants
        )

        # Convert to response format
        components_info = []
        if components_list:
            for component in components_list:
                component_data = {}

                # Extract common fields
                if hasattr(component, 'id'):
                    component_data['id'] = component.id

                if hasattr(component, 'component'):
                    comp = component.component
                    component_data['name'] = comp.name if hasattr(comp, 'name') else None
                    component_data['parent_group_id'] = comp.parent_group_id if hasattr(comp, 'parent_group_id') else None
                    component_data['type'] = comp.type if hasattr(comp, 'type') else None
                    component_data['comments'] = comp.comments if hasattr(comp, 'comments') else None

                    # For processors, include state
                    if kind == 'processors' or kind == 'processor':
                        component_data['state'] = comp.state if hasattr(comp, 'state') else None

                    # For ports, include state
                    if kind in ['input_ports', 'output_ports', 'input_port', 'output_port']:
                        component_data['state'] = comp.state if hasattr(comp, 'state') else None

                    # For process groups, include version control info
                    if kind in ['process_groups', 'process_group']:
                        if hasattr(comp, 'version_control_information') and comp.version_control_information:
                            vci = comp.version_control_information
                            component_data['version_control_information'] = {
                                'registry_id': vci.registry_id if hasattr(vci, 'registry_id') else None,
                                'bucket_id': vci.bucket_id if hasattr(vci, 'bucket_id') else None,
                                'flow_id': vci.flow_id if hasattr(vci, 'flow_id') else None,
                                'version': vci.version if hasattr(vci, 'version') else None,
                                'state': vci.state if hasattr(vci, 'state') else None,
                            }

                    # For connections, include source and destination
                    if kind in ['connections', 'connection']:
                        if hasattr(comp, 'source'):
                            source = comp.source
                            component_data['source'] = {
                                'id': source.id if hasattr(source, 'id') else None,
                                'name': source.name if hasattr(source, 'name') else None,
                                'type': source.type if hasattr(source, 'type') else None,
                                'group_id': source.group_id if hasattr(source, 'group_id') else None,
                            }
                        if hasattr(comp, 'destination'):
                            dest = comp.destination
                            component_data['destination'] = {
                                'id': dest.id if hasattr(dest, 'id') else None,
                                'name': dest.name if hasattr(dest, 'name') else None,
                                'type': dest.type if hasattr(dest, 'type') else None,
                                'group_id': dest.group_id if hasattr(dest, 'group_id') else None,
                            }

                # Include status if available
                if hasattr(component, 'status'):
                    status = component.status
                    component_data['status'] = {}
                    if hasattr(status, 'run_status'):
                        component_data['status']['run_status'] = status.run_status
                    if hasattr(status, 'aggregate_snapshot'):
                        snapshot = status.aggregate_snapshot
                        component_data['status']['aggregate_snapshot'] = {
                            'active_thread_count': snapshot.active_thread_count if hasattr(snapshot, 'active_thread_count') else None,
                            'bytes_in': snapshot.bytes_in if hasattr(snapshot, 'bytes_in') else None,
                            'bytes_out': snapshot.bytes_out if hasattr(snapshot, 'bytes_out') else None,
                            'flow_files_in': snapshot.flow_files_in if hasattr(snapshot, 'flow_files_in') else None,
                            'flow_files_out': snapshot.flow_files_out if hasattr(snapshot, 'flow_files_out') else None,
                            'queued': snapshot.queued if hasattr(snapshot, 'queued') else None,
                        }

                components_info.append(component_data)

        logger.info(f"✓ Found {len(components_info)} component(s) of kind '{kind}'")

        return {
            'status': 'success',
            'kind': kind,
            'pg_id': pg_id,
            'descendants': descendants,
            'components': components_info,
            'count': len(components_info),
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to list components by kind: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list components by kind: {error_msg}",
        )


@router.get("/{instance_id}/component-connection")
async def get_component_connections(
    instance_id: int,
    component_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get all connections for a specific component (processor, port, etc).

    Args:
        instance_id: NiFi instance ID
        component_id: Component ID to get connections for
        token_data: Authentication token data
        db: Database session

    Returns:
        List of connections associated with the component
    """
    try:
        # Get NiFi instance
        instance = get_instance_or_404(db, instance_id)

        logger.info(
            f"Getting connections for component {component_id} "
            f"on instance {instance_id}"
        )

        # Configure NiFi connection
        setup_nifi_connection(instance)

        # Get the component first
        from nipyapi import canvas
        from nipyapi.nifi import ProcessorsApi, InputPortsApi, OutputPortsApi

        # Try to get the component (could be processor, input port, or output port)
        component = None
        component_type = None

        # Try processor first
        try:
            processors_api = ProcessorsApi()
            component = processors_api.get_processor(component_id)
            component_type = 'PROCESSOR'
            logger.info(f"  Found processor: {component.component.name if hasattr(component, 'component') else component_id}")
        except Exception:
            pass

        # Try input port
        if not component:
            try:
                input_ports_api = InputPortsApi()
                component = input_ports_api.get_input_port(component_id)
                component_type = 'INPUT_PORT'
                logger.info(f"  Found input port: {component.component.name if hasattr(component, 'component') else component_id}")
            except Exception:
                pass

        # Try output port
        if not component:
            try:
                output_ports_api = OutputPortsApi()
                component = output_ports_api.get_output_port(component_id)
                component_type = 'OUTPUT_PORT'
                logger.info(f"  Found output port: {component.component.name if hasattr(component, 'component') else component_id}")
            except Exception:
                pass

        if not component:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Component with ID {component_id} not found"
            )

        # Get connections for the component
        connections_list = canvas.get_component_connections(component)

        # Convert to response format
        connections_info = []
        if connections_list:
            for conn in connections_list:
                source_info = None
                dest_info = None

                # Extract source information
                if hasattr(conn, 'component') and hasattr(conn.component, 'source'):
                    source = conn.component.source
                    source_info = {
                        'id': source.id if hasattr(source, 'id') else None,
                        'name': source.name if hasattr(source, 'name') else None,
                        'type': source.type if hasattr(source, 'type') else None,
                        'group_id': source.group_id if hasattr(source, 'group_id') else None,
                    }

                # Extract destination information
                if hasattr(conn, 'component') and hasattr(conn.component, 'destination'):
                    dest = conn.component.destination
                    dest_info = {
                        'id': dest.id if hasattr(dest, 'id') else None,
                        'name': dest.name if hasattr(dest, 'name') else None,
                        'type': dest.type if hasattr(dest, 'type') else None,
                        'group_id': dest.group_id if hasattr(dest, 'group_id') else None,
                    }

                connection_data = {
                    'id': conn.id if hasattr(conn, 'id') else None,
                    'name': conn.component.name if hasattr(conn, 'component') and hasattr(conn.component, 'name') else None,
                    'parent_group_id': conn.component.parent_group_id if hasattr(conn, 'component') and hasattr(conn.component, 'parent_group_id') else None,
                    'source': source_info,
                    'destination': dest_info,
                    'selected_relationships': conn.component.selected_relationships if hasattr(conn, 'component') and hasattr(conn.component, 'selected_relationships') else None,
                }
                connections_info.append(connection_data)

        logger.info(f"✓ Found {len(connections_info)} connection(s) for component")

        return {
            'status': 'success',
            'component_id': component_id,
            'component_type': component_type,
            'connections': connections_info,
            'count': len(connections_info),
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get component connections: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get component connections: {error_msg}",
        )


@router.get("/{instance_id}/process-group/{process_group_id}/all-connections")
async def get_all_connections(
    instance_id: int,
    process_group_id: str,
    descendants: bool = True,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get all connections for a process group.

    Args:
        instance_id: NiFi instance ID
        process_group_id: Process group ID to get connections for
        descendants: Whether to include connections from descendant process groups (default: True)
        token_data: Authentication token data
        db: Database session

    Returns:
        List of all connections with source and destination information
    """
    try:
        # Get NiFi instance
        instance = get_instance_or_404(db, instance_id)

        logger.info(
            f"Getting all connections for process group {process_group_id} "
            f"on instance {instance_id} (descendants={descendants})"
        )

        # Configure NiFi connection
        setup_nifi_connection(instance)

        # Get all connections using nipyapi
        from nipyapi import canvas

        connections_list = canvas.list_all_connections(
            pg_id=process_group_id, descendants=descendants
        )

        # Convert to response format
        connections_info = []
        if connections_list:
            for conn in connections_list:
                source_info = None
                dest_info = None

                # Extract source information
                if hasattr(conn, 'component') and hasattr(conn.component, 'source'):
                    source = conn.component.source
                    source_info = {
                        'id': source.id if hasattr(source, 'id') else None,
                        'name': source.name if hasattr(source, 'name') else None,
                        'type': source.type if hasattr(source, 'type') else None,
                        'group_id': source.group_id if hasattr(source, 'group_id') else None,
                    }

                # Extract destination information
                if hasattr(conn, 'component') and hasattr(conn.component, 'destination'):
                    dest = conn.component.destination
                    dest_info = {
                        'id': dest.id if hasattr(dest, 'id') else None,
                        'name': dest.name if hasattr(dest, 'name') else None,
                        'type': dest.type if hasattr(dest, 'type') else None,
                        'group_id': dest.group_id if hasattr(dest, 'group_id') else None,
                    }

                connection_data = {
                    'id': conn.id if hasattr(conn, 'id') else None,
                    'name': conn.component.name if hasattr(conn, 'component') and hasattr(conn.component, 'name') else None,
                    'parent_group_id': conn.component.parent_group_id if hasattr(conn, 'component') and hasattr(conn.component, 'parent_group_id') else None,
                    'source': source_info,
                    'destination': dest_info,
                    'selected_relationships': conn.component.selected_relationships if hasattr(conn, 'component') and hasattr(conn.component, 'selected_relationships') else None,
                }
                connections_info.append(connection_data)

        logger.info(f"✓ Found {len(connections_info)} connection(s)")

        return {
            'status': 'success',
            'process_group_id': process_group_id,
            'connections': connections_info,
            'count': len(connections_info),
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get connections: {error_msg}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connections: {error_msg}",
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
