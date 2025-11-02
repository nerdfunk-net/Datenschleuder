"""Authentication API endpoints"""

from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import verify_token
from app.services.certificate_manager import certificate_manager


router = APIRouter(prefix="/api/authentication", tags=["authentication"])


class CertificateInfo(BaseModel):
    """Certificate information for API response"""

    name: str


class CertificatesResponse(BaseModel):
    """Response for get-certificates endpoint"""

    certificates: List[CertificateInfo]


@router.get("/get-certificates", response_model=CertificatesResponse)
async def get_certificates(token_data: dict = Depends(verify_token)):
    """Get list of available client certificates for NiFi authentication"""
    certificates = certificate_manager.get_certificates()

    return CertificatesResponse(
        certificates=[CertificateInfo(name=cert.name) for cert in certificates]
    )
