"""NiFi authentication service for nipyapi configuration"""

import ssl
import nipyapi
from nipyapi import config, security

from app.models.nifi_instance import NiFiInstance
from app.services.encryption_service import encryption_service
from app.services.certificate_manager import certificate_manager


def configure_nifi_connection(
    instance: NiFiInstance,
    normalize_url: bool = False,
) -> None:
    """
    Configure nipyapi connection for a NiFi instance.

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

    # Configure SSL context with client certificates if certificate_name is specified
    if instance.certificate_name:
        # Get certificate configuration from certificate manager
        cert_paths = certificate_manager.get_certificate_paths(
            instance.certificate_name
        )

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

        # Create SSL context manually to handle verify_ssl setting properly
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
            # Don't verify certificates at all
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        elif not instance.check_hostname:
            # Verify certificates but don't check hostname
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Set the SSL context to nipyapi config
        config.nifi_config.ssl_context = ssl_context

    # Authenticate with username/password if provided
    if instance.username:
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(
                instance.password_encrypted
            )

        if password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(
                service="nifi", username=instance.username, password=password
            )


def configure_nifi_test_connection(
    nifi_url: str,
    username: str = None,
    password: str = None,
    verify_ssl: bool = True,
    certificate_name: str = None,
    check_hostname: bool = True,
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
    """
    # Configure base URL
    nifi_url = nifi_url.rstrip("/")
    config.nifi_config.host = nifi_url
    config.nifi_config.verify_ssl = verify_ssl

    if not verify_ssl:
        nipyapi.config.disable_insecure_request_warnings = True

    # Configure SSL context with client certificates if certificate_name is specified
    if certificate_name:
        # Get certificate configuration from certificate manager
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

        # Create SSL context manually to handle verify_ssl setting properly
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        # Load client certificate and key
        ssl_context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
            password=key_password,
        )

        # Load CA certificate
        ssl_context.load_verify_locations(cafile=str(ca_cert_path))

        # Configure SSL verification based on settings
        if not verify_ssl:
            # Don't verify certificates at all
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        elif not check_hostname:
            # Verify certificates but don't check hostname
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Set the SSL context to nipyapi config
        config.nifi_config.ssl_context = ssl_context

    # Authenticate with username/password if provided
    if username and password:
        config.nifi_config.username = username
        config.nifi_config.password = password
        security.service_login(service="nifi", username=username, password=password)
