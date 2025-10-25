"""NiFi flows management API endpoints with dynamic table creation"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import (
    Table, Column, Integer, String, Boolean, DateTime, Text, MetaData,
    inspect, text
)
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import get_db
from app.core import database
from app.core.security import verify_token
from app.models.nifi_flow import NiFiFlowCreate, NiFiFlowUpdate, NiFiFlowResponse
from app.api.settings import get_setting_value

router = APIRouter(prefix="/api/nifi-flows", tags=["nifi-flows"])


def get_engine():
    """Get the database engine, raising error if not initialized"""
    if database.engine is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database engine not initialized"
        )
    return database.engine


def get_hierarchy_config(db: Session) -> List[dict]:
    """Get the current hierarchy configuration"""
    settings = get_setting_value(db, "data_format_config")

    if not settings:
        # Return default hierarchy
        return [
            {"name": "CN", "label": "Common Name", "order": 0},
            {"name": "O", "label": "Organization", "order": 1},
            {"name": "OU", "label": "Organizational Unit", "order": 2},
            {"name": "DC", "label": "Domain Component", "order": 3}
        ]

    return settings.get("hierarchy", [])


def create_nifi_flows_table(db: Session):
    """
    Dynamically create the nifi_flows table based on current hierarchy configuration.
    If table exists, it will be dropped and recreated.
    """
    engine = get_engine()
    hierarchy = get_hierarchy_config(db)

    # Sort by order to ensure correct column order
    hierarchy = sorted(hierarchy, key=lambda x: x.get("order", 0))

    metadata = MetaData()

    # Check if table exists and drop it
    inspector = inspect(engine)
    if inspector.has_table("nifi_flows"):
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS nifi_flows"))
            conn.commit()

    # Build columns list
    columns = [
        Column("id", Integer, primary_key=True, index=True),
    ]

    # Add dynamic hierarchy columns
    for attr in hierarchy:
        col_name = attr["name"].lower()
        columns.append(Column(col_name, String, nullable=False, index=True))

    # Add standard flow columns
    columns.extend([
        Column("source", String, nullable=False),
        Column("destination", String, nullable=False),
        Column("connection_param", String, nullable=False),
        Column("template", String, nullable=False),
        Column("active", Boolean, nullable=False, default=True),
        Column("description", Text, nullable=True),
        Column("creator_name", String, nullable=True),
        Column("created_at", DateTime(timezone=True), server_default=func.now()),
        Column("modified_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    ])

    # Create table
    table = Table("nifi_flows", metadata, *columns)
    metadata.create_all(engine)

    return {
        "table_name": "nifi_flows",
        "hierarchy_columns": [attr["name"] for attr in hierarchy],
        "total_columns": len(columns)
    }


@router.post("/recreate-table")
async def recreate_nifi_flows_table(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Recreate the nifi_flows table based on current hierarchy configuration.
    WARNING: This will drop the existing table and all data will be lost!
    """
    try:
        result = create_nifi_flows_table(db)
        return {
            "message": "NiFi flows table recreated successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recreate table: {str(e)}"
        )


@router.get("/table-info")
async def get_table_info(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get information about the current nifi_flows table structure"""
    try:
        engine = get_engine()
        inspector = inspect(engine)

        if not inspector.has_table("nifi_flows"):
            return {
                "exists": False,
                "message": "Table does not exist. Use POST /recreate-table to create it."
            }

        columns = inspector.get_columns("nifi_flows")
        hierarchy = get_hierarchy_config(db)

        return {
            "exists": True,
            "table_name": "nifi_flows",
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "primary_key": col.get("primary_key", False)
                }
                for col in columns
            ],
            "hierarchy_columns": [attr["name"] for attr in hierarchy],
            "current_hierarchy": hierarchy
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table info: {str(e)}"
        )


@router.post("/", response_model=dict)
async def create_nifi_flow(
    data: NiFiFlowCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new NiFi flow entry"""
    try:
        engine = get_engine()
        # Check if table exists
        inspector = inspect(engine)
        if not inspector.has_table("nifi_flows"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NiFi flows table does not exist. Use POST /recreate-table first."
            )

        # Get current hierarchy
        hierarchy = get_hierarchy_config(db)
        hierarchy_names = [attr["name"] for attr in hierarchy]

        # Validate hierarchy values
        for name in hierarchy_names:
            if name not in data.hierarchy_values:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing hierarchy value: {name}"
                )

        # Build insert query
        columns = [attr["name"].lower() for attr in hierarchy]
        columns.extend(["source", "destination", "connection_param", "template", "active", "description", "creator_name"])

        values = [data.hierarchy_values[attr["name"]] for attr in hierarchy]
        values.extend([
            data.source,
            data.destination,
            data.connection_param,
            data.template,
            data.active,
            data.description,
            data.creator_name
        ])

        placeholders = ", ".join([f":{i}" for i in range(len(values))])
        cols_str = ", ".join(columns)

        query = text(f"INSERT INTO nifi_flows ({cols_str}) VALUES ({placeholders}) RETURNING id")

        with engine.connect() as conn:
            result = conn.execute(query, {str(i): v for i, v in enumerate(values)})
            conn.commit()
            row_id = result.fetchone()[0]

        return {
            "message": "NiFi flow created successfully",
            "id": row_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create flow: {str(e)}"
        )


@router.get("/")
async def list_nifi_flows(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List all NiFi flows"""
    try:
        engine = get_engine()
        # Check if table exists
        inspector = inspect(engine)
        if not inspector.has_table("nifi_flows"):
            return {
                "flows": [],
                "message": "Table does not exist. Use POST /recreate-table to create it."
            }

        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM nifi_flows ORDER BY created_at DESC"))
            rows = result.fetchall()
            columns = result.keys()

            flows = []
            for row in rows:
                flow_dict = dict(zip(columns, row))
                flows.append(flow_dict)

        return {"flows": flows}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list flows: {str(e)}"
        )


@router.put("/{flow_id}", response_model=dict)
async def update_nifi_flow(
    flow_id: int,
    data: NiFiFlowUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update an existing NiFi flow entry"""
    try:
        engine = get_engine()
        # Check if table exists
        inspector = inspect(engine)
        if not inspector.has_table("nifi_flows"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NiFi flows table does not exist. Use POST /recreate-table first."
            )

        # Get current hierarchy
        hierarchy = get_hierarchy_config(db)

        # Build update query
        update_parts = []
        values = {}
        param_counter = 0

        # Update hierarchy values if provided
        if data.hierarchy_values:
            for attr in hierarchy:
                attr_name = attr["name"]
                if attr_name in data.hierarchy_values:
                    col_name = attr_name.lower()
                    update_parts.append(f"{col_name} = :param_{param_counter}")
                    values[f"param_{param_counter}"] = data.hierarchy_values[attr_name]
                    param_counter += 1

        # Update standard fields if provided
        if data.source is not None:
            update_parts.append(f"source = :param_{param_counter}")
            values[f"param_{param_counter}"] = data.source
            param_counter += 1

        if data.destination is not None:
            update_parts.append(f"destination = :param_{param_counter}")
            values[f"param_{param_counter}"] = data.destination
            param_counter += 1

        if data.connection_param is not None:
            update_parts.append(f"connection_param = :param_{param_counter}")
            values[f"param_{param_counter}"] = data.connection_param
            param_counter += 1

        if data.template is not None:
            update_parts.append(f"template = :param_{param_counter}")
            values[f"param_{param_counter}"] = data.template
            param_counter += 1

        if data.active is not None:
            update_parts.append(f"active = :param_{param_counter}")
            values[f"param_{param_counter}"] = data.active
            param_counter += 1

        if data.description is not None:
            update_parts.append(f"description = :param_{param_counter}")
            values[f"param_{param_counter}"] = data.description
            param_counter += 1

        # Always update modified_at
        update_parts.append("modified_at = CURRENT_TIMESTAMP")

        if not update_parts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update"
            )

        # Build and execute update query
        update_clause = ", ".join(update_parts)
        values["flow_id"] = flow_id

        query = text(f"UPDATE nifi_flows SET {update_clause} WHERE id = :flow_id")

        with engine.connect() as conn:
            result = conn.execute(query, values)
            conn.commit()

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Flow with id {flow_id} not found"
                )

        return {
            "message": "NiFi flow updated successfully",
            "id": flow_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update flow: {str(e)}"
        )


@router.delete("/{flow_id}")
async def delete_nifi_flow(
    flow_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a NiFi flow entry"""
    try:
        engine = get_engine()
        # Check if table exists
        inspector = inspect(engine)
        if not inspector.has_table("nifi_flows"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NiFi flows table does not exist."
            )

        query = text("DELETE FROM nifi_flows WHERE id = :flow_id")

        with engine.connect() as conn:
            result = conn.execute(query, {"flow_id": flow_id})
            conn.commit()

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Flow with id {flow_id} not found"
                )

        return {
            "message": f"NiFi flow {flow_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete flow: {str(e)}"
        )
