"""NiFi instance CRUD operations"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import (
    NiFiInstance,
    NiFiInstanceCreate,
    NiFiInstanceUpdate,
    NiFiInstanceResponse,
)
from app.services.encryption_service import encryption_service
from app.api.nifi.nifi_helpers import get_instance_or_404

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.get("/", response_model=List[NiFiInstanceResponse])
async def list_nifi_instances(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get all NiFi instances"""
    instances = (
        db.query(NiFiInstance)
        .order_by(NiFiInstance.hierarchy_attribute, NiFiInstance.hierarchy_value)
        .all()
    )
    return instances


@router.get("/{instance_id}", response_model=NiFiInstanceResponse)
async def get_nifi_instance(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get a specific NiFi instance"""
    instance = get_instance_or_404(db, instance_id)
    return instance


@router.post("/", response_model=NiFiInstanceResponse)
async def create_nifi_instance(
    data: NiFiInstanceCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new NiFi instance"""
    existing = (
        db.query(NiFiInstance)
        .filter(
            NiFiInstance.hierarchy_attribute == data.hierarchy_attribute,
            NiFiInstance.hierarchy_value == data.hierarchy_value,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NiFi instance already exists for {data.hierarchy_attribute}={data.hierarchy_value}",
        )

    encrypted_password = None
    if data.password:
        encrypted_password = encryption_service.encrypt_to_string(data.password)

    instance = NiFiInstance(
        hierarchy_attribute=data.hierarchy_attribute,
        hierarchy_value=data.hierarchy_value,
        nifi_url=data.nifi_url,
        username=data.username,
        password_encrypted=encrypted_password,
        use_ssl=data.use_ssl,
        verify_ssl=data.verify_ssl,
        certificate_name=data.certificate_name,
        check_hostname=data.check_hostname,
    )

    db.add(instance)
    db.commit()
    db.refresh(instance)

    return instance


@router.put("/{instance_id}", response_model=NiFiInstanceResponse)
async def update_nifi_instance(
    instance_id: int,
    data: NiFiInstanceUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update a NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    if data.nifi_url is not None:
        instance.nifi_url = data.nifi_url
    if data.username is not None:
        instance.username = data.username
    if data.password is not None:
        instance.password_encrypted = encryption_service.encrypt_to_string(data.password)
    if data.use_ssl is not None:
        instance.use_ssl = data.use_ssl
    if data.verify_ssl is not None:
        instance.verify_ssl = data.verify_ssl
    if data.certificate_name is not None:
        instance.certificate_name = data.certificate_name
    if data.check_hostname is not None:
        instance.check_hostname = data.check_hostname

    db.commit()
    db.refresh(instance)

    return instance


@router.delete("/{instance_id}")
async def delete_nifi_instance(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    db.delete(instance)
    db.commit()

    return {
        "message": f"Deleted NiFi instance for {instance.hierarchy_attribute}={instance.hierarchy_value}"
    }
