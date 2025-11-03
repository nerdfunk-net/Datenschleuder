"""NiFi installation API endpoints for checking and creating process groups"""

import logging
from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance
from app.services.nifi_auth import configure_nifi_connection
from app.services.nifi_deployment_service import NiFiDeploymentService
from app.api.settings import get_setting_value


router = APIRouter(prefix="/api/nifi-install", tags=["nifi-install"])
logger = logging.getLogger(__name__)


class PathStatus(BaseModel):
    """Status of a process group path"""

    path: str
    exists: bool


class CheckPathResponse(BaseModel):
    """Response for check-path endpoint"""

    status: List[PathStatus]


class CreateGroupsRequest(BaseModel):
    """Request for create-groups endpoint"""

    instance_id: int
    path_type: Literal["source", "destination"]


@router.get("/check-path", response_model=CheckPathResponse)
async def check_path(
    instance_id: int = Query(..., description="NiFi instance ID"),
    path_type: Literal["source", "destination"] = Query(
        ..., description="Path type to check"
    ),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Check if process groups exist for all managed flows.
    For each flow, checks: configured_path_parts + hierarchy_values (excluding last).
    """
    try:
        from nipyapi import canvas

        # Get the NiFi instance
        instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="NiFi instance not found")

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get all process groups (already flattened by nipyapi)
        root_pg_id = canvas.get_root_pg_id()
        all_pgs_raw = canvas.list_all_process_groups(root_pg_id)

        # Build a map of PG id -> PG info
        pg_map = {}
        for pg in all_pgs_raw:
            pg_map[pg.id] = {
                "id": pg.id,
                "name": pg.component.name,
                "parent_group_id": pg.component.parent_group_id,
            }

        # Build paths for each PG by walking up the parent chain
        def build_path(pg_id):
            """Build path from root to this PG"""
            path = []
            current_id = pg_id
            while current_id in pg_map:
                pg_info = pg_map[current_id]
                path.insert(0, {"name": pg_info["name"], "id": pg_info["id"]})
                current_id = pg_info["parent_group_id"]
            return path

        all_pgs = []
        for pg_id, pg_info in pg_map.items():
            pg_info["path"] = build_path(pg_id)
            all_pgs.append(pg_info)

        # Get all managed flows
        result = db.execute(text("SELECT * FROM nifi_flows"))
        rows = result.fetchall()
        columns = result.keys()
        flows = [dict(zip(columns, row)) for row in rows]

        # Get deployment paths configuration
        deployment_paths = get_setting_value(db, "deployment_paths") or {}
        instance_paths = deployment_paths.get(str(instance_id), {})

        # Get the configured path based on type
        if path_type == "source":
            path_config = instance_paths.get("source_path")
            attr_key = "source_hierarchy_attributes"
        else:  # destination
            path_config = instance_paths.get("dest_path")
            attr_key = "destination_hierarchy_attributes"

        if not path_config:
            raise HTTPException(
                status_code=400,
                detail=f"No {path_type} path configured for this instance.",
            )

        # Extract path string from config (support both old format and new format)
        if isinstance(path_config, dict):
            configured_path_full = path_config.get("path", "")
        else:
            # Legacy format: just a string (UUID or path)
            configured_path_full = path_config

        if not configured_path_full:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {path_type} path configuration for this instance.",
            )

        # Split configured path by "/" (e.g., "Nifi Flow/From DC1" -> ["Nifi Flow", "From DC1"])
        configured_path_parts = [p.strip() for p in configured_path_full.split("/")]

        # Get hierarchy configuration
        settings_data = get_setting_value(db, "hierarchy_config")
        if not settings_data or "hierarchy" not in settings_data:
            raise HTTPException(
                status_code=500, detail="Hierarchy configuration not found"
            )

        hierarchy = settings_data["hierarchy"]

        # Build a set of all paths that should exist
        paths_to_check = set()

        # Determine prefix for columns (src_ or dest_)
        column_prefix = "src_" if path_type == "source" else "dest_"

        for flow in flows:
            # Build path: configured_parts + hierarchy_values (up to penultimate)
            path_components = configured_path_parts.copy()

            # Add hierarchy values (excluding first and last level)
            # First level is already in configured path, last level is the flow itself
            for level in hierarchy[1:-1]:
                attr_name = level.get("name")
                # Get value from database column (e.g., src_o, dest_ou, etc.)
                column_name = f"{column_prefix}{attr_name.lower()}"
                attr_value = flow.get(column_name)

                if attr_value:
                    path_components.append(attr_value)

            # Add all intermediate paths to check
            for i in range(1, len(path_components) + 1):
                path = "/".join(path_components[:i])
                paths_to_check.add(path)

        # Build pg lookup by path
        pg_by_path = {}
        for pg in all_pgs:
            path_list = pg.get("path", [])
            if path_list:
                path_str = "/".join([p["name"] for p in path_list])
                pg_by_path[path_str] = pg

        # Check each path
        status_list = []
        for path in sorted(paths_to_check):
            exists = path in pg_by_path
            status_list.append(PathStatus(path=path, exists=exists))

        return CheckPathResponse(status=status_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-groups")
async def create_groups(
    request: CreateGroupsRequest,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Create missing process groups for all managed flows.
    """
    instance = (
        db.query(NiFiInstance).filter(NiFiInstance.id == request.instance_id).first()
    )
    if not instance:
        raise HTTPException(status_code=404, detail="NiFi instance not found")

    try:
        from nipyapi import canvas

        # Configure NiFi connection
        configure_nifi_connection(instance)

        # Get all managed flows
        result = db.execute(text("SELECT * FROM nifi_flows"))
        rows = result.fetchall()
        columns = result.keys()
        flows = [dict(zip(columns, row)) for row in rows]

        # Get deployment paths configuration
        deployment_paths = get_setting_value(db, "deployment_paths") or {}
        instance_paths = deployment_paths.get(str(request.instance_id), {})

        # Get the configured path based on type
        if request.path_type == "source":
            path_config = instance_paths.get("source_path")
            attr_key = "source_hierarchy_attributes"
        else:  # destination
            path_config = instance_paths.get("dest_path")
            attr_key = "destination_hierarchy_attributes"

        if not path_config:
            raise HTTPException(
                status_code=400,
                detail=f"No {request.path_type} path configured for this instance.",
            )

        # Extract path string from config (support both old format and new format)
        if isinstance(path_config, dict):
            configured_path_full = path_config.get("path", "")
        else:
            # Legacy format: just a string (UUID or path)
            configured_path_full = path_config

        if not configured_path_full:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {request.path_type} path configuration for this instance.",
            )

        # Split configured path by "/"
        configured_path_parts = [p.strip() for p in configured_path_full.split("/")]

        # Get hierarchy configuration
        settings_data = get_setting_value(db, "hierarchy_config")
        if not settings_data or "hierarchy" not in settings_data:
            raise HTTPException(
                status_code=500, detail="Hierarchy configuration not found"
            )

        hierarchy = settings_data["hierarchy"]

        # Build all paths that should exist
        all_paths = set()

        # Determine prefix for columns (src_ or dest_)
        column_prefix = "src_" if request.path_type == "source" else "dest_"

        for flow in flows:
            path_components = configured_path_parts.copy()

            # Add hierarchy values (excluding first and last level)
            # First level is already in configured path, last level is the flow itself
            for level in hierarchy[1:-1]:
                attr_name = level.get("name")
                # Get value from database column (e.g., src_o, dest_ou, etc.)
                column_name = f"{column_prefix}{attr_name.lower()}"
                attr_value = flow.get(column_name)

                if attr_value:
                    path_components.append(attr_value)

            # Add all intermediate paths
            for i in range(1, len(path_components) + 1):
                path = "/".join(path_components[:i])
                all_paths.add(path)

        # Get root process group and all existing process groups
        root_pg_id = canvas.get_root_pg_id()
        all_pgs_raw = canvas.list_all_process_groups(root_pg_id)

        # Build a map of PG id -> PG info
        pg_map = {}
        for pg in all_pgs_raw:
            pg_map[pg.id] = {
                "id": pg.id,
                "name": pg.component.name,
                "parent_group_id": pg.component.parent_group_id,
            }

        # Build paths for each PG by walking up the parent chain
        def build_path(pg_id):
            """Build path from root to this PG"""
            path = []
            current_id = pg_id
            while current_id in pg_map:
                pg_info = pg_map[current_id]
                path.insert(0, {"name": pg_info["name"], "id": pg_info["id"]})
                current_id = pg_info["parent_group_id"]
            return path

        all_pgs = []
        for pg_id, pg_info in pg_map.items():
            pg_info["path"] = build_path(pg_id)
            all_pgs.append(pg_info)

        # Build pg lookup by path
        pg_by_path = {}
        for pg in all_pgs:
            path_list = pg.get("path", [])
            if path_list:
                path_str = "/".join([p["name"] for p in path_list])
                pg_by_path[path_str] = pg

        # Find missing paths
        missing_paths = []
        for path in sorted(all_paths):
            if path not in pg_by_path:
                missing_paths.append(path)

        # Create missing groups
        created_groups = []
        
        # Initialize deployment service for port connections
        deployment_service = NiFiDeploymentService(instance)

        for path in missing_paths:
            parts = path.split("/")

            # Find the parent path (all parts except the last)
            if len(parts) == 1:
                # Top-level group, parent is root
                parent_id = root_pg_id
            else:
                parent_path = "/".join(parts[:-1])
                if parent_path in pg_by_path:
                    parent_id = pg_by_path[parent_path]["id"]
                else:
                    # Parent doesn't exist, skip for now (will be created in next iteration)
                    continue

            # Create the last element in the parent
            pg_name = parts[-1]

            # Check if it already exists (might have been created in previous iteration)
            children = canvas.list_all_process_groups(parent_id)
            already_exists = any(
                child.component.name == pg_name and child.component.parent_group_id == parent_id
                for child in children
            )

            if not already_exists:
                logger.info(f"Creating process group: {pg_name} in parent: {parent_id}")
                new_pg = canvas.create_process_group(
                    parent_pg=canvas.get_process_group(parent_id, "id"),
                    new_pg_name=pg_name,
                    location=(0.0, 0.0),
                )
                logger.info(f"  Created process group ID: {new_pg.id}")
                created_groups.append(path)
                
                # Auto-connect output ports between the new process group and its parent
                # This checks if both have output ports and connects them if they do
                logger.info(f"  Attempting to auto-connect ports for: {pg_name}")
                logger.info(f"    New PG ID: {new_pg.id}")
                logger.info(f"    Parent PG ID: {parent_id}")
                try:
                    deployment_service.auto_connect_ports(new_pg.id, parent_id)
                    logger.info(f"  ✓ Auto-connect completed for {path}")
                except Exception as port_error:
                    # Log warning but don't fail the entire operation
                    logger.warning(f"Could not auto-connect ports for {path}: {port_error}")
                    logger.warning(f"  Error type: {type(port_error).__name__}")
                    import traceback
                    logger.warning(f"  Traceback: {traceback.format_exc()}")
                
                # Add to lookup for next iterations
                pg_by_path[path] = {"id": new_pg.id, "name": pg_name, "parent_group_id": parent_id}

        return {
            "status": "success",
            "message": f"Created {len(created_groups)} process groups",
            "created_groups": created_groups,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
