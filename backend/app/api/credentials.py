"""Credential management API endpoints."""

from datetime import datetime, date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.credential import (
    Credential,
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialWithPassword,
)
from app.services.encryption_service import encryption_service

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


def _calculate_status(valid_until: datetime | None) -> str:
    """Calculate credential status based on expiration date."""
    if not valid_until:
        return "active"

    try:
        expiry_date = valid_until.date()
        today = date.today()

        if expiry_date < today:
            return "expired"
        elif (expiry_date - today).days <= 7:
            return "expiring"
        else:
            return "active"
    except Exception:
        return "unknown"


@router.get("/", response_model=List[CredentialResponse])
async def list_credentials(
    include_expired: bool = False,
    source: str | None = None,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """List all credentials (without passwords)."""
    query = db.query(Credential)

    if source:
        query = query.filter(Credential.source == source)

    credentials = query.order_by(Credential.name).all()

    # Calculate status and filter if needed
    results = []
    for cred in credentials:
        status = _calculate_status(cred.valid_until)

        if not include_expired and status == "expired":
            continue

        cred_dict = {
            "id": cred.id,
            "name": cred.name,
            "username": cred.username,
            "type": cred.type,
            "valid_until": cred.valid_until,
            "is_active": cred.is_active,
            "source": cred.source,
            "owner": cred.owner,
            "created_at": cred.created_at,
            "updated_at": cred.updated_at,
            "status": status,
        }
        results.append(cred_dict)

    return results


@router.post("/", response_model=CredentialResponse)
async def create_credential(
    credential: CredentialCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new credential with encrypted password."""
    # Encrypt the password
    encrypted_password = encryption_service.encrypt_to_string(credential.password)

    # Create credential
    db_credential = Credential(
        name=credential.name,
        username=credential.username,
        type=credential.type,
        password_encrypted=encrypted_password,
        valid_until=credential.valid_until,
        source=credential.source,
        owner=credential.owner,
    )

    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)

    # Calculate status
    status = _calculate_status(db_credential.valid_until)

    return {
        "id": db_credential.id,
        "name": db_credential.name,
        "username": db_credential.username,
        "type": db_credential.type,
        "valid_until": db_credential.valid_until,
        "is_active": db_credential.is_active,
        "source": db_credential.source,
        "owner": db_credential.owner,
        "created_at": db_credential.created_at,
        "updated_at": db_credential.updated_at,
        "status": status,
    }


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get a credential by ID (without password)."""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    status_str = _calculate_status(credential.valid_until)

    return {
        "id": credential.id,
        "name": credential.name,
        "username": credential.username,
        "type": credential.type,
        "valid_until": credential.valid_until,
        "is_active": credential.is_active,
        "source": credential.source,
        "owner": credential.owner,
        "created_at": credential.created_at,
        "updated_at": credential.updated_at,
        "status": status_str,
    }


@router.get("/{credential_id}/password")
async def get_credential_password(
    credential_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get decrypted password for a credential."""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    try:
        decrypted_password = encryption_service.decrypt_from_string(
            credential.password_encrypted
        )
        return {"password": decrypted_password}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt password: {str(e)}",
        )


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: int,
    credential_update: CredentialUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update a credential."""
    db_credential = db.query(Credential).filter(Credential.id == credential_id).first()

    if not db_credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Update fields
    if credential_update.name is not None:
        db_credential.name = credential_update.name
    if credential_update.username is not None:
        db_credential.username = credential_update.username
    if credential_update.type is not None:
        db_credential.type = credential_update.type
    if credential_update.valid_until is not None:
        db_credential.valid_until = credential_update.valid_until
    if credential_update.source is not None:
        db_credential.source = credential_update.source
    if credential_update.owner is not None:
        db_credential.owner = credential_update.owner

    # Update password if provided
    if credential_update.password is not None:
        db_credential.password_encrypted = encryption_service.encrypt_to_string(
            credential_update.password
        )

    db_credential.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_credential)

    status_str = _calculate_status(db_credential.valid_until)

    return {
        "id": db_credential.id,
        "name": db_credential.name,
        "username": db_credential.username,
        "type": db_credential.type,
        "valid_until": db_credential.valid_until,
        "is_active": db_credential.is_active,
        "source": db_credential.source,
        "owner": db_credential.owner,
        "created_at": db_credential.created_at,
        "updated_at": db_credential.updated_at,
        "status": status_str,
    }


@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a credential."""
    db_credential = db.query(Credential).filter(Credential.id == credential_id).first()

    if not db_credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    db.delete(db_credential)
    db.commit()

    return {"message": "Credential deleted successfully"}
