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

    logger.info(f"[OIDC Debug] Callback received for provider '{provider_id}'")
    logger.debug(f"[OIDC Debug] Authorization code length: {len(callback_data.code) if callback_data.code else 0}")
    logger.debug(f"[OIDC Debug] State parameter: {callback_data.state}")

    try:
        # Validate state includes correct provider_id
        if callback_data.state:
            state_parts = callback_data.state.split(":", 1)
            if len(state_parts) != 2:
                logger.error(f"[OIDC Debug] Invalid state format: {callback_data.state}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid state parameter",
                )

            state_provider = state_parts[0]
            if state_provider != provider_id:
                logger.error(f"[OIDC Debug] State provider mismatch: expected '{provider_id}', got '{state_provider}'")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="State provider mismatch",
                )
            
            logger.debug(f"[OIDC Debug] State validation successful")

        # Exchange code for tokens
        logger.debug(f"[OIDC Debug] Exchanging authorization code for tokens...")
        tokens = await oidc_service.exchange_code_for_tokens(provider_id, callback_data.code)

        # Verify ID token
        if "id_token" not in tokens:
            logger.error(f"[OIDC Debug] No ID token in response from provider '{provider_id}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from provider",
            )

        logger.debug(f"[OIDC Debug] Verifying ID token...")
        claims = await oidc_service.verify_id_token(provider_id, tokens["id_token"])

        # Extract user data
        logger.debug(f"[OIDC Debug] Extracting user data from claims...")
        user_data = oidc_service.extract_user_data(provider_id, claims)

        # Provision or get user
        logger.debug(f"[OIDC Debug] Provisioning or retrieving user...")
        user = await oidc_service.provision_or_get_user(provider_id, user_data, db)

        # Check if user is active
        if not user.is_active:
            logger.warning(f"[OIDC Debug] Inactive user '{user.username}' attempted login via OIDC provider '{provider_id}'")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is pending approval by an administrator. Please contact your system administrator.",
            )

        # Create application JWT
        logger.debug(f"[OIDC Debug] Creating application access token...")
        access_token = create_access_token(data={"sub": user.username})

        logger.info(f"[OIDC Debug] User '{user.username}' authenticated successfully via OIDC provider '{provider_id}'")

        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OIDC Debug] OIDC callback failed for provider '{provider_id}': {e}")
        logger.error(f"[OIDC Debug] Exception type: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed with provider '{provider_id}'",
        )


@router.post("/{provider_id}/logout")
async def oidc_logout(provider_id: str, id_token_hint: str = Query(None, description="Optional ID token hint for logout")) -> Dict[str, Any]:
    """
    Handle OIDC logout for specific provider.

    Args:
        provider_id: Provider identifier
        id_token_hint: Optional ID token to hint to provider which session to end

    Returns:
        Dictionary with logout_url and redirect information

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

        # Check if provider supports end_session_endpoint
        end_session_endpoint = getattr(config, 'end_session_endpoint', None)

        if end_session_endpoint:
            # Build logout URL with optional ID token hint
            logout_url = end_session_endpoint
            if id_token_hint:
                from urllib.parse import urlencode
                params = {"id_token_hint": id_token_hint}
                logout_url += f"?{urlencode(params)}"

            return {
                "logout_url": logout_url,
                "requires_redirect": True,
                "provider_id": provider_id,
            }
        else:
            return {
                "logout_url": None,
                "requires_redirect": False,
                "message": f"OIDC provider '{provider_id}' does not support end_session_endpoint",
                "provider_id": provider_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OIDC logout failed for provider '{provider_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process OIDC logout for provider '{provider_id}'",
        )


@router.get("/debug")
async def get_oidc_debug_info() -> Dict[str, Any]:
    """
    Get detailed debug information about OIDC configuration.

    Returns:
        Dictionary with comprehensive OIDC configuration details
    """
    try:
        oidc_enabled = settings_manager.is_oidc_enabled()
        global_settings = settings_manager.get_oidc_global_settings()

        providers_debug = []

        if oidc_enabled:
            enabled_providers = settings_manager.get_enabled_oidc_providers()

            for provider in enabled_providers:
                provider_id = provider["provider_id"]

                # Get full configuration
                try:
                    config = await oidc_service.get_oidc_config(provider_id)

                    provider_debug = {
                        "provider_id": provider_id,
                        "name": provider.get("name", provider_id),
                        "enabled": True,
                        "discovery_url": provider.get("discovery_url"),
                        "configuration": {
                            "issuer": config.issuer,
                            "authorization_endpoint": config.authorization_endpoint,
                            "token_endpoint": config.token_endpoint,
                            "jwks_uri": config.jwks_uri,
                            "userinfo_endpoint": config.userinfo_endpoint,
                            "end_session_endpoint": getattr(config, 'end_session_endpoint', None),
                            "response_types_supported": config.response_types_supported,
                            "scopes_supported": config.scopes_supported,
                        },
                        "client_settings": {
                            "client_id": provider.get("client_id"),
                            "redirect_uri": provider.get("redirect_uri"),
                            "scopes": provider.get("scopes", ["openid", "profile", "email"]),
                            "claim_mappings": provider.get("claim_mappings", {}),
                        },
                        "provisioning": {
                            "auto_provision": provider.get("auto_provision", False),
                            "default_role": provider.get("default_role", "user"),
                            "username_prefix": provider.get("username_prefix", ""),
                        },
                        "ssl": {
                            "ca_cert_path": provider.get("ca_cert_path"),
                        }
                    }
                    providers_debug.append(provider_debug)

                except Exception as e:
                    providers_debug.append({
                        "provider_id": provider_id,
                        "name": provider.get("name", provider_id),
                        "enabled": True,
                        "error": f"Failed to fetch configuration: {str(e)}",
                    })

        return {
            "oidc_enabled": oidc_enabled,
            "global_settings": global_settings,
            "providers_count": len(providers_debug),
            "providers": providers_debug,
        }

    except Exception as e:
        logger.error(f"Failed to get OIDC debug info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OIDC debug information",
        )
