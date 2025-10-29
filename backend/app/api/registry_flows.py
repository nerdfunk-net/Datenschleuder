"""Registry flows management API endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.registry_flow import (
    RegistryFlow,
    RegistryFlowCreate,
    RegistryFlowResponse,
)

router = APIRouter(prefix="/api/registry-flows", tags=["registry-flows"])


@router.get("/", response_model=List[RegistryFlowResponse])
async def list_registry_flows(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List all registry flows"""
    flows = (
        db.query(RegistryFlow)
        .order_by(
            RegistryFlow.nifi_instance_name,
            RegistryFlow.bucket_name,
            RegistryFlow.flow_name,
        )
        .all()
    )
    return flows


@router.get("/{flow_id}", response_model=RegistryFlowResponse)
async def get_registry_flow(
    flow_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get a specific registry flow"""
    flow = db.query(RegistryFlow).filter(RegistryFlow.id == flow_id).first()

    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry flow with id {flow_id} not found",
        )

    return flow


@router.post("/", response_model=dict)
async def create_registry_flows(
    flows: List[RegistryFlowCreate],
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create one or more registry flows"""
    created_count = 0
    skipped_count = 0

    for flow_data in flows:
        # Check if flow already exists
        existing = (
            db.query(RegistryFlow)
            .filter(
                RegistryFlow.nifi_instance_url == flow_data.nifi_instance_url,
                RegistryFlow.bucket_id == flow_data.bucket_id,
                RegistryFlow.flow_id == flow_data.flow_id,
            )
            .first()
        )

        if existing:
            skipped_count += 1
            continue

        # Create new registry flow
        new_flow = RegistryFlow(
            nifi_instance_name=flow_data.nifi_instance_name,
            nifi_instance_url=flow_data.nifi_instance_url,
            registry_id=flow_data.registry_id,
            registry_name=flow_data.registry_name,
            bucket_id=flow_data.bucket_id,
            bucket_name=flow_data.bucket_name,
            flow_id=flow_data.flow_id,
            flow_name=flow_data.flow_name,
            flow_description=flow_data.flow_description,
        )

        db.add(new_flow)
        created_count += 1

    db.commit()

    return {
        "message": f"Created {created_count} flows, skipped {skipped_count} duplicates",
        "created": created_count,
        "skipped": skipped_count,
    }


@router.delete("/{flow_id}")
async def delete_registry_flow(
    flow_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a registry flow"""
    flow = db.query(RegistryFlow).filter(RegistryFlow.id == flow_id).first()

    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry flow with id {flow_id} not found",
        )

    flow_name = flow.flow_name
    db.delete(flow)
    db.commit()

    return {"message": f"Registry flow '{flow_name}' deleted successfully"}


@router.get("/templates/list", response_model=List[dict])
async def list_flow_templates(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List all flows formatted for template selection dropdown"""
    flows = db.query(RegistryFlow).order_by(RegistryFlow.flow_name).all()

    return [
        {
            "id": flow.id,
            "name": flow.flow_name,
            "label": f"{flow.flow_name} ({flow.nifi_instance_name} / {flow.bucket_name})",
            "nifi_instance": flow.nifi_instance_name,
            "bucket": flow.bucket_name,
        }
        for flow in flows
    ]
