"""Flow view management API endpoints"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.flow_view import FlowView, FlowViewCreate, FlowViewUpdate, FlowViewResponse

router = APIRouter(prefix="/api/flow-views", tags=["flow-views"])


@router.get("/", response_model=List[FlowViewResponse])
async def list_flow_views(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List all flow views"""
    views = db.query(FlowView).order_by(FlowView.is_default.desc(), FlowView.name).all()

    # Parse JSON columns
    result = []
    for view in views:
        view_dict = {
            "id": view.id,
            "name": view.name,
            "description": view.description,
            "visible_columns": json.loads(view.visible_columns),
            "column_widths": json.loads(view.column_widths) if view.column_widths else None,
            "is_default": view.is_default,
            "created_by": view.created_by,
            "created_at": view.created_at,
            "modified_at": view.modified_at
        }
        result.append(view_dict)

    return result


@router.get("/{view_id}", response_model=FlowViewResponse)
async def get_flow_view(
    view_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get a specific flow view"""
    view = db.query(FlowView).filter(FlowView.id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View with id {view_id} not found"
        )

    return {
        "id": view.id,
        "name": view.name,
        "description": view.description,
        "visible_columns": json.loads(view.visible_columns),
        "column_widths": json.loads(view.column_widths) if view.column_widths else None,
        "is_default": view.is_default,
        "created_by": view.created_by,
        "created_at": view.created_at,
        "modified_at": view.modified_at
    }


@router.post("/", response_model=dict)
async def create_flow_view(
    data: FlowViewCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new flow view"""
    # Check if name already exists
    existing = db.query(FlowView).filter(FlowView.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"View with name '{data.name}' already exists"
        )

    # If this is set as default, unset other defaults
    if data.is_default:
        db.query(FlowView).update({"is_default": False})

    # Create new view
    view = FlowView(
        name=data.name,
        description=data.description,
        visible_columns=json.dumps(data.visible_columns),
        column_widths=json.dumps(data.column_widths) if data.column_widths else None,
        is_default=data.is_default,
        created_by=token_data.get("username", "admin")
    )

    db.add(view)
    db.commit()
    db.refresh(view)

    return {
        "message": "Flow view created successfully",
        "id": view.id
    }


@router.put("/{view_id}", response_model=dict)
async def update_flow_view(
    view_id: int,
    data: FlowViewUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update an existing flow view"""
    view = db.query(FlowView).filter(FlowView.id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View with id {view_id} not found"
        )

    # If setting as default, unset other defaults
    if data.is_default:
        db.query(FlowView).filter(FlowView.id != view_id).update({"is_default": False})

    # Update fields
    if data.name is not None:
        # Check if new name conflicts
        existing = db.query(FlowView).filter(
            FlowView.name == data.name,
            FlowView.id != view_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"View with name '{data.name}' already exists"
            )
        view.name = data.name

    if data.description is not None:
        view.description = data.description

    if data.visible_columns is not None:
        view.visible_columns = json.dumps(data.visible_columns)

    if data.column_widths is not None:
        view.column_widths = json.dumps(data.column_widths) if data.column_widths else None

    if data.is_default is not None:
        view.is_default = data.is_default

    db.commit()

    return {
        "message": "Flow view updated successfully",
        "id": view.id
    }


@router.delete("/{view_id}")
async def delete_flow_view(
    view_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a flow view"""
    view = db.query(FlowView).filter(FlowView.id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View with id {view_id} not found"
        )

    db.delete(view)
    db.commit()

    return {
        "message": f"Flow view '{view.name}' deleted successfully"
    }


@router.post("/{view_id}/set-default")
async def set_default_view(
    view_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Set a view as the default"""
    view = db.query(FlowView).filter(FlowView.id == view_id).first()

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View with id {view_id} not found"
        )

    # Unset all other defaults
    db.query(FlowView).update({"is_default": False})

    # Set this as default
    view.is_default = True
    db.commit()

    return {
        "message": f"View '{view.name}' set as default"
    }
