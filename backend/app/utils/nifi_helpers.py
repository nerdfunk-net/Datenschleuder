"""
NiFi helper utilities for common operations.

This module contains reusable utility functions for working with NiFi
process groups and components, extracted from the API layer to promote
code reuse and maintainability.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def extract_pg_info(pg: Any) -> Dict[str, Any]:
    """
    Extract process group information from a NiFi process group object.

    This helper safely extracts common attributes from a nipyapi ProcessGroupEntity
    object using hasattr checks to handle variations in the API response structure.

    Args:
        pg: A nipyapi ProcessGroupEntity object from the NiFi API.

    Returns:
        Dictionary containing extracted process group information:
            - id: Process group ID
            - name: Process group name
            - parent_group_id: Parent process group ID
            - comments: Process group comments/description
            - running_count: Count of running components
            - stopped_count: Count of stopped components
            - invalid_count: Count of invalid components
    """
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
        "running_count": pg.running_count if hasattr(pg, "running_count") else 0,
        "stopped_count": pg.stopped_count if hasattr(pg, "stopped_count") else 0,
        "invalid_count": pg.invalid_count if hasattr(pg, "invalid_count") else 0,
    }


def safe_get_attribute(obj: Any, attr_path: str, default: Any = None) -> Any:
    """
    Safely get a nested attribute from an object using dot notation.

    This utility function traverses nested object attributes safely,
    returning a default value if any attribute in the path doesn't exist.

    Args:
        obj: The object to traverse.
        attr_path: Dot-separated path to the attribute (e.g., "component.name").
        default: Default value to return if attribute doesn't exist.

    Returns:
        The attribute value if found, otherwise the default value.

    Examples:
        >>> safe_get_attribute(pg, "component.name", "Unknown")
        'MyProcessGroup'
        >>> safe_get_attribute(pg, "component.missing.attr", None)
        None
    """
    try:
        current = obj
        for attr in attr_path.split("."):
            if not hasattr(current, attr):
                return default
            current = getattr(current, attr)
        return current
    except (AttributeError, TypeError):
        return default


def build_process_group_path(pg_map: Dict[str, Dict[str, Any]], pg_id: str, root_pg_id: str) -> str:
    """
    Build the full path string for a process group from the root.

    Given a mapping of process groups and a target process group ID,
    this function constructs the full hierarchical path from root to
    the target process group.

    Args:
        pg_map: Dictionary mapping process group IDs to their info dicts
                (must include 'name' and 'parent_group_id' keys).
        pg_id: The process group ID to build the path for.
        root_pg_id: The root process group ID (path building stops here).

    Returns:
        Full path string with process group names separated by '/' (e.g., "root/level1/level2").
        Returns "/" if the target is the root process group.

    Examples:
        >>> pg_map = {
        ...     "root-id": {"name": "NiFi Flow", "parent_group_id": None},
        ...     "child-id": {"name": "SubFlow", "parent_group_id": "root-id"}
        ... }
        >>> build_process_group_path(pg_map, "child-id", "root-id")
        'NiFi Flow/SubFlow'
    """
    if pg_id == root_pg_id:
        return "/"
    
    path_parts = []
    current_id = pg_id
    visited_ids = set()
    
    # Traverse from target to root, collecting names
    while current_id and current_id in pg_map and current_id != root_pg_id:
        # Prevent infinite loops
        if current_id in visited_ids:
            break
        visited_ids.add(current_id)
        
        pg_info = pg_map[current_id]
        path_parts.insert(0, pg_info["name"])
        current_id = pg_info.get("parent_group_id")
    
    # Add root name if it exists
    if root_pg_id in pg_map:
        path_parts.insert(0, pg_map[root_pg_id]["name"])
    
    return "/".join(path_parts) if path_parts else "/"
