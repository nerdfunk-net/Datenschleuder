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
    Get list of available OIDC providers for user login selection.
    Excludes backend-only providers (backend=true).
    
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
        enabled_providers = settings_manager.get_enabled_user_providers()

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


@router.get("/backend-providers")
async def get_backend_oidc_providers() -> Dict[str, Any]:
    """
    Get list of OIDC providers available for backend authentication (NiFi instances).
    Returns ALL enabled providers (both user-facing and backend-only).
    
    Returns:
        Dict with providers list
    """
    try:
        enabled_providers = settings_manager.get_enabled_oidc_providers()

        # Return minimal info for dropdown selection
        providers_list = [
            {
                "provider_id": provider["provider_id"],
                "name": provider.get("name", provider["provider_id"]),
                "description": provider.get("description", ""),
                "backend": provider.get("backend", False),
            }
            for provider in enabled_providers
        ]

        return {
            "providers": providers_list
        }

    except Exception as e:
        logger.error(f"Failed to get backend OIDC providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve backend OIDC providers",
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


@router.get("/test/providers")
async def get_test_providers() -> Dict[str, Any]:
    """
    Get all OIDC providers (including backend providers) for testing purposes.
    This endpoint is accessible without authentication.
    
    Returns:
        Dictionary with list of all providers
    """
    try:
        providers = settings_manager.get_enabled_oidc_providers()
        provider_list = []
        
        for provider in providers:
            # Convert scopes list to space-separated string
            scopes = provider.get("scopes", ["openid", "profile", "email"])
            if isinstance(scopes, list):
                scope_str = " ".join(scopes)
            else:
                scope_str = scopes
            
            provider_list.append({
                "provider_id": provider["provider_id"],
                "name": provider.get("name", provider["provider_id"]),
                "discovery_url": provider.get("discovery_url"),
                "client_id": provider.get("client_id"),
                "client_secret": provider.get("client_secret", ""),
                "redirect_uri": provider.get("redirect_uri", ""),
                "scope": scope_str,
                "response_type": "code",
                "backend": provider.get("backend", False),
                "enabled": True,
            })
        
        return {
            "providers": provider_list,
            "count": len(provider_list),
        }
    except Exception as e:
        logger.error(f"Failed to get test providers: {e}")
        return {
            "providers": [],
            "count": 0,
            "error": str(e),
        }


@router.post("/test/frontend")
async def test_frontend_oidc(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test frontend OIDC configuration without authentication.
    Validates discovery URL, fetches configuration, and validates settings.
    
    Args:
        request: Dictionary with OIDC configuration
            - discovery_url: OIDC discovery endpoint
            - client_id: OAuth client ID
            - client_secret: OAuth client secret (optional)
            - redirect_uri: OAuth redirect URI
            - scope: OAuth scopes
            - response_type: OAuth response type
    
    Returns:
        Test results with configuration details
    """
    try:
        import httpx
        from urllib.parse import urlparse
        
        steps = []
        discovery_url = request.get("discovery_url")
        
        if not discovery_url:
            return {
                "status": "error",
                "message": "Discovery URL is required",
                "error": "Missing discovery_url parameter",
            }
        
        steps.append(f"Testing discovery URL: {discovery_url}")
        
        # Fetch OIDC configuration
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(discovery_url, timeout=10.0)
                response.raise_for_status()
                config = response.json()
                steps.append("✓ Successfully fetched OIDC configuration")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to fetch OIDC configuration: {str(e)}",
                "error": str(e),
                "steps": steps,
            }
        
        # Validate required endpoints
        required_endpoints = ["authorization_endpoint", "token_endpoint", "jwks_uri"]
        missing_endpoints = [ep for ep in required_endpoints if ep not in config]
        
        if missing_endpoints:
            return {
                "status": "error",
                "message": f"Missing required endpoints: {', '.join(missing_endpoints)}",
                "error": f"Configuration missing: {missing_endpoints}",
                "steps": steps,
            }
        
        steps.append("✓ All required endpoints present")
        
        # Validate client settings
        client_id = request.get("client_id")
        redirect_uri = request.get("redirect_uri")
        
        if not client_id:
            steps.append("⚠ Warning: No client_id provided")
        else:
            steps.append(f"✓ Client ID: {client_id}")
        
        if not redirect_uri:
            steps.append("⚠ Warning: No redirect_uri provided")
        else:
            steps.append(f"✓ Redirect URI: {redirect_uri}")
            # Validate redirect URI format
            try:
                parsed = urlparse(redirect_uri)
                if not parsed.scheme or not parsed.netloc:
                    steps.append("⚠ Warning: Redirect URI may be invalid")
                else:
                    steps.append("✓ Redirect URI format valid")
            except Exception:
                steps.append("⚠ Warning: Could not parse redirect URI")
        
        # Check supported response types
        response_type = request.get("response_type", "code")
        supported_types = config.get("response_types_supported", [])
        if supported_types and response_type not in supported_types:
            steps.append(f"⚠ Warning: Response type '{response_type}' may not be supported")
            steps.append(f"  Supported types: {', '.join(supported_types)}")
        else:
            steps.append(f"✓ Response type '{response_type}' is supported")
        
        # Check scopes
        scope = request.get("scope", "openid profile email")
        supported_scopes = config.get("scopes_supported", [])
        requested_scopes = scope.split()
        if supported_scopes:
            unsupported_scopes = [s for s in requested_scopes if s not in supported_scopes]
            if unsupported_scopes:
                steps.append(f"⚠ Warning: Scopes may not be supported: {', '.join(unsupported_scopes)}")
            else:
                steps.append(f"✓ All requested scopes are supported")
        
        return {
            "status": "success",
            "message": "Frontend OIDC configuration is valid",
            "details": {
                "issuer": config.get("issuer"),
                "authorization_endpoint": config.get("authorization_endpoint"),
                "token_endpoint": config.get("token_endpoint"),
                "jwks_uri": config.get("jwks_uri"),
                "userinfo_endpoint": config.get("userinfo_endpoint"),
                "end_session_endpoint": config.get("end_session_endpoint"),
                "response_types_supported": config.get("response_types_supported"),
                "scopes_supported": config.get("scopes_supported"),
                "claims_supported": config.get("claims_supported"),
                "grant_types_supported": config.get("grant_types_supported"),
            },
            "steps": steps,
        }
        
    except Exception as e:
        logger.error(f"Frontend OIDC test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Test failed with exception",
            "error": str(e),
            "steps": steps if 'steps' in locals() else [],
        }


@router.post("/test/backend")
async def test_backend_oidc(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test backend NiFi OIDC authentication without authentication.
    Attempts to authenticate with NiFi using OIDC and fetch version info.
    
    Args:
        request: Dictionary with configuration
            - discovery_url: OIDC discovery endpoint
            - client_id: OAuth client ID
            - client_secret: OAuth client secret
            - nifi_url: NiFi API URL
            - verify_ssl: Whether to verify SSL (default: False)
    
    Returns:
        Test results with authentication details
    """
    try:
        import nipyapi
        from nipyapi import config as nifi_config, security
        import httpx
        
        steps = []
        discovery_url = request.get("discovery_url")
        client_id = request.get("client_id")
        client_secret = request.get("client_secret")
        nifi_url = request.get("nifi_url")
        verify_ssl = request.get("verify_ssl", False)
        
        # Validate inputs
        if not all([discovery_url, client_id, client_secret, nifi_url]):
            missing = []
            if not discovery_url: missing.append("discovery_url")
            if not client_id: missing.append("client_id")
            if not client_secret: missing.append("client_secret")
            if not nifi_url: missing.append("nifi_url")
            
            return {
                "status": "error",
                "message": f"Missing required parameters: {', '.join(missing)}",
                "error": "Incomplete configuration",
            }
        
        steps.append(f"Testing NiFi OIDC authentication to: {nifi_url}")
        steps.append(f"Using discovery URL: {discovery_url}")
        
        # Derive token endpoint from discovery URL
        token_endpoint = discovery_url
        if "/.well-known/openid-configuration" in token_endpoint:
            token_endpoint = token_endpoint.replace(
                "/.well-known/openid-configuration",
                "/protocol/openid-connect/token"
            )
        elif "/.well-known/oauth-authorization-server" in token_endpoint:
            token_endpoint = token_endpoint.replace(
                "/.well-known/oauth-authorization-server",
                "/oauth/token"
            )
        
        steps.append(f"Derived token endpoint: {token_endpoint}")
        
        # Configure NiFi connection
        nifi_config.host = nifi_url.rstrip("/")
        nifi_config.verify_ssl = verify_ssl
        
        if not verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True
            steps.append("⚠ SSL verification disabled")
        
        steps.append("Configuring nipyapi for OIDC authentication")
        
        try:
            # Attempt OIDC login using nipyapi
            result = security.service_login_oidc(
                service="nifi",
                oidc_token_endpoint=token_endpoint,
                client_id=client_id,
                client_secret=client_secret,
                verify_ssl=verify_ssl,
            )
            
            if result:
                steps.append("✓ Successfully authenticated with NiFi using OIDC")
            else:
                steps.append("⚠ Authentication returned but may not be complete")
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"OIDC authentication failed: {str(e)}",
                "error": str(e),
                "steps": steps,
            }
        
        # Try to fetch NiFi version as connection test
        try:
            version_info = nipyapi.system.get_nifi_version_info()
            nifi_version = version_info.nifi_version if hasattr(version_info, "nifi_version") else str(version_info)
            steps.append(f"✓ Successfully connected to NiFi (version: {nifi_version})")
            
            return {
                "status": "success",
                "message": "Backend NiFi OIDC authentication successful",
                "details": {
                    "nifi_version": nifi_version,
                    "nifi_url": nifi_url,
                    "token_endpoint": token_endpoint,
                    "verify_ssl": verify_ssl,
                },
                "steps": steps,
            }
            
        except Exception as e:
            steps.append(f"✗ Failed to fetch NiFi version: {str(e)}")
            return {
                "status": "error",
                "message": "Authentication succeeded but failed to connect to NiFi API",
                "error": str(e),
                "steps": steps,
            }
        
    except Exception as e:
        logger.error(f"Backend OIDC test failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Test failed with exception",
            "error": str(e),
            "steps": steps if 'steps' in locals() else [],
        }
