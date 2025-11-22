"""NiFi authentication service for nipyapi configuration"""

import ssl
import logging
import nipyapi
from nipyapi import config, security

from app.models.nifi_instance import NiFiInstance
from app.services.encryption_service import encryption_service
from app.services.certificate_manager import certificate_manager
from app.core.settings_manager import settings_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


def configure_nifi_connection(
    instance: NiFiInstance,
    normalize_url: bool = False,
) -> None:
    """
    Configure nipyapi connection for a NiFi instance.
    Supports three authentication methods (in priority order):
    1. OIDC (if instance.oidc_provider_id is set)
    2. Client certificates (if certificate_name is specified)
    3. Username/password (if username is provided)

    Args:
        instance: NiFi instance model with connection details
        normalize_url: If True, removes /nifi-api suffix and re-adds it (for deployment endpoints)
    """
    # Configure base URL
    nifi_url = instance.nifi_url.rstrip("/")

    # Normalize URL if requested (remove and re-add /nifi-api)
    if normalize_url:
        if nifi_url.endswith("/nifi-api"):
            nifi_url = nifi_url[:-9]
        nifi_url = f"{nifi_url}/nifi-api"

    config.nifi_config.host = nifi_url
    config.nifi_config.verify_ssl = instance.verify_ssl

    if not instance.verify_ssl:
        nipyapi.config.disable_insecure_request_warnings = True

    # Priority 1: OIDC Authentication (if oidc_provider_id is set)
    if instance.oidc_provider_id and instance.oidc_provider_id.strip():
        logger.info(f"Using OIDC authentication with provider: {instance.oidc_provider_id}")
        _configure_oidc_auth(instance.oidc_provider_id, instance.verify_ssl)
        return
    
    # Priority 2: Certificate-based Authentication
    if instance.certificate_name:
        logger.info(f"Using certificate authentication: {instance.certificate_name}")
        _configure_certificate_auth(instance)
        return
    
    # Priority 3: Username/Password Authentication
    if instance.username:
        logger.info("Using username/password authentication")
        _configure_username_auth(instance)
        return
    
    logger.warning("No authentication method configured for NiFi instance")


def _configure_oidc_auth(provider_id: str, verify_ssl: bool = True) -> None:
    """
    Configure OIDC authentication using a provider from oidc_providers.yaml.
    
    Args:
        provider_id: ID of the OIDC provider from oidc_providers.yaml
        verify_ssl: Whether to verify SSL certificates for OIDC endpoints
    """
    try:
        # Load provider configuration
        provider_config = settings_manager.get_oidc_provider(provider_id)
        if not provider_config:
            raise ValueError(
                f"OIDC provider '{provider_id}' not found in oidc_providers.yaml"
            )
        
        if not provider_config.get("enabled", False):
            raise ValueError(
                f"OIDC provider '{provider_id}' is not enabled in oidc_providers.yaml"
            )
        
        # Get OIDC configuration
        discovery_url = provider_config.get("discovery_url")
        if not discovery_url:
            raise ValueError(
                f"OIDC provider '{provider_id}' missing discovery_url"
            )
        
        # Derive token endpoint from discovery URL
        # For Keycloak: https://host/realms/realm/.well-known/openid-configuration
        #            -> https://host/realms/realm/protocol/openid-connect/token
        token_endpoint = discovery_url
        if "/.well-known/openid-configuration" in token_endpoint:
            token_endpoint = token_endpoint.replace(
                "/.well-known/openid-configuration",
                "/protocol/openid-connect/token"
            )
        
        client_id = provider_config.get("client_id")
        client_secret = provider_config.get("client_secret")
        
        if not client_id or not client_secret:
            raise ValueError(
                f"OIDC provider '{provider_id}' missing client_id or client_secret"
            )
        
        # Use Client Credentials flow (no username/password)
        # This is the recommended approach for backend-to-NiFi authentication
        logger.debug(f"Authenticating with OIDC token endpoint: {token_endpoint}")
        
        security.service_login_oidc(
            service="nifi",
            oidc_token_endpoint=token_endpoint,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )
        
        logger.info(f"Successfully authenticated with OIDC provider: {provider_id}")
        
    except Exception as e:
        logger.error(f"Failed to authenticate with OIDC provider '{provider_id}': {e}")
        raise ValueError(f"OIDC authentication failed: {str(e)}")


def _configure_certificate_auth(instance: NiFiInstance) -> None:
    """
    Configure certificate-based authentication.
    
    Args:
        instance: NiFi instance with certificate configuration
    """
    try:
        # Get certificate configuration from certificate manager
        cert_paths = certificate_manager.get_certificate_paths(instance.certificate_name)
        
        if not cert_paths:
            raise ValueError(
                f"Certificate '{instance.certificate_name}' not found in certificates.yaml"
            )
        
        # Get certificate paths and password
        ca_cert_path = cert_paths["ca_cert_path"]
        cert_path = cert_paths["cert_path"]
        key_path = cert_paths["key_path"]
        key_password = cert_paths["password"]
        
        # Verify certificate files exist
        if not ca_cert_path.exists():
            raise FileNotFoundError(f"CA certificate not found: {ca_cert_path}")
        if not cert_path.exists():
            raise FileNotFoundError(f"Client certificate not found: {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"Client key not found: {key_path}")
        
        # Create SSL context
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        
        # Load client certificate and key
        ssl_context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
            password=key_password,
        )
        
        # Load CA certificate
        ssl_context.load_verify_locations(cafile=str(ca_cert_path))
        
        # Configure SSL verification based on instance settings
        if not instance.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        elif not instance.check_hostname:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Set the SSL context to nipyapi config
        config.nifi_config.ssl_context = ssl_context
        
        logger.info(f"Successfully configured certificate authentication: {instance.certificate_name}")
        
    except Exception as e:
        logger.error(f"Failed to configure certificate authentication: {e}")
        raise


def _configure_username_auth(instance: NiFiInstance) -> None:
    """
    Configure username/password authentication.
    
    Args:
        instance: NiFi instance with username/password
    """
    try:
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(
                instance.password_encrypted
            )
        
        if not password:
            logger.warning("Username provided but password is empty")
            return
        
        config.nifi_config.username = instance.username
        config.nifi_config.password = password
        
        security.service_login(
            service="nifi",
            username=instance.username,
            password=password
        )
        
        logger.info(f"Successfully authenticated with username: {instance.username}")
        
    except Exception as e:
        logger.error(f"Failed to authenticate with username/password: {e}")
        raise


def configure_nifi_test_connection(
    nifi_url: str,
    username: str = None,
    password: str = None,
    verify_ssl: bool = True,
    certificate_name: str = None,
    check_hostname: bool = True,
    oidc_provider_id: str = None,
) -> None:
    """
    Configure nipyapi connection for testing (without saving to database).

    Args:
        nifi_url: NiFi API URL
        username: Optional username
        password: Optional password
        verify_ssl: Whether to verify SSL certificates
        certificate_name: Name of certificate to use (from certificates.yaml)
        check_hostname: Whether to verify SSL certificate hostname matches
        oidc_provider_id: Optional OIDC provider ID from oidc_providers.yaml
    """
    # Configure base URL
    nifi_url = nifi_url.rstrip("/")
    config.nifi_config.host = nifi_url
    config.nifi_config.verify_ssl = verify_ssl

    if not verify_ssl:
        nipyapi.config.disable_insecure_request_warnings = True

    # Priority 1: OIDC Authentication
    if oidc_provider_id and oidc_provider_id.strip():
        logger.info(f"Test connection using OIDC provider: {oidc_provider_id}")
        _configure_oidc_auth(oidc_provider_id, verify_ssl)
        return

    # Priority 2: Certificate Authentication
    if certificate_name:
        logger.info(f"Test connection using certificate: {certificate_name}")
        _configure_certificate_test_auth(certificate_name, verify_ssl, check_hostname)
        return

    # Priority 3: Username/Password Authentication
    if username and password:
        logger.info("Test connection using username/password")
        config.nifi_config.username = username
        config.nifi_config.password = password
        security.service_login(service="nifi", username=username, password=password)
        return

    logger.warning("No authentication method configured for test connection")


def _configure_certificate_test_auth(
    certificate_name: str, verify_ssl: bool = True, check_hostname: bool = True
) -> None:
    """
    Configure certificate-based authentication for testing.
    
    Args:
        certificate_name: Name of certificate from certificates.yaml
        verify_ssl: Whether to verify SSL certificates
        check_hostname: Whether to verify SSL certificate hostname
    """
    try:
        # Get certificate configuration
        cert_paths = certificate_manager.get_certificate_paths(certificate_name)
        if not cert_paths:
            raise ValueError(
                f"Certificate '{certificate_name}' not found in certificates.yaml"
            )

        # Get certificate paths and password
        ca_cert_path = cert_paths["ca_cert_path"]
        cert_path = cert_paths["cert_path"]
        key_path = cert_paths["key_path"]
        key_password = cert_paths["password"]

        # Verify certificate files exist
        if not ca_cert_path.exists():
            raise FileNotFoundError(f"CA certificate not found: {ca_cert_path}")
        if not cert_path.exists():
            raise FileNotFoundError(f"Client certificate not found: {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"Client key not found: {key_path}")

        # Create SSL context
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        # Load client certificate and key
        ssl_context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
            password=key_password,
        )

        # Load CA certificate
        ssl_context.load_verify_locations(cafile=str(ca_cert_path))

        # Configure SSL verification
        if not verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        elif not check_hostname:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Set the SSL context to nipyapi config
        config.nifi_config.ssl_context = ssl_context
        
    except Exception as e:
        logger.error(f"Failed to configure certificate for test: {e}")
        raise
