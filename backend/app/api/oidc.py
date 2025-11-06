"""
OIDC authentication router for OpenID Connect integration with multiple providers.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.orm import Session

from app.models.oidc import (
    OIDCProvidersResponse,
    OIDCProvider,
    OIDCLoginResponse,
    OIDCCallbackRequest,
)
from app.models.user import Token
from app.core.settings_manager import settings_manager
from app.services.oidc_service import oidc_service
from app.core.security import create_access_token
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oidc", tags=["oidc-authentication"])


@router.get("/enabled")
async def check_oidc_enabled() -> Dict[str, bool]:
    """
    Check if OIDC authentication is enabled.
    
    Returns:
        Dictionary with 'enabled' boolean
    """
    return {"enabled": settings_manager.is_oidc_enabled()}


@router.get("/providers", response_model=OIDCProvidersResponse)
async def get_oidc_providers() -> OIDCProvidersResponse:
    """
    Get list of available OIDC providers for login selection.
    
    Returns:
        OIDCProvidersResponse with provider list and settings
        
    Raises:
        HTTPException: If OIDC is not enabled or error occurs
    """
    if not settings_manager.is_oidc_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC authentication is not enabled",
        )

    try:
        enabled_providers = settings_manager.get_enabled_oidc_providers()

        # Return only user-facing information
        providers_list = [
            OIDCProvider(
                provider_id=provider["provider_id"],
                name=provider.get("name", provider["provider_id"]),
                description=provider.get("description", ""),
                icon=provider.get("icon", ""),
                display_order=provider.get("display_order", 999),
            )
            for provider in enabled_providers
        ]

        global_settings = settings_manager.get_oidc_global_settings()
        allow_traditional = global_settings.get("allow_traditional_login", True)

        return OIDCProvidersResponse(
            providers=providers_list, allow_traditional_login=allow_traditional
        )

    except Exception as e:
        logger.error(f"Failed to get OIDC providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OIDC providers",
        )


@router.get("/{provider_id}/login", response_model=OIDCLoginResponse)
async def oidc_login(
    provider_id: str, redirect_uri: str = Query(None, description="Optional redirect URI override")
) -> OIDCLoginResponse:
    """
    Initiate OIDC authentication flow with specific provider.
    
    Args:
        provider_id: Provider identifier
        redirect_uri: Optional redirect URI override
        
    Returns:
        OIDCLoginResponse with authorization URL and state
        
    Raises:
        HTTPException: If OIDC disabled or provider not found
    """
    if not settings_manager.is_oidc_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC authentication is not enabled",
        )

    try:
        config = await oidc_service.get_oidc_config(provider_id)
        state = oidc_service.generate_state()

        # Include provider_id in state for callback validation
        state_with_provider = f"{provider_id}:{state}"

        # Generate authorization URL
        auth_url = await oidc_service.generate_authorization_url(
            provider_id, config, state_with_provider, redirect_uri
        )

        return OIDCLoginResponse(
            authorization_url=auth_url, state=state_with_provider, provider_id=provider_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate OIDC login for '{provider_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OIDC login with provider '{provider_id}'",
        )


@router.post("/{provider_id}/callback", response_model=Token)
async def oidc_callback(
    provider_id: str, callback_data: OIDCCallbackRequest, db: Session = Depends(get_db)
) -> Token:
    """
    Handle OIDC callback after user authentication.
    
    Args:
        provider_id: Provider identifier
        callback_data: Authorization code and state from callback
        db: Database session
        
    Returns:
        Token with access_token for application
        
    Raises:
        HTTPException: If OIDC disabled, state mismatch, or auth fails
    """
    if not settings_manager.is_oidc_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC authentication is not enabled",
        )

    try:
        # Validate state includes correct provider_id
        if callback_data.state:
            state_parts = callback_data.state.split(":", 1)
            if len(state_parts) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid state parameter",
                )

            state_provider = state_parts[0]
            if state_provider != provider_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="State provider mismatch",
                )

        # Exchange code for tokens
        tokens = await oidc_service.exchange_code_for_tokens(provider_id, callback_data.code)

        # Verify ID token
        if "id_token" not in tokens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from provider",
            )

        claims = await oidc_service.verify_id_token(provider_id, tokens["id_token"])

        # Extract user data
        user_data = oidc_service.extract_user_data(provider_id, claims)

        # Provision or get user
        user = await oidc_service.provision_or_get_user(provider_id, user_data, db)

        # Create application JWT
        access_token = create_access_token(data={"sub": user.username})

        logger.info(f"User '{user.username}' authenticated via OIDC provider '{provider_id}'")

        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OIDC callback failed for provider '{provider_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed with provider '{provider_id}'",
        )
