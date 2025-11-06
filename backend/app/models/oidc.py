"""
Pydantic models for OIDC authentication.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OIDCConfig(BaseModel):
    """OpenID Connect provider configuration from discovery endpoint."""
    
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str
    response_types_supported: List[str] = []
    subject_types_supported: List[str] = []
    id_token_signing_alg_values_supported: List[str] = []
    scopes_supported: Optional[List[str]] = None
    token_endpoint_auth_methods_supported: Optional[List[str]] = None
    claims_supported: Optional[List[str]] = None


class OIDCProvider(BaseModel):
    """OIDC provider information for frontend display."""
    
    provider_id: str
    name: str
    description: str = ""
    icon: str = ""
    display_order: int = 999


class OIDCProvidersResponse(BaseModel):
    """Response containing available OIDC providers."""
    
    providers: List[OIDCProvider]
    allow_traditional_login: bool = True


class OIDCLoginResponse(BaseModel):
    """Response for OIDC login initiation."""
    
    authorization_url: str
    state: str
    provider_id: str


class OIDCCallbackRequest(BaseModel):
    """Request body for OIDC callback."""
    
    code: str
    state: Optional[str] = None


class OIDCTokenResponse(BaseModel):
    """Response from OIDC token exchange."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


class OIDCUserData(BaseModel):
    """Extracted user data from OIDC claims."""
    
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    sub: str  # Subject identifier from OIDC
