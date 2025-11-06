"""
OIDC authentication service for handling OpenID Connect flows.
Supports multiple identity providers with per-provider configuration and caching.
"""

import logging
import secrets
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.settings_manager import settings_manager
from app.models.oidc import OIDCConfig, OIDCUserData
from app.models.user import User
from app.core.security import create_access_token

logger = logging.getLogger(__name__)


class OIDCService:
    """Service for OIDC authentication operations supporting multiple providers."""

    def __init__(self):
        # Per-provider caches: {provider_id: config}
        self._configs: Dict[str, OIDCConfig] = {}
        # JWKS cache per provider: {provider_id: jwks}
        self._jwks_caches: Dict[str, Dict[str, Any]] = {}
        # JWKS cache time per provider: {provider_id: datetime}
        self._jwks_cache_times: Dict[str, datetime] = {}
        self._jwks_cache_ttl = timedelta(hours=1)

    async def get_oidc_config(self, provider_id: str) -> OIDCConfig:
        """
        Fetch OIDC configuration from discovery endpoint for specific provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            OIDCConfig with provider endpoints and capabilities
            
        Raises:
            HTTPException: If provider not found, disabled, or unreachable
        """
        # Check if any OIDC providers are enabled
        if not settings_manager.is_oidc_enabled():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="OIDC authentication is not enabled",
            )

        # Get provider configuration
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OIDC provider '{provider_id}' not found",
            )

        if not provider_config.get("enabled", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"OIDC provider '{provider_id}' is not enabled",
            )

        discovery_url = provider_config.get("discovery_url")
        if not discovery_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OIDC discovery URL not configured for provider '{provider_id}'",
            )

        # Return cached config if available
        if provider_id in self._configs:
            return self._configs[provider_id]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url, timeout=10.0)
                response.raise_for_status()
                config_data = response.json()

            config = OIDCConfig(**config_data)
            self._configs[provider_id] = config
            logger.info(f"Loaded OIDC config for provider '{provider_id}' from {discovery_url}")
            return config

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch OIDC configuration for '{provider_id}': {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to connect to OIDC provider '{provider_id}'",
            )
        except Exception as e:
            logger.error(f"Error parsing OIDC configuration for '{provider_id}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid OIDC provider configuration for '{provider_id}'",
            )

    def generate_state(self) -> str:
        """Generate a secure random state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)

    async def generate_authorization_url(
        self,
        provider_id: str,
        config: OIDCConfig,
        state: str,
        redirect_uri: Optional[str] = None,
    ) -> str:
        """
        Generate the authorization URL for OIDC login.
        
        Args:
            provider_id: Provider identifier
            config: OIDC configuration
            state: CSRF state parameter (should include provider_id)
            redirect_uri: Optional redirect URI override
            
        Returns:
            Complete authorization URL for redirect
        """
        # Get provider configuration
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OIDC provider '{provider_id}' not found",
            )

        # Use provider-specific settings
        client_id = provider_config.get("client_id")
        scopes = provider_config.get("scopes", ["openid", "profile", "email"])

        # Use provider redirect_uri if specified, otherwise use parameter
        if not redirect_uri:
            redirect_uri = provider_config.get("redirect_uri", "")
        
        if not redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No redirect URI configured for provider '{provider_id}'",
            )

        scopes_str = " ".join(scopes)

        params = {
            "client_id": client_id,
            "response_type": "code",
            "scope": scopes_str,
            "redirect_uri": redirect_uri,
            "state": state,
        }

        # Build query string with proper URL encoding
        query_string = urlencode(params)
        return f"{config.authorization_endpoint}?{query_string}"

    async def exchange_code_for_tokens(
        self, provider_id: str, code: str, redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.
        
        Args:
            provider_id: Provider identifier
            code: Authorization code from callback
            redirect_uri: Optional redirect URI override
            
        Returns:
            Token response with access_token, id_token, etc.
        """
        config = await self.get_oidc_config(provider_id)

        # Get provider configuration
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OIDC provider '{provider_id}' not found",
            )

        # Use provider-specific settings
        client_id = provider_config.get("client_id")
        client_secret = provider_config.get("client_secret")

        # Use provider redirect_uri if not specified
        if not redirect_uri:
            redirect_uri = provider_config.get("redirect_uri", "")
        
        if not redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No redirect URI configured for provider '{provider_id}'",
            )

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        logger.debug(f"[OIDC Debug] Exchanging authorization code for provider '{provider_id}'")
        logger.debug(f"[OIDC Debug] Token endpoint: {config.token_endpoint}")
        logger.debug(f"[OIDC Debug] Client ID: {client_id}")
        logger.debug(f"[OIDC Debug] Redirect URI: {redirect_uri}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )
                
                logger.debug(f"[OIDC Debug] Token response status: {response.status_code}")
                
                response.raise_for_status()
                token_response = response.json()
                
                # Log token response (mask sensitive data)
                logger.debug(f"[OIDC Debug] Token response keys: {list(token_response.keys())}")
                if 'access_token' in token_response:
                    logger.debug(f"[OIDC Debug] Access token received (length: {len(token_response['access_token'])})")
                if 'id_token' in token_response:
                    logger.debug(f"[OIDC Debug] ID token received (length: {len(token_response['id_token'])})")
                if 'token_type' in token_response:
                    logger.debug(f"[OIDC Debug] Token type: {token_response['token_type']}")
                if 'expires_in' in token_response:
                    logger.debug(f"[OIDC Debug] Expires in: {token_response['expires_in']} seconds")
                if 'scope' in token_response:
                    logger.debug(f"[OIDC Debug] Scopes: {token_response['scope']}")
                
                return token_response

        except httpx.HTTPError as e:
            logger.error(f"[OIDC Debug] Token exchange failed for provider '{provider_id}': {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[OIDC Debug] Error response status: {e.response.status_code}")
                logger.error(f"[OIDC Debug] Error response body: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to exchange authorization code for tokens with provider '{provider_id}'",
            )

    async def get_jwks(self, provider_id: str) -> Dict[str, Any]:
        """
        Fetch and cache JWKS from the OIDC provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            JWKS dictionary with signing keys
        """
        # Return cached JWKS if still valid
        if (
            provider_id in self._jwks_caches
            and provider_id in self._jwks_cache_times
            and datetime.now(timezone.utc) - self._jwks_cache_times[provider_id]
            < self._jwks_cache_ttl
        ):
            return self._jwks_caches[provider_id]

        config = await self.get_oidc_config(provider_id)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(config.jwks_uri, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()

            self._jwks_caches[provider_id] = jwks
            self._jwks_cache_times[provider_id] = datetime.now(timezone.utc)
            logger.debug(f"JWKS cache updated for provider '{provider_id}'")
            return jwks

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS for provider '{provider_id}': {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to fetch OIDC signing keys from provider '{provider_id}'",
            )

    async def verify_id_token(self, provider_id: str, id_token: str) -> Dict[str, Any]:
        """
        Verify and decode ID token from OIDC provider.
        
        Args:
            provider_id: Provider identifier
            id_token: ID token to verify
            
        Returns:
            Decoded claims from ID token
        """
        config = await self.get_oidc_config(provider_id)
        jwks = await self.get_jwks(provider_id)

        # Get provider configuration
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OIDC provider '{provider_id}' not found",
            )

        client_id = provider_config.get("client_id")

        logger.debug(f"[OIDC Debug] Verifying ID token for provider '{provider_id}'")
        logger.debug(f"[OIDC Debug] Issuer: {config.issuer}")
        logger.debug(f"[OIDC Debug] Client ID (audience): {client_id}")

        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")
            
            logger.debug(f"[OIDC Debug] ID token algorithm: {unverified_header.get('alg')}")
            logger.debug(f"[OIDC Debug] ID token key ID (kid): {kid}")

            # Find matching key in JWKS
            key = None
            for jwk_key in jwks.get("keys", []):
                if jwk_key.get("kid") == kid:
                    key = jwk_key
                    break

            if not key:
                logger.error(f"[OIDC Debug] No matching key found in JWKS for kid: {kid}")
                logger.debug(f"[OIDC Debug] Available keys in JWKS: {[k.get('kid') for k in jwks.get('keys', [])]}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Unable to find matching signing key for provider '{provider_id}'",
                )

            logger.debug(f"[OIDC Debug] Found matching key in JWKS")

            # Verify and decode token
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=client_id,
                issuer=config.issuer,
                options={"verify_at_hash": False},  # Disable at_hash validation
            )

            logger.debug(f"[OIDC Debug] ID token verified successfully")
            logger.debug(f"[OIDC Debug] Token claims: {list(claims.keys())}")
            logger.debug(f"[OIDC Debug] Subject (sub): {claims.get('sub')}")
            logger.debug(f"[OIDC Debug] Issued at (iat): {claims.get('iat')}")
            logger.debug(f"[OIDC Debug] Expires at (exp): {claims.get('exp')}")

            return claims

        except JWTError as e:
            logger.error(f"[OIDC Debug] ID token verification failed for provider '{provider_id}': {e}")
            logger.error(f"[OIDC Debug] Error type: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid ID token from provider '{provider_id}'",
            )

    def extract_user_data(self, provider_id: str, claims: Dict[str, Any]) -> OIDCUserData:
        """
        Extract user data from OIDC claims using provider-specific claim mappings.
        
        Args:
            provider_id: Provider identifier
            claims: Claims from ID token
            
        Returns:
            OIDCUserData with extracted user information
        """
        # Get provider configuration for claim mappings
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OIDC provider '{provider_id}' not found",
            )

        claim_mappings = provider_config.get("claim_mappings", {})
        username_claim = claim_mappings.get("username", "preferred_username")
        email_claim = claim_mappings.get("email", "email")
        name_claim = claim_mappings.get("name", "name")

        # Log available claims for debugging
        logger.debug(f"[OIDC Debug] Available claims in ID token from '{provider_id}': {list(claims.keys())}")
        logger.debug(f"[OIDC Debug] Claim mappings - username: {username_claim}, email: {email_claim}, name: {name_claim}")
        logger.debug(f"[OIDC Debug] Extracted username: {claims.get(username_claim)}")
        logger.debug(f"[OIDC Debug] Extracted email: {claims.get(email_claim)}")
        logger.debug(f"[OIDC Debug] Extracted name: {claims.get(name_claim)}")
        logger.debug(f"Looking for username claim: '{username_claim}'")

        # Extract username (required)
        username = claims.get(username_claim)
        if not username:
            logger.error(f"Username claim '{username_claim}' not found in token from '{provider_id}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username claim '{username_claim}' not found in OIDC token",
            )

        # Apply username prefix if configured
        username_prefix = provider_config.get("username_prefix", "")
        if username_prefix:
            username = f"{username_prefix}{username}"

        # Extract optional fields
        email = claims.get(email_claim)
        name = claims.get(name_claim)
        sub = claims.get("sub", "")

        return OIDCUserData(username=username, email=email, name=name, sub=sub)

    async def provision_or_get_user(
        self, provider_id: str, user_data: OIDCUserData, db: Session
    ) -> User:
        """
        Auto-provision or retrieve existing user.
        
        Args:
            provider_id: Provider identifier
            user_data: Extracted user data from OIDC
            db: Database session
            
        Returns:
            User object (existing or newly created)
        """
        logger.debug(f"[OIDC Debug] Provisioning or retrieving user from provider '{provider_id}'")
        logger.debug(f"[OIDC Debug] Username: {user_data.username}")
        logger.debug(f"[OIDC Debug] Email: {user_data.email}")
        logger.debug(f"[OIDC Debug] Subject (sub): {user_data.sub}")
        
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OIDC provider '{provider_id}' not found",
            )

        # Check if user exists
        user = db.query(User).filter(User.username == user_data.username).first()

        if user:
            # User exists - optionally update email/name
            logger.info(f"[OIDC Debug] Existing user '{user_data.username}' logged in via OIDC provider '{provider_id}'")
            logger.debug(f"[OIDC Debug] User ID: {user.id}, is_active: {user.is_active}, is_superuser: {user.is_superuser}")
            return user

        # User doesn't exist - check if auto-provisioning is enabled
        auto_provision = provider_config.get("auto_provision", False)
        logger.debug(f"[OIDC Debug] Auto-provisioning enabled: {auto_provision}")
        
        if not auto_provision:
            logger.warning(f"[OIDC Debug] User '{user_data.username}' not found and auto-provisioning is disabled")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User '{user_data.username}' not found and auto-provisioning is disabled for provider '{provider_id}'",
            )

        # Create new user
        default_role = provider_config.get("default_role", "user")
        is_superuser = default_role == "admin"

        logger.debug(f"[OIDC Debug] Creating new user with role: {default_role} (is_superuser={is_superuser})")

        # OIDC users don't have passwords (set a placeholder hash)
        # They can only authenticate via OIDC
        placeholder_password = secrets.token_urlsafe(32)

        new_user = User(
            username=user_data.username,
            hashed_password=placeholder_password,  # Not used for OIDC auth
            is_active=False,  # New OIDC users must be approved by admin
            is_superuser=is_superuser,
            is_oidc_user=True,  # Mark as OIDC user
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(
            f"[OIDC Debug] Auto-provisioned new user '{user_data.username}' (ID: {new_user.id}) from OIDC provider '{provider_id}' "
            f"with role '{default_role}' - PENDING ADMIN APPROVAL (is_active=False)"
        )

        return new_user


# Singleton instance
oidc_service = OIDCService()
